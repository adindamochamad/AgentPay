#!/usr/bin/env python3
"""
Demo dua agen Claude (Anthropic) yang berinteraksi dengan AgentPay secara otonom.

Menjalankan:
  export ANTHROPIC_API_KEY=...
  pip install anthropic requests cryptography
  python demo_ai_agents.py

Backend AgentPay harus hidup (mis. docker compose), default http://localhost:8000
"""

from __future__ import annotations

import base64
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import requests
from anthropic import Anthropic
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# --- Penandatanganan Ed25519 (selaras dengan backend / tests/e2e/tanda_helper.py) ---


def serialisasi_kanonik(muatan: dict[str, Any]) -> str:
    return json.dumps(muatan, sort_keys=True, separators=(",", ":"))


def stempel_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def tanda_dengan_kunci_privat(privat_base64: str, pesan_tanpa_tanda: dict[str, Any]) -> str:
    byte_privat = base64.b64decode(privat_base64)
    kunci_privat = Ed25519PrivateKey.from_private_bytes(byte_privat)
    kanonik = serialisasi_kanonik(pesan_tanpa_tanda).encode("utf-8")
    tanda_byte = kunci_privat.sign(kanonik)
    return base64.b64encode(tanda_byte).decode("utf-8")


def pasangan_kunci_baru() -> tuple[str, str]:
    kunci_privat = Ed25519PrivateKey.generate()
    byte_privat = kunci_privat.private_bytes_raw()
    byte_publik = kunci_privat.public_key().public_bytes_raw()
    return (
        base64.b64encode(byte_privat).decode("utf-8"),
        base64.b64encode(byte_publik).decode("utf-8"),
    )


def badan_pembuatan_agen(
    id_agen: str,
    saldo_teks: str,
    privat_base64: str,
    publik_base64: str,
) -> dict[str, Any]:
    stempel = stempel_iso_utc()
    pesan = {
        "agent_id": id_agen,
        "initial_balance": saldo_teks,
        "public_key": publik_base64,
        "timestamp": stempel,
    }
    tanda = tanda_dengan_kunci_privat(privat_base64, pesan)
    return {**pesan, "signature": tanda}


def badan_transaksi_baru(
    dari_agen: str,
    ke_agen: str,
    jumlah_teks: str,
    privat_pengirim_base64: str,
    nonce_unik: str | None = None,
) -> dict[str, Any]:
    nonce = nonce_unik or str(uuid4())
    stempel = stempel_iso_utc()
    pesan = {
        "from_agent": dari_agen,
        "to_agent": ke_agen,
        "amount": jumlah_teks,
        "nonce": nonce,
        "timestamp": stempel,
    }
    tanda = tanda_dengan_kunci_privat(privat_pengirim_base64, pesan)
    return {**pesan, "signature": tanda}


def badan_aksi_transaksi(
    privat_base64: str,
    id_agen: str,
    id_transaksi: str,
) -> dict[str, Any]:
    nonce = str(uuid4())
    stempel = stempel_iso_utc()
    pesan: dict[str, Any] = {
        "agent_id": id_agen,
        "transaction_id": id_transaksi,
        "nonce": nonce,
        "timestamp": stempel,
    }
    tanda = tanda_dengan_kunci_privat(privat_base64, pesan)
    return {**pesan, "signature": tanda}


# --- Klien HTTP AgentPay dengan retry ---


@dataclass
class CatatanApi:
    """Log permintaan untuk ditampilkan di demo."""

    daftar_log: list[str] = field(default_factory=list)

    def catat(self, teks: str) -> None:
        self.daftar_log.append(teks)
        print(teks)


