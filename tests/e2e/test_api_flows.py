"""Alur API end-to-end terhadap stack yang sedang berjalan."""

from __future__ import annotations

import concurrent.futures
import time
from uuid import uuid4

import pytest

from tanda_helper import (
    badan_aksi_transaksi,
    badan_pembuatan_agen,
    badan_transaksi_baru,
    pasangan_kunci_baru,
    tanda_dengan_kunci_privat,
)


def test_kesehatan_ringkas(klien_http: requests.Session, url_dasar_api: str) -> None:
    r = klien_http.get(f"{url_dasar_api}/health", timeout=10)
    assert r.status_code == 200
    badan = r.json()
    assert badan.get("status") == "ok"


def test_kesehatan_mendalam(klien_http: requests.Session, url_dasar_api: str) -> None:
    r = klien_http.get(f"{url_dasar_api}/health/deep", timeout=15)
    assert r.status_code == 200
    badan = r.json()
    assert badan.get("status") in ("healthy", "degraded", "unhealthy")
    cek = badan.get("checks", {})
    assert cek.get("database", {}).get("ok") is True
    assert cek.get("redis", {}).get("ok") is True


def test_alur_pembuatan_agen(
    klien_http: requests.Session,
    prefiks_api_v1: str,
) -> None:
    privat, publik = pasangan_kunci_baru()
    id_agen = f"e2e_c_{uuid4().hex[:10]}"
    muatan = badan_pembuatan_agen(id_agen, "50.00", privat, publik)
    r = klien_http.post(f"{prefiks_api_v1}/agents", json=muatan, timeout=30)
    assert r.status_code == 201, r.text
    saldo = klien_http.get(f"{prefiks_api_v1}/agents/{id_agen}/balance", timeout=10)
    assert saldo.status_code == 200
    assert saldo.json()["balance"] == "50.00000000"


def test_alur_pembayaran_lengkap_hingga_settled(
    klien_http: requests.Session,
    prefiks_api_v1: str,
    sepasang_agen_siap: dict,
) -> None:
    d = sepasang_agen_siap
    muatan_tx = badan_transaksi_baru(
        d["id_pengirim"],
        d["id_penerima"],
        "12.50",
        d["privat_pengirim"],
    )
    r_tx = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan_tx, timeout=30)
    assert r_tx.status_code == 201, r_tx.text
    id_tx = r_tx.json()["id"]

    muatan_terima = badan_aksi_transaksi(d["privat_penerima"], d["id_penerima"], id_tx)
    r1 = klien_http.post(f"{prefiks_api_v1}/transactions/{id_tx}/accept", json=muatan_terima, timeout=30)
    assert r1.status_code == 200, r1.text

    muatan_konfirm = badan_aksi_transaksi(d["privat_pengirim"], d["id_pengirim"], id_tx)
    r2 = klien_http.post(f"{prefiks_api_v1}/transactions/{id_tx}/confirm", json=muatan_konfirm, timeout=30)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "SETTLED"


def test_pembatalan_transaksi(
    klien_http: requests.Session,
    prefiks_api_v1: str,
    sepasang_agen_siap: dict,
) -> None:
    d = sepasang_agen_siap
    muatan_tx = badan_transaksi_baru(
        d["id_pengirim"],
        d["id_penerima"],
        "1.00",
        d["privat_pengirim"],
    )
    r_tx = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan_tx, timeout=30)
    assert r_tx.status_code == 201, r_tx.text
    id_tx = r_tx.json()["id"]
    muatan_batal = badan_aksi_transaksi(d["privat_pengirim"], d["id_pengirim"], id_tx)
    r_b = klien_http.post(f"{prefiks_api_v1}/transactions/{id_tx}/cancel", json=muatan_batal, timeout=30)
    assert r_b.status_code == 200, r_b.text
    assert r_b.json()["status"] == "ROLLED_BACK"


def test_saldo_tidak_mencukupi(
    klien_http: requests.Session,
    prefiks_api_v1: str,
) -> None:
    privat_a, publik_a = pasangan_kunci_baru()
    privat_b, publik_b = pasangan_kunci_baru()
    id_a = f"e2e_d_{uuid4().hex[:8]}"
    id_b = f"e2e_e_{uuid4().hex[:8]}"
    for id_agen, privat, publik, saldo in (
        (id_a, privat_a, publik_a, "1.00"),
        (id_b, privat_b, publik_b, "100.00"),
    ):
        muatan = badan_pembuatan_agen(id_agen, saldo, privat, publik)
        assert klien_http.post(f"{prefiks_api_v1}/agents", json=muatan, timeout=30).status_code == 201

    muatan_tx = badan_transaksi_baru(id_a, id_b, "9999.00", privat_a)
    r = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan_tx, timeout=30)
    assert r.status_code == 409
    assert "balance" in r.text.lower() or "saldo" in r.text.lower() or "Insufficient" in r.text


