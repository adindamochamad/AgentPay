"""Pengujian utilitas modul database."""

import pytest

from app.database import ambil_statistik_pool_database, cek_kesehatan_koneksi_database


@pytest.mark.asyncio
async def test_cek_kesehatan_koneksi_database() -> None:
    sehat = await cek_kesehatan_koneksi_database()
    assert sehat is True


def test_ambil_statistik_pool_database() -> None:
    stat = ambil_statistik_pool_database()
    assert "ukuran_konfigurasi" in stat
