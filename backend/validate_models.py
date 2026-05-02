#!/usr/bin/env python3
"""Memeriksa metadata tabel ORM (jalankan dari folder backend)."""

import asyncio

from sqlalchemy import inspect

from app.database import Base, engine


async def utama() -> None:
    async with engine.connect() as koneksi:

        def periksa(sync_conn) -> None:
            pemeriksa = inspect(sync_conn)
            for nama_tabel in Base.metadata.tables.keys():
                print(f"Tabel: {nama_tabel}")
                if nama_tabel in pemeriksa.get_table_names():
                    kolom = pemeriksa.get_columns(nama_tabel)
                    print(f"  Kolom: {len(kolom)}")
                else:
                    print("  (belum ada di basis data — jalankan alembic upgrade)")

        await koneksi.run_sync(periksa)


if __name__ == "__main__":
    asyncio.run(utama())
