"""Cabang error agen dan sengketa pada status yang salah."""

from __future__ import annotations

from uuid import UUID

import pytest

from app.crypto import Ed25519Crypto

from tests.bantuan_tanda import (
    body_pembuatan_agen_tertanda,
    body_sengketa_tertanda,
    body_transaksi_tertanda,
)


@pytest.mark.asyncio
async def test_pembuatan_agen_id_tidak_sesuai_pola(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    respons = await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("nama@tidak_valid", "1.00", privat, publik),
    )
    assert respons.status_code == 400


@pytest.mark.asyncio
async def test_saldo_agen_tidak_ditemukan(client_api):
    respons = await client_api.get("/api/v1/agents/tidak_pernah_daftar/balance")
    assert respons.status_code == 404


@pytest.mark.asyncio
async def test_sengketa_saat_masih_initiated_ditolak(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_sg1", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_sg2", "10.00", privat_r, publik_r),
    )
    buat = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("agen_sg1", "agen_sg2", "2.00", privat_p),
    )
    id_txn = UUID(buat.json()["id"])

    respons = await client_api.post(
        f"/api/v1/transactions/{id_txn}/dispute",
        json=body_sengketa_tertanda(privat_r, "agen_sg2", id_txn, "Terlalu cepat"),
    )
    assert respons.status_code == 400
