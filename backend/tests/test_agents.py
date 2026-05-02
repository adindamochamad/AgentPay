import pytest

from app.crypto import Ed25519Crypto

from tests.bantuan_tanda import body_pembuatan_agen_tertanda


@pytest.mark.asyncio
async def test_create_agent_berhasil(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    muatan_json = body_pembuatan_agen_tertanda("agen_utama", "150.00", privat, publik)
    respons_buat = await client_api.post("/api/v1/agents", json=muatan_json)

    assert respons_buat.status_code == 201
    data_agent = respons_buat.json()
    assert data_agent["agent_id"] == "agen_utama"
    assert data_agent["balance"] == "150.00"


@pytest.mark.asyncio
async def test_create_agent_duplikat(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    muatan_pertama = body_pembuatan_agen_tertanda("agen_duplikat", "100.00", privat, publik)
    await client_api.post("/api/v1/agents", json=muatan_pertama)

    privat2, publik2 = Ed25519Crypto.generate_keypair()
    muatan_kedua = body_pembuatan_agen_tertanda("agen_duplikat", "200.00", privat2, publik2)
    respons_duplikat = await client_api.post("/api/v1/agents", json=muatan_kedua)

    assert respons_duplikat.status_code == 409
    assert "sudah ada" in respons_duplikat.json()["detail"]


@pytest.mark.asyncio
async def test_get_balance_berhasil(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    muatan = body_pembuatan_agen_tertanda("agen_saldo", "75.00", privat, publik)
    await client_api.post("/api/v1/agents", json=muatan)
    respons_saldo = await client_api.get("/api/v1/agents/agen_saldo/balance")

    assert respons_saldo.status_code == 200
    data_saldo = respons_saldo.json()
    assert data_saldo["agent_id"] == "agen_saldo"
    assert data_saldo["balance"] == "75.00000000"


@pytest.mark.asyncio
async def test_get_balance_agent_tidak_ditemukan(client_api):
    respons_saldo = await client_api.get("/api/v1/agents/agen_tidak_ada/balance")
    assert respons_saldo.status_code == 404
