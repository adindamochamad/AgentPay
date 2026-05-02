"""Pengujian daftar transaksi, batal, sengketa, dan filter status."""

from __future__ import annotations

from uuid import UUID

import pytest

from app.crypto import Ed25519Crypto

from tests.bantuan_tanda import (
    body_aksi_transaksi_tertanda,
    body_pembuatan_agen_tertanda,
    body_sengketa_tertanda,
    body_transaksi_tertanda,
)


@pytest.mark.asyncio
async def test_daftar_transaksi_dengan_filter_status(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_lp", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_lq", "10.00", privat_r, publik_r),
    )
    await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("agen_lp", "agen_lq", "5.00", privat_p),
    )

    respons = await client_api.get("/api/v1/transactions", params={"status": "INITIATED"})
    assert respons.status_code == 200
    muatan = respons.json()
    assert muatan["total"] >= 1
    assert all(baris["status"] == "INITIATED" for baris in muatan["items"])


@pytest.mark.asyncio
async def test_daftar_transaksi_status_tidak_valid(client_api):
    respons = await client_api.get("/api/v1/transactions", params={"status": "TIDAK_ADA"})
    assert respons.status_code == 422


@pytest.mark.asyncio
async def test_batal_transaksi_dari_pengirim(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_bp", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_bq", "10.00", privat_r, publik_r),
    )
    buat = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("agen_bp", "agen_bq", "8.00", privat_p),
    )
    id_txn = UUID(buat.json()["id"])

    respons_batal = await client_api.post(
        f"/api/v1/transactions/{id_txn}/cancel",
        json=body_aksi_transaksi_tertanda(privat_p, "agen_bp", id_txn, "Uji batal"),
    )
    assert respons_batal.status_code == 200
    assert respons_batal.json()["status"] == "ROLLED_BACK"


@pytest.mark.asyncio
async def test_sengketa_transaksi_dari_penerima(client_api, tmp_path, monkeypatch):
    jalur_log = tmp_path / "dispute_test.log"
    monkeypatch.setenv("DISPUTE_LOG_PATH", str(jalur_log))
    from app.config import get_settings

    get_settings.cache_clear()

    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_dp", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_dq", "10.00", privat_r, publik_r),
    )
    buat = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("agen_dp", "agen_dq", "6.00", privat_p),
    )
    id_txn = UUID(buat.json()["id"])
    await client_api.post(
        f"/api/v1/transactions/{id_txn}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "agen_dq", id_txn),
    )

    respons = await client_api.post(
        f"/api/v1/transactions/{id_txn}/dispute",
        json=body_sengketa_tertanda(privat_r, "agen_dq", id_txn, "Layanan tidak sesuai"),
    )
    assert respons.status_code == 200
    assert respons.json()["status"] == "ROLLED_BACK"
    assert jalur_log.read_text(encoding="utf-8")

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_agen_duplikat_mengembalikan_409(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    badan = body_pembuatan_agen_tertanda("agen_ganda", "1.00", privat, publik)
    pertama = await client_api.post("/api/v1/agents", json=badan)
    assert pertama.status_code == 201
    privat2, publik2 = Ed25519Crypto.generate_keypair()
    kedua = await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("agen_ganda", "2.00", privat2, publik2),
    )
    assert kedua.status_code == 409
