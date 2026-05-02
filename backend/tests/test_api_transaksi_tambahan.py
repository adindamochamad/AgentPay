"""Endpoint transaksi tambahan untuk cakupan cabang yang jarang terpanggil."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.crypto import Ed25519Crypto

from tests.bantuan_tanda import (
    body_aksi_transaksi_tertanda,
    body_pembuatan_agen_tertanda,
    body_transaksi_tertanda,
)


@pytest.mark.asyncio
async def test_ambil_transaksi_tidak_ada(client_api):
    respons = await client_api.get(f"/api/v1/transactions/{uuid4()}")
    assert respons.status_code == 404


@pytest.mark.asyncio
async def test_daftar_transaksi_berdasarkan_agen(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_fta", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_ftb", "10.00", privat_r, publik_r),
    )
    await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("agen_fta", "agen_ftb", "3.00", privat_p),
    )

    respons = await client_api.get("/api/v1/transactions", params={"agent_id": "agen_fta"})
    assert respons.status_code == 200
    assert respons.json()["total"] >= 1


@pytest.mark.asyncio
async def test_daftar_transaksi_agen_tidak_dikenal(client_api):
    respons = await client_api.get("/api/v1/transactions", params={"agent_id": "tidak_ada_xyz"})
    assert respons.status_code == 404


@pytest.mark.asyncio
async def test_idempotensi_kembalikan_transaksi_sama(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_idp", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_idq", "10.00", privat_r, publik_r),
    )
    kunci = "idem-uji-satu"
    badan = body_transaksi_tertanda("agen_idp", "agen_idq", "4.00", privat_p)
    pertama = await client_api.post(
        "/api/v1/transactions",
        json=badan,
        headers={"Idempotency-Key": kunci},
    )
    assert pertama.status_code == 201
    id_pertama = pertama.json()["id"]
    kedua = await client_api.post(
        "/api/v1/transactions",
        json=badan,
        headers={"Idempotency-Key": kunci},
    )
    assert kedua.status_code == 201
    assert kedua.json()["id"] == id_pertama


@pytest.mark.asyncio
async def test_batal_gagal_setelah_settled(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_bs", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_bt", "10.00", privat_r, publik_r),
    )
    buat = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("agen_bs", "agen_bt", "9.00", privat_p),
    )
    id_txn = UUID(buat.json()["id"])
    await client_api.post(
        f"/api/v1/transactions/{id_txn}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "agen_bt", id_txn),
    )
    await client_api.post(
        f"/api/v1/transactions/{id_txn}/confirm",
        json=body_aksi_transaksi_tertanda(privat_p, "agen_bs", id_txn),
    )

    respons = await client_api.post(
        f"/api/v1/transactions/{id_txn}/cancel",
        json=body_aksi_transaksi_tertanda(privat_p, "agen_bs", id_txn),
    )
    assert respons.status_code == 400
