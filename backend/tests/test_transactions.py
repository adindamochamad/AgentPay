from uuid import UUID

import pytest

from app.crypto import Ed25519Crypto

from tests.bantuan_tanda import (
    body_aksi_transaksi_tertanda,
    body_pembuatan_agen_tertanda,
    body_transaksi_tertanda,
)


@pytest.mark.asyncio
async def test_initiate_payment_berhasil(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("pengirim", "200.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("penerima", "10.00", privat_r, publik_r),
    )

    respons_transaksi = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("pengirim", "penerima", "35.50", privat_p),
    )

    assert respons_transaksi.status_code == 201
    data_transaksi = respons_transaksi.json()
    assert data_transaksi["status"] == "INITIATED"
    assert data_transaksi["from_agent"] == "pengirim"
    assert data_transaksi["to_agent"] == "penerima"


@pytest.mark.asyncio
async def test_initiate_payment_saldo_tidak_cukup(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("pengirim_kecil", "1.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("penerima_kecil", "1.00", privat_r, publik_r),
    )

    respons_transaksi = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("pengirim_kecil", "penerima_kecil", "5.00", privat_p),
    )

    assert respons_transaksi.status_code == 409


@pytest.mark.asyncio
async def test_accept_confirm_dan_get_transaction(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("pengirim_alur", "100.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("penerima_alur", "5.00", privat_r, publik_r),
    )

    respons_buat = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("pengirim_alur", "penerima_alur", "20.00", privat_p),
    )
    id_transaksi = UUID(respons_buat.json()["id"])

    respons_terima = await client_api.post(
        f"/api/v1/transactions/{id_transaksi}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "penerima_alur", id_transaksi),
    )
    assert respons_terima.status_code == 200
    assert respons_terima.json()["status"] == "PENDING"

    respons_konfirmasi = await client_api.post(
        f"/api/v1/transactions/{id_transaksi}/confirm",
        json=body_aksi_transaksi_tertanda(privat_p, "pengirim_alur", id_transaksi),
    )
    assert respons_konfirmasi.status_code == 200
    assert respons_konfirmasi.json()["status"] == "SETTLED"

    respons_detail = await client_api.get(f"/api/v1/transactions/{id_transaksi}")
    assert respons_detail.status_code == 200
    assert respons_detail.json()["status"] == "SETTLED"

    respons_saldo_penerima = await client_api.get("/api/v1/agents/penerima_alur/balance")
    assert respons_saldo_penerima.json()["balance"] == "25.00000000"


@pytest.mark.asyncio
async def test_accept_status_tidak_valid(client_api):
    privat_p, publik_p = Ed25519Crypto.generate_keypair()
    privat_r, publik_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("pengirim_validasi", "90.00", privat_p, publik_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("penerima_validasi", "0.00", privat_r, publik_r),
    )

    respons_buat = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("pengirim_validasi", "penerima_validasi", "10.00", privat_p),
    )
    id_transaksi = UUID(respons_buat.json()["id"])

    await client_api.post(
        f"/api/v1/transactions/{id_transaksi}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "penerima_validasi", id_transaksi),
    )
    respons_terima_ulang = await client_api.post(
        f"/api/v1/transactions/{id_transaksi}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "penerima_validasi", id_transaksi),
    )

    assert respons_terima_ulang.status_code == 400