class KlienAgentPay:
    def __init__(
        self,
        url_dasar: str,
        catatan: CatatanApi,
        percobaan_maks: int = 5,
        backoff_awal_detik: float = 0.4,
    ) -> None:
        self.url_dasar = url_dasar.rstrip("/")
        self.sesi = requests.Session()
        self.sesi.headers.update({"Content-Type": "application/json"})
        self.catatan = catatan
        self.percobaan_maks = percobaan_maks
        self.backoff_awal_detik = backoff_awal_detik

    def _tunggu_acak(self, percobaan: int) -> None:
        dasar = self.backoff_awal_detik * (2**percobaan)
        jitter = random.uniform(0, 0.25)
        time.sleep(min(dasar + jitter, 8.0))

    def _lakukan(
        self,
        metode: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        url = f"{self.url_dasar}{path}"
        galat_terakhir: Exception | None = None
        for percobaan in range(self.percobaan_maks):
            try:
                self.catatan.catat(
                    f"  [HTTP] {metode} {url}"
                    + (f" params={params}" if params else "")
                    + (f" body_keys={list(json_body.keys())}" if json_body else "")
                )
                if metode == "GET":
                    r = self.sesi.get(url, params=params, timeout=45)
                elif metode == "POST":
                    r = self.sesi.post(url, json=json_body, timeout=45)
                else:
                    raise ValueError(f"Metode tidak didukung: {metode}")

                if r.status_code in (429, 502, 503, 504) and percobaan < self.percobaan_maks - 1:
                    self.catatan.catat(
                        f"  [HTTP] status {r.status_code}, retry {percobaan + 1}/{self.percobaan_maks}"
                    )
                    self._tunggu_acak(percobaan)
                    continue
                potong = r.text[:800] + ("..." if len(r.text) > 800 else "")
                self.catatan.catat(f"  [HTTP] <- {r.status_code} {potong}")
                return r
            except requests.RequestException as exc:
                galat_terakhir = exc
                self.catatan.catat(f"  [HTTP] galat jaringan: {exc} (retry {percobaan + 1})")
                if percobaan < self.percobaan_maks - 1:
                    self._tunggu_acak(percobaan)
        assert galat_terakhir is not None
        raise galat_terakhir

    def daftar_transaksi(self, id_agen: str | None = None, status: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if id_agen:
            params["agent_id"] = id_agen
        if status:
            params["status"] = status
        r = self._lakukan("GET", "/transactions", params=params or None)
        r.raise_for_status()
        return r.json()

    def buat_transaksi(self, muatan: dict[str, Any]) -> dict[str, Any]:
        r = self._lakukan("POST", "/transactions", json_body=muatan)
        r.raise_for_status()
        return r.json()

    def terima_transaksi(self, id_transaksi: str, muatan: dict[str, Any]) -> dict[str, Any]:
        r = self._lakukan("POST", f"/transactions/{id_transaksi}/accept", json_body=muatan)
        r.raise_for_status()
        return r.json()

    def konfirmasi_transaksi(self, id_transaksi: str, muatan: dict[str, Any]) -> dict[str, Any]:
        r = self._lakukan("POST", f"/transactions/{id_transaksi}/confirm", json_body=muatan)
        r.raise_for_status()
        return r.json()

    def saldo(self, id_agen: str) -> dict[str, Any]:
        r = self._lakukan("GET", f"/agents/{id_agen}/balance")
        r.raise_for_status()
        return r.json()


# --- Katalog layanan (simulasi marketplace; AgentPay inti tidak punya GET /services) ---

KATALOG_LAYANAN_DEMO = {
    "layanan": [
        {
            "id": "cuaca_jakarta_realtime",
            "nama": "Data cuaca Jakarta (JSON)",
            "penyedia_agent_id": "seller",
            "harga_minta_usd": Decimal("5.00"),
            "mata_uang": "USD",
            "catatan": "Snapshot suhu, kelembaban, angin; diperbarui tiap jam.",
        }
    ]
}


def bangun_tools_pembeli(id_penjual: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "katalog_layanan_tersedia",
            "description": (
                "Mengambil daftar layanan data yang dijual agen terdaftar di AgentPay "
                "(demo: satu penyedia cuaca Jakarta)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "negosiasi_setujui_harga",
            "description": (
                "Mencatat hasil negosiasi harga dengan penyedia. "
                f"Penjual terdaftar sebagai agent_id '{id_penjual}' dengan harga $5."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "harga_penawaran_awal": {"type": "number", "description": "Angka tawar pembeli"},
                    "harga_disepakati": {"type": "number", "description": "Harga final yang disetujui kedua pihak"},
                    "alasan": {"type": "string"},
                },
                "required": ["harga_disepakati"],
            },
        },
        {
            "name": "pembayaran_buat",
            "description": "Membuat pembayaran escrow via POST /transactions (ditandatangani kunci pembeli).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ke_agent_id": {"type": "string"},
                    "jumlah_usd": {"type": "string", "description": 'String desimal, mis. "5.00"'},
                },
                "required": ["ke_agent_id", "jumlah_usd"],
            },
        },
        {
            "name": "transaksi_ambil_status",
            "description": "Mengambil detail satu transaksi untuk debugging.",
            "input_schema": {
                "type": "object",
                "properties": {"id_transaksi": {"type": "string", "format": "uuid"}},
                "required": ["id_transaksi"],
            },
        },
        {
            "name": "pembayaran_konfirmasi_penerimaan",
            "description": "Mengonfirmasi barang/layanan diterima: POST /transactions/{id}/confirm",
            "input_schema": {
                "type": "object",
                "properties": {"id_transaksi": {"type": "string"}},
                "required": ["id_transaksi"],
            },
        },
        {
            "name": "saldo_saya",
            "description": "Membaca saldo agent pembeli saat ini.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def bangun_tools_penjual() -> list[dict[str, Any]]:
    return [
        {
            "name": "pantau_pembayaran_masuk",
            "description": "Memantau transaksi yang melibatkan agen penjual (GET /transactions?agent_id=seller).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filter_status": {
                        "type": "string",
                        "description": "Opsional: INITIATED, PENDING, dll.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "pembayaran_terima",
            "description": "Menerima pembayaran escrow: POST /transactions/{id}/accept",
            "input_schema": {
                "type": "object",
                "properties": {"id_transaksi": {"type": "string"}},
                "required": ["id_transaksi"],
            },
        },
        {
            "name": "kirim_data_cuaca_jakarta",
            "description": (
                "Mengirim payload data cuaca Jakarta (JSON) ke pembeli setelah pembayaran diterima (di luar rantai on-chain)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "id_transaksi": {"type": "string"},
                    "suhu_c": {"type": "number"},
                    "kelembaban_persen": {"type": "number"},
                    "kondisi": {"type": "string"},
                },
                "required": ["id_transaksi", "suhu_c", "kelembaban_persen", "kondisi"],
            },
        },
    ]


def jalankan_siklus_tools(
    klien_anthropic: Anthropic,
    nama_model: str,
    sistem: str,
    pesan_user: str,
    tools: list[dict[str, Any]],
    penangan_tool: Any,
    catatan: CatatanApi,
    langkah_maks: int = 14,
) -> str:
    """
    Menjalankan satu fase agen dengan tool_use hingga selesai atau batas langkah.
    Mengembalikan teks penutup terakhir dari asisten.
    """
    pesan: list[dict[str, Any]] = [{"role": "user", "content": pesan_user}]
    teks_akhir = ""

    for langkah in range(langkah_maks):
        catatan.catat(f"\n--- Claude ({nama_model}) langkah {langkah + 1} ---")
        respons = klien_anthropic.messages.create(
            model=nama_model,
            max_tokens=4096,
            system=sistem,
            tools=tools,
            messages=pesan,
        )

        blok_teks: list[str] = []
        for blok in respons.content:
            if blok.type == "text":
                blok_teks.append(blok.text)
            elif getattr(blok, "type", None) == "thinking" and hasattr(blok, "thinking"):
                blok_teks.append(f"[thinking] {blok.thinking}")

        if blok_teks:
            gabung = "\n".join(blok_teks)
            teks_akhir = gabung
            catatan.catat("  [Pemikiran / jawaban agen]\n" + gabung)

        ada_tool = any(b.type == "tool_use" for b in respons.content)
        konten_asisten: list[dict[str, Any]] = []
        untuk_tool_results: list[dict[str, Any]] = []

        for blok in respons.content:
            if blok.type == "text":
                konten_asisten.append({"type": "text", "text": blok.text})
            elif blok.type == "tool_use":
                konten_asisten.append(
                    {
                        "type": "tool_use",
                        "id": blok.id,
                        "name": blok.name,
                        "input": blok.input,
                    }
                )
                catatan.catat(f"  [Tool dipanggil] {blok.name}({json.dumps(blok.input, ensure_ascii=False)})")
                hasil = penangan_tool(blok.name, blok.input if isinstance(blok.input, dict) else {})
                catatan.catat(f"  [Hasil tool] {hasil[:1200]}{'...' if len(hasil) > 1200 else ''}")
                untuk_tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": blok.id,
                        "content": hasil,
                    }
                )

        if not konten_asisten:
            break

        pesan.append({"role": "assistant", "content": konten_asisten})

        if ada_tool and untuk_tool_results:
            pesan.append({"role": "user", "content": untuk_tool_results})
            continue

        # Tidak ada tool: percakapan fase ini selesai
        break

    return teks_akhir


