"""Kunci publik unik: percobaan kedua dengan kunci sama harus 409."""

from __future__ import annotations

import pytest

from app.crypto import Ed25519Crypto

from tests.bantuan_tanda import body_pembuatan_agen_tertanda


@pytest.mark.asyncio
async def test_kunci_publik_duplikat_menjadi_integrity(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    pertama = await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_kunci_a", "1.00", privat, publik),
    )
    assert pertama.status_code == 201

    kedua = await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_kunci_b", "2.00", privat, publik),
    )
    assert kedua.status_code == 409
