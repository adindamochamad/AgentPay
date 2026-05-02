"""Helper permintaan bertanda untuk pengujian API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.crypto import Ed25519Crypto


def muatan_iso_sekarang() -> str:
    return datetime.now(timezone.utc).isoformat()


def muatan_tanpa_tanda(body: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in body.items() if k != "signature"}


def pasangan_dari_fixture(nama_agen: str) -> tuple[str, str]:
    """Memuat private/public key dari tests/fixtures/{nama}_keypair.json."""
    jalur = Path(__file__).resolve().parent / "fixtures" / f"{nama_agen}_keypair.json"
    teks = jalur.read_text(encoding="utf-8")
    data = json.loads(teks)
    return str(data["private_key"]), str(data["public_key"])


def body_pembuatan_agen_tertanda(
    agent_id: str,
    saldo_teks: str,
    privat_base64: str,
    publik_base64: str,
) -> dict[str, Any]:
    """Membangun JSON POST /agents lengkap dengan tanda Ed25519."""
    stempel = muatan_iso_sekarang()
    pesan = {
        "agent_id": agent_id,
        "initial_balance": saldo_teks,
        "public_key": publik_base64,
        "timestamp": stempel,
    }
    tanda = Ed25519Crypto.sign_message(privat_base64, pesan)
    return {**pesan, "signature": tanda}


def body_transaksi_tertanda(
    dari_agent: str,
    ke_agent: str,
    jumlah_teks: str,
    privat_pengirim_base64: str,
    nonce: str | None = None,
) -> dict[str, Any]:
    """Membangun JSON POST /transactions lengkap dengan tanda dari pengirim."""
    nonce_aktual = nonce or str(uuid4())
    stempel = muatan_iso_sekarang()
    pesan = {
        "from_agent": dari_agent,
        "to_agent": ke_agent,
        "amount": jumlah_teks,
        "nonce": nonce_aktual,
        "timestamp": stempel,
    }
    tanda = Ed25519Crypto.sign_message(privat_pengirim_base64, pesan)
    return {**pesan, "signature": tanda}


def body_aksi_transaksi_tertanda(
    privat_base64: str,
    agent_id: str,
    id_transaksi: UUID,
    alasan_opsional: str | None = None,
) -> dict[str, Any]:
    """Membangun JSON untuk accept/confirm/cancel (tanda diverifikasi terhadap kunci publik di DB)."""
    nonce_aktual = str(uuid4())
    stempel = muatan_iso_sekarang()
    pesan: dict[str, Any] = {
        "agent_id": agent_id,
        "transaction_id": str(id_transaksi),
        "nonce": nonce_aktual,
        "timestamp": stempel,
    }
    if alasan_opsional is not None:
        pesan["reason"] = alasan_opsional
    tanda = Ed25519Crypto.sign_message(privat_base64, pesan)
    return {**pesan, "signature": tanda}


def body_sengketa_tertanda(
    privat_base64: str,
    agent_id: str,
    id_transaksi: UUID,
    teks_justifikasi: str,
) -> dict[str, Any]:
    nonce_aktual = str(uuid4())
    stempel = muatan_iso_sekarang()
    pesan = {
        "agent_id": agent_id,
        "transaction_id": str(id_transaksi),
        "justification": teks_justifikasi,
        "nonce": nonce_aktual,
        "timestamp": stempel,
    }
    tanda = Ed25519Crypto.sign_message(privat_base64, pesan)
    return {**pesan, "signature": tanda}