def tunggu_backend_sehat(url_host: str, detik_maks: int = 90) -> None:
    mulai = time.monotonic()
    while time.monotonic() - mulai < detik_maks:
        try:
            r = requests.get(f"{url_host.rstrip('/')}/health", timeout=3)
            if r.status_code == 200:
                print(f"Backend siap: {url_host}/health")
                return
        except requests.RequestException:
            pass
        time.sleep(1.2)
    print(
        f"Peringatan: /health tidak merespons OK dalam {detik_maks}s. "
        "Lanjut mencoba — pastikan AgentPay berjalan.",
        file=sys.stderr,
    )


def utama() -> None:
    kunci_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    if not kunci_anthropic:
        print("Set ANTHROPIC_API_KEY terlebih dahulu.", file=sys.stderr)
        sys.exit(1)

    url_host = os.environ.get("AGENTPAY_HOST", "http://127.0.0.1:8000").rstrip("/")
    prefiks_api = os.environ.get("AGENTPAY_API_PREFIX", "/api/v1")
    url_api = f"{url_host}{prefiks_api}"

    id_pembeli = os.environ.get("DEMO_BUYER_ID", "buyer")
    id_penjual = os.environ.get("DEMO_SELLER_ID", "seller")
    nama_model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    catatan = CatatanApi()
    klien_http = KlienAgentPay(url_api, catatan)
    klien_anthropic = Anthropic(api_key=kunci_anthropic)

    tunggu_backend_sehat(url_host)

    privat_pembeli, publik_pembeli = pasangan_kunci_baru()
    privat_penjual, publik_penjual = pasangan_kunci_baru()

    print("\n========== Pendaftaran agen (POST /agents) ==========")
    for id_agen, privat, publik, saldo in (
        (id_pembeli, privat_pembeli, publik_pembeli, "10.00"),
        (id_penjual, privat_penjual, publik_penjual, "0.00"),
    ):
        muatan = badan_pembuatan_agen(id_agen, saldo, privat, publik)
        try:
            r = klien_http.sesi.post(f"{url_api}/agents", json=muatan, timeout=30)
            catatan.catat(f"  POST /agents -> {r.status_code} {r.text[:400]}")
            if r.status_code == 409:
                print(
                    f"\nGagal: agen '{id_agen}' sudah ada dengan kunci lain. "
                    "Kosongkan DB demo atau set DEMO_BUYER_ID / DEMO_SELLER_ID ke id unik.\n",
                    file=sys.stderr,
                )
                sys.exit(2)
            r.raise_for_status()
        except requests.HTTPError:
            print(r.text, file=sys.stderr)
            raise

    # Status transaksi bersama (untuk penangan tool)
    id_transaksi_aktif: dict[str, str | None] = {"nilai": None}
    data_cuaca_terkirim: dict[str, Any] = {}

    def penangan_tool_pembeli(nama: str, argumen: dict[str, Any]) -> str:
        if nama == "katalog_layanan_tersedia":
            # Menyesuaikan id penyedia runtime
            salin = json.loads(json.dumps(KATALOG_LAYANAN_DEMO, default=str))
            for item in salin.get("layanan", []):
                item["penyedia_agent_id"] = id_penjual
            return json.dumps(salin, ensure_ascii=False, indent=2)

        if nama == "negosiasi_setujui_harga":
            catatan.catat(
                f"  [Negosiasi tercatat] disepakati=${argumen.get('harga_disepakati')} "
                f"(awal={argumen.get('harga_penawaran_awal')})"
            )
            return json.dumps(
                {
                    "status": "sepakat",
                    "harga_disepakati_usd": float(argumen.get("harga_disepakati", 5)),
                    "penjual": id_penjual,
                    "catatan": argumen.get("alasan", ""),
                },
                ensure_ascii=False,
            )

        if nama == "pembayaran_buat":
            muatan_tx = badan_transaksi_baru(
                id_pembeli,
                str(argumen.get("ke_agent_id", id_penjual)),
                str(argumen.get("jumlah_usd", "5.00")),
                privat_pembeli,
            )
            badan = klien_http.buat_transaksi(muatan_tx)
            id_transaksi_aktif["nilai"] = badan["id"]
            catatan.catat(f"  [Status transaksi] {json.dumps(badan, default=str)[:500]}")
            return json.dumps(badan, default=str)

        if nama == "transaksi_ambil_status":
            tid = str(argumen.get("id_transaksi", ""))
            r = klien_http._lakukan("GET", f"/transactions/{tid}")
            return r.text

        if nama == "pembayaran_konfirmasi_penerimaan":
            tid = str(argumen["id_transaksi"])
            muatan = badan_aksi_transaksi(privat_pembeli, id_pembeli, tid)
            badan = klien_http.konfirmasi_transaksi(tid, muatan)
            catatan.catat(f"  [Status setelah konfirmasi] {badan.get('status')}")
            return json.dumps(badan, default=str)

        if nama == "saldo_saya":
            badan = klien_http.saldo(id_pembeli)
            return json.dumps(badan, default=str)

        return json.dumps({"galat": "tool tidak dikenal", "nama": nama})

    def penangan_tool_penjual(nama: str, argumen: dict[str, Any]) -> str:
        if nama == "pantau_pembayaran_masuk":
            st = argumen.get("filter_status")
            badan = klien_http.daftar_transaksi(id_agen=id_penjual, status=st)
            catatan.catat(f"  [Daftar transaksi seller] total={badan.get('total')}")
            return json.dumps(badan, default=str)

        if nama == "pembayaran_terima":
            tid = str(argumen["id_transaksi"])
            muatan = badan_aksi_transaksi(privat_penjual, id_penjual, tid)
            badan = klien_http.terima_transaksi(tid, muatan)
            return json.dumps(badan, default=str)

        if nama == "kirim_data_cuaca_jakarta":
            payload = {
                "transaksi_id": argumen.get("id_transaksi"),
                "kota": "Jakarta",
                "suhu_celsius": argumen.get("suhu_c"),
                "kelembaban_persen": argumen.get("kelembaban_persen"),
                "kondisi": argumen.get("kondisi"),
                "diperbarui": stempel_iso_utc(),
                "format": "agentpay_demo_v1",
            }
            data_cuaca_terkirim.clear()
            data_cuaca_terkirim.update(payload)
            return json.dumps(
                {"status": "terkirim_ke_pembeli", "payload": payload},
                ensure_ascii=False,
            )

        return json.dumps({"galat": "tool tidak dikenal", "nama": nama})

    sistem_pembeli = (
        "You are a data buyer agent. You need weather data for Jakarta. "
        "You have $10 budget. Use AgentPay API to purchase data from provider agents.\n"
        "You must: query available services (via tool), negotiate price, "
        "create payment via POST /transactions (tool pembayaran_buat), "
        "and after you receive the data, confirm delivery via pembayaran_konfirmasi_penerimaan.\n"
        "Be concise in reasoning. Agree to a fair price ($5) if negotiation aligns with catalog."
    )

    sistem_penjual = (
        "You are a weather data provider. You sell Jakarta weather data for $5. "
        "Monitor AgentPay for incoming payments and deliver data when payment is accepted.\n"
        "You must: monitor with pantau_pembayaran_masuk (GET /transactions?agent_id=seller), "
        "accept via pembayaran_terima (POST .../accept), then deliver JSON weather via kirim_data_cuaca_jakarta.\n"
        "Respond professionally and show autonomous decision-making."
    )

    print("\n========== Percakapan: Agent A memulai ==========")
    percakapan_pembuka = klien_anthropic.messages.create(
        model=nama_model,
        max_tokens=1024,
        system=sistem_pembeli,
        messages=[
            {
                "role": "user",
                "content": "Mulai percakapan singkat dengan penjual data cuaca: sapa dan sebutkan kebutuhanmu.",
            }
        ],
    )
    teks_a = ""
    for blok in percakapan_pembuka.content:
        if blok.type == "text":
            teks_a = blok.text
            print(f"\n[Agent A — pemikiran / pesan]\n{blok.text}")

    print("\n========== Percakapan: Agent B menjawab ==========")
    percakapan_penjual = klien_anthropic.messages.create(
        model=nama_model,
        max_tokens=1024,
        system=sistem_penjual,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Pembeli (Agent A) mengatakan:\n{teks_a}\n\n"
                    "Balas singkat: konfirmasi harga $5 dan kesiapan mengirim data setelah pembayaran."
                ),
            }
        ],
    )
    for blok in percakapan_penjual.content:
        if blok.type == "text":
            print(f"\n[Agent B — pemikiran / pesan]\n{blok.text}")

    def cetak_status_transaksi(label: str) -> None:
        tid = id_transaksi_aktif.get("nilai")
        if not tid:
            return
        try:
            r = klien_http._lakukan("GET", f"/transactions/{tid}")
            if r.ok:
                badan = r.json()
                catatan.catat(
                    f"\n>>> [{label}] transaksi {tid} status={badan.get('status')}"
                )
        except requests.RequestException as exc:
            catatan.catat(f"\n>>> [{label}] gagal baca status: {exc}")

    print("\n========== Agent A: katalog, negosiasi, pembayaran ==========")
    jalankan_siklus_tools(
        klien_anthropic,
        nama_model,
        sistem_pembeli,
        (
            "Lanjutkan alur pembelian: gunakan tool. "
            f"Penjual terdaftar sebagai agent_id '{id_penjual}'. "
            "Setelah negosiasi, bayar tepat sesuai harga yang disepakati (gunakan string desimal). "
            "Setelah itu berhenti memanggil tool sampai data diterima (fase berikutnya)."
        ),
        bangun_tools_pembeli(id_penjual),
        penangan_tool_pembeli,
        catatan,
    )

    id_tx = id_transaksi_aktif.get("nilai")
    if not id_tx:
        print("Demo gagal: tidak ada transaksi yang dibuat.", file=sys.stderr)
        sys.exit(3)

    cetak_status_transaksi("setelah pembayaran dibuat")

    print("\n========== Agent B: pantau, terima, kirim data ==========")
    jalankan_siklus_tools(
        klien_anthropic,
        nama_model,
        sistem_penjual,
        (
            f"Ada transaksi aktif id {id_tx}. "
            "Pantau pembayaran masuk, terima transaksi INITIATED tersebut, lalu kirim data cuaca Jakarta (realistis)."
        ),
        bangun_tools_penjual(),
        penangan_tool_penjual,
        catatan,
    )

    cetak_status_transaksi("setelah penjual terima & mengirim data")

    print("\n========== Agent A: konfirmasi penerimaan ==========")
    jalankan_siklus_tools(
        klien_anthropic,
        nama_model,
        sistem_pembeli,
        (
            f"Data cuaca telah dikirim penjual (payload demo: {json.dumps(data_cuaca_terkirim, ensure_ascii=False)[:400]}). "
            f"Konfirmasi penerimaan untuk transaksi {id_tx} agar settlement selesai."
        ),
        bangun_tools_pembeli(id_penjual),
        penangan_tool_pembeli,
        catatan,
    )

    cetak_status_transaksi("setelah pembeli konfirmasi (settlement)")

    print("\n========== Saldo akhir ==========")
    saldo_a = klien_http.saldo(id_pembeli)
    saldo_b = klien_http.saldo(id_penjual)
    print(json.dumps({"buyer": saldo_a, "seller": saldo_b}, indent=2, default=str))

    badan_akhir = klien_http.daftar_transaksi(id_agen=id_pembeli)
    if badan_akhir.get("items"):
        terbaru = badan_akhir["items"][0]
        catatan.catat(
            f"\n[Transaksi terbaru pembeli] status={terbaru.get('status')} id={terbaru.get('id')}"
        )

    print(
        "\n*** Transaction settled! Agent A received data, Agent B received payment ***\n"
        "Transaction settled! Agent A received data, Agent B received payment"
    )


if __name__ == "__main__":
    try:
        utama()
    except KeyboardInterrupt:
        print("\nDibatalkan pengguna.", file=sys.stderr)
        sys.exit(130)
