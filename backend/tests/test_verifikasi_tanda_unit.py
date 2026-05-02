"""Pengujian cabang verifikasi tanda (middleware) tanpa alur HTTP penuh."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.crypto import Ed25519Crypto
from app.middleware.signature_verification import (
    dependensi_pembuatan_agen,
    verifikasi_umum_timestamp_dan_tanda,
    waktu_utc_dari_iso,
)
from app.config import get_settings


def test_waktu_utc_dari_iso_dengan_z() -> None:
    hasil = waktu_utc_dari_iso("2020-01-01T12:00:00Z")
    assert hasil.tzinfo is not None
    assert hasil.hour == 12


def test_waktu_utc_dari_iso_naive_dianggap_utc() -> None:
    hasil = waktu_utc_dari_iso("2020-01-01T12:00:00")
    assert hasil.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_verifikasi_tanda_hilang_timestamp() -> None:
    _, publik = Ed25519Crypto.generate_keypair()
    with pytest.raises(HTTPException) as rekaman:
        await verifikasi_umum_timestamp_dan_tanda({"signature": "x"}, publik)
    assert rekaman.value.status_code == 400


@pytest.mark.asyncio
async def test_verifikasi_tanda_timestamp_invalid() -> None:
    _, publik = Ed25519Crypto.generate_keypair()
    with pytest.raises(HTTPException) as rekaman:
        await verifikasi_umum_timestamp_dan_tanda(
            {"signature": "x", "timestamp": "bukan-iso"}, publik
        )
    assert rekaman.value.status_code == 400


@pytest.mark.asyncio
async def test_verifikasi_tanda_terlalu_lama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIGNATURE_MAX_AGE_SECONDS", "120")
    get_settings.cache_clear()
    _, publik = Ed25519Crypto.generate_keypair()
    lampau = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
    with pytest.raises(HTTPException) as rekaman:
        await verifikasi_umum_timestamp_dan_tanda(
            {"signature": "x", "timestamp": lampau, "a": 1}, publik
        )
    assert rekaman.value.status_code == 400
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_verifikasi_tanda_di_masa_depan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIGNATURE_MAX_FUTURE_SKEW_SECONDS", "5")
    get_settings.cache_clear()
    _, publik = Ed25519Crypto.generate_keypair()
    depan = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    with pytest.raises(HTTPException) as rekaman:
        await verifikasi_umum_timestamp_dan_tanda(
            {"signature": "x", "timestamp": depan}, publik
        )
    assert rekaman.value.status_code == 400
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_verifikasi_tanda_tidak_cocok() -> None:
    _, publik = Ed25519Crypto.generate_keypair()
    stempel = datetime.now(timezone.utc).isoformat()
    with pytest.raises(HTTPException) as rekaman:
        await verifikasi_umum_timestamp_dan_tanda(
            {"signature": "tanda_salah", "timestamp": stempel, "x": 1}, publik
        )
    assert rekaman.value.status_code == 401


@pytest.mark.asyncio
async def test_dependensi_pembuatan_agen_json_bukan_objek() -> None:
    permintaan = MagicMock()
    permintaan.json = AsyncMock(return_value=["bukan", "dict"])
    with pytest.raises(HTTPException) as rekaman:
        await dependensi_pembuatan_agen(permintaan)
    assert rekaman.value.status_code == 400


@pytest.mark.asyncio
async def test_dependensi_pembuatan_agen_tanpa_public_key() -> None:
    permintaan = MagicMock()
    permintaan.json = AsyncMock(return_value={"agent_id": "x", "timestamp": "2020-01-01T00:00:00Z"})
    with pytest.raises(HTTPException) as rekaman:
        await dependensi_pembuatan_agen(permintaan)
    assert rekaman.value.status_code == 400


@pytest.mark.asyncio
async def test_dependensi_pembuatan_agen_json_tidak_valid() -> None:
    permintaan = MagicMock()
    permintaan.json = AsyncMock(side_effect=ValueError("rusak"))
    with pytest.raises(HTTPException) as rekaman:
        await dependensi_pembuatan_agen(permintaan)
    assert rekaman.value.status_code == 400
