"""Penandatanganan Ed25519 kanonik untuk permintaan e2e (selaras dengan backend)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


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


def pasangan_kunci_baru() -> tuple[str, str]:
    kunci_privat = Ed25519PrivateKey.generate()
    byte_privat = kunci_privat.private_bytes_raw()
    byte_publik = kunci_privat.public_key().public_bytes_raw()
    return (
        base64.b64encode(byte_privat).decode("utf-8"),
        base64.b64encode(byte_publik).decode("utf-8"),
    )
