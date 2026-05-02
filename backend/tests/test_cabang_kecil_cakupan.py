"""Beberapa assert ringan untuk menaikkan cakupan cabang yang tipis."""

from __future__ import annotations

import base64
from decimal import Decimal

import pytest

from app.crypto import Ed25519Crypto
from app.routes.agents import layanan_simpan_agent
from app.schemas import AgentCreateSigned
from app.utils.exceptions import InvalidAmountException

from tests.bantuan_tanda import body_pembuatan_agen_tertanda


def test_invalid_amount_exception_menyimpan_pesan() -> None:
    galat = InvalidAmountException("nilai tidak wajar")
    assert "tidak wajar" in str(galat)


@pytest.mark.asyncio
async def test_layanan_simpan_agent_public_key_bukan_base64(pabrik_sesi_uji):
    muatan = AgentCreateSigned.model_construct(
        agent_id="agen_b64x",
        initial_balance=Decimal("1"),
        public_key="bukan_base64_valid",
        signature="x",
    )
    async with pabrik_sesi_uji() as sesi:
        with pytest.raises(ValueError, match="Base64"):
            await layanan_simpan_agent(sesi, muatan)


@pytest.mark.asyncio
async def test_layanan_simpan_agent_panjang_kunci_salah(pabrik_sesi_uji):
    kunci_salah_panjang = base64.b64encode(b"x" * 31).decode("ascii")
    muatan = AgentCreateSigned.model_construct(
        agent_id="agen_len31",
        initial_balance=Decimal("1"),
        public_key=kunci_salah_panjang,
        signature="x",
    )
    async with pabrik_sesi_uji() as sesi:
        with pytest.raises(ValueError, match="32 byte"):
            await layanan_simpan_agent(sesi, muatan)


@pytest.mark.asyncio
async def test_get_balance_setelah_daftar(client_api):
    privat, publik = Ed25519Crypto.generate_keypair()
    nama = "agen_saldo_cepat"
    buat = await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda(nama, "42.50", privat, publik),
    )
    assert buat.status_code == 201

    respons = await client_api.get(f"/api/v1/agents/{nama}/balance")
    assert respons.status_code == 200
    data = respons.json()
    assert data["agent_id"] == nama
    assert data["balance"] in ("42.5", "42.50", "42.50000000")
