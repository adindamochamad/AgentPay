#!/usr/bin/env python3
"""Skrip cepat: uji koneksi basis data (async, jalankan dari folder backend)."""

import asyncio

from app.database import ambil_statistik_pool_database, cek_kesehatan_koneksi_database


async def utama() -> None:
    if await cek_kesehatan_koneksi_database():
        print("Koneksi basis data: OK")
        print(f"Statistik pool: {ambil_statistik_pool_database()}")
    else:
        print("Koneksi basis data: GAGAL")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(utama())
