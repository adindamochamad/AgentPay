import base64
from datetime import datetime, timedelta, timezone

import pytest

from app.crypto import Ed25519Crypto


def test_generate_keypair():
    privat, publik = Ed25519Crypto.generate_keypair()
    assert len(base64.b64decode(privat)) == 32
    assert len(base64.b64decode(publik)) == 32


def test_sign_and_verify():
    privat, publik = Ed25519Crypto.generate_keypair()
    pesan = {"from": "alice", "to": "bob", "amount": 10}
    tanda = Ed25519Crypto.sign_message(privat, pesan)
    assert Ed25519Crypto.verify_signature(publik, pesan, tanda)


def test_invalid_signature_rejected():
    _, publik = Ed25519Crypto.generate_keypair()
    privat2, _ = Ed25519Crypto.generate_keypair()
    pesan = {"from": "alice", "to": "bob", "amount": 10}
    tanda = Ed25519Crypto.sign_message(privat2, pesan)
    assert not Ed25519Crypto.verify_signature(publik, pesan, tanda)


def test_message_tampering_detected():
    privat, publik = Ed25519Crypto.generate_keypair()
    pesan = {"from": "alice", "to": "bob", "amount": 10}
    tanda = Ed25519Crypto.sign_message(privat, pesan)
    dirusak = {"from": "alice", "to": "bob", "amount": 100}
    assert not Ed25519Crypto.verify_signature(publik, dirusak, tanda)


@pytest.mark.asyncio
async def test_timestamp_lama_ditolak(client_api):
    """Permintaan dengan timestamp lebih dari 5 menit harus ditolak (anti-replay)."""
    privat, publik = Ed25519Crypto.generate_keypair()
    stempel_lama = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    pesan = {
        "agent_id": "agen_timestamp_lama",
        "initial_balance": "1.00",
        "public_key": publik,
        "timestamp": stempel_lama,
    }
    tanda = Ed25519Crypto.sign_message(privat, pesan)
    respons = await client_api.post("/api/v1/agents", json={**pesan, "signature": tanda})
    assert respons.status_code == 400
    assert "lama" in respons.json()["detail"].lower() or "timestamp" in respons.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tanda_salah_ditolak_unauthorized(client_api):
    """Tanda yang tidak cocok dengan kunci publik harus 401."""
    privat_benar, publik = Ed25519Crypto.generate_keypair()
    privat_salah, _ = Ed25519Crypto.generate_keypair()
    stempel = datetime.now(timezone.utc).isoformat()
    pesan = {
        "agent_id": "agen_tanda_salah",
        "initial_balance": "5.00",
        "public_key": publik,
        "timestamp": stempel,
    }
    tanda_salah = Ed25519Crypto.sign_message(privat_salah, pesan)
    respons = await client_api.post("/api/v1/agents", json={**pesan, "signature": tanda_salah})
    assert respons.status_code == 401