def test_transaksi_bersamaan_ringan(
    klien_http: requests.Session,
    prefiks_api_v1: str,
    sepasang_agen_siap: dict,
) -> None:
    d = sepasang_agen_siap

    def satu_permintaan(_: int) -> int:
        muatan = badan_transaksi_baru(
            d["id_pengirim"],
            d["id_penerima"],
            "0.01",
            d["privat_pengirim"],
        )
        resp = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan, timeout=60)
        return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as eksekutor:
        kode = list(eksekutor.map(satu_permintaan, range(8)))

    assert all(k == 201 for k in kode), f"kode status tidak konsisten: {kode}"


def test_transaksi_kedaluwarsa_saat_diterima(
    klien_http: requests.Session,
    prefiks_api_v1: str,
    sepasang_agen_siap: dict,
) -> None:
    """Membutuhkan backend dengan TRANSACTION_TIMEOUT_HOURS sangat kecil (lihat docker-compose.e2e.yml)."""
    d = sepasang_agen_siap
    muatan_tx = badan_transaksi_baru(
        d["id_pengirim"],
        d["id_penerima"],
        "2.00",
        d["privat_pengirim"],
    )
    r_tx = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan_tx, timeout=30)
    assert r_tx.status_code == 201, r_tx.text
    id_tx = r_tx.json()["id"]
    time.sleep(0.35)
    muatan_terima = badan_aksi_transaksi(d["privat_penerima"], d["id_penerima"], id_tx)
    r1 = klien_http.post(f"{prefiks_api_v1}/transactions/{id_tx}/accept", json=muatan_terima, timeout=30)
    if r1.status_code == 200:
        pytest.skip("timeout transaksi belum lewat — naikkan stack dengan docker-compose.e2e.yml")
    assert r1.status_code == 409


def test_tanda_tidak_valid_ditolak(
    klien_http: requests.Session,
    prefiks_api_v1: str,
) -> None:
    privat, publik = pasangan_kunci_baru()
    id_agen = f"e2e_f_{uuid4().hex[:8]}"
    from tanda_helper import stempel_iso_utc

    stempel = stempel_iso_utc()
    pesan = {
        "agent_id": id_agen,
        "initial_balance": "10.00",
        "public_key": publik,
        "timestamp": stempel,
    }
    tanda_salah = tanda_dengan_kunci_privat(privat, {**pesan, "initial_balance": "9.99"})
    muatan = {**pesan, "signature": tanda_salah}
    r = klien_http.post(f"{prefiks_api_v1}/agents", json=muatan, timeout=30)
    assert r.status_code == 401


def test_replay_nonce_transaksi(
    klien_http: requests.Session,
    prefiks_api_v1: str,
    sepasang_agen_siap: dict,
) -> None:
    d = sepasang_agen_siap
    nonce_tetap = str(uuid4())
    muatan = badan_transaksi_baru(
        d["id_pengirim"],
        d["id_penerima"],
        "3.00",
        d["privat_pengirim"],
        nonce_unik=nonce_tetap,
    )
    r1 = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan, timeout=30)
    assert r1.status_code == 201, r1.text
    r2 = klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan, timeout=30)
    assert r2.status_code == 400
    assert "nonce" in r2.text.lower() or "replay" in r2.text.lower()


def test_paginasi_daftar_transaksi(
    klien_http: requests.Session,
    prefiks_api_v1: str,
    sepasang_agen_siap: dict,
) -> None:
    d = sepasang_agen_siap
    for _ in range(3):
        muatan = badan_transaksi_baru(
            d["id_pengirim"],
            d["id_penerima"],
            "0.02",
            d["privat_pengirim"],
        )
        assert klien_http.post(f"{prefiks_api_v1}/transactions", json=muatan, timeout=30).status_code == 201

    r = klien_http.get(
        f"{prefiks_api_v1}/transactions",
        params={"agent_id": d["id_pengirim"], "limit": 1, "offset": 0},
        timeout=30,
    )
    assert r.status_code == 200
    badan = r.json()
    assert badan["limit"] == 1
    assert badan["offset"] == 0
    assert len(badan["items"]) <= 1
    assert badan["total"] >= 1


def test_metrik_prometheus_terbaca(klien_http: requests.Session, url_dasar_api: str) -> None:
    r = klien_http.get(f"{url_dasar_api}/metrics", timeout=15)
    assert r.status_code == 200
    assert len(r.text) > 10
