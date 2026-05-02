"""
Modul basis data AgentPay.

Engine async SQLAlchemy 2.0, pool, dan dependensi sesi untuk FastAPI.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

pengaturan = get_settings()
url_database_asinkron = pengaturan.ambil_url_database_async().replace(
    "postgresql+psycopg2://", "postgresql+asyncpg://"
)
url_database_asinkron = url_database_asinkron.replace("postgresql+psycopg://", "postgresql+asyncpg://")
url_database_asinkron = url_database_asinkron.replace("postgresql://", "postgresql+asyncpg://")

argumen_engine: dict[str, object] = {
    "pool_pre_ping": True,
    "echo": pengaturan.DATABASE_ECHO,
}

if not url_database_asinkron.startswith("sqlite"):
    argumen_engine["pool_size"] = pengaturan.DATABASE_POOL_SIZE
    argumen_engine["max_overflow"] = pengaturan.DATABASE_MAX_OVERFLOW
    argumen_engine["pool_recycle"] = pengaturan.DATABASE_POOL_RECYCLE
    # asyncpg: zona waktu UTC di sisi server
    argumen_engine["connect_args"] = {
        "timeout": 10,
        "server_settings": {"timezone": "UTC"},
    }

engine = create_async_engine(url_database_asinkron, **argumen_engine)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as sesi_database:
        yield sesi_database


@asynccontextmanager
async def konteks_sesi_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager sesi untuk pemakaian di luar dependensi FastAPI.

    Contoh: `async with konteks_sesi_database() as sesi: ...`
    """
    async with SessionLocal() as sesi_database:
        try:
            yield sesi_database
        except Exception as galat:  # noqa: BLE001 — log lalu teruskan
            logger.error("Galat sesi basis data: %s", galat, exc_info=True)
            await sesi_database.rollback()
            raise


async def cek_kesehatan_koneksi_database() -> bool:
    """Mengembalikan True jika koneksi ke basis data sehat."""
    try:
        async with engine.connect() as koneksi:
            await koneksi.execute(text("SELECT 1"))
        return True
    except Exception as galat:  # noqa: BLE001
        logger.error("Pemeriksaan koneksi basis data gagal: %s", galat)
        return False


def ambil_statistik_pool_database() -> dict[str, int]:
    """Ringkasan pool koneksi (beberapa field hilang pada backend SQLite)."""
    info: dict[str, int] = {
        "ukuran_konfigurasi": int(pengaturan.DATABASE_POOL_SIZE),
        "overflow_maks": int(pengaturan.DATABASE_MAX_OVERFLOW),
    }
    kolam = engine.pool
    fn_checkout = getattr(kolam, "checkedout", None)
    fn_checkin = getattr(kolam, "checkedin", None)
    if callable(fn_checkout) and callable(fn_checkin):
        try:
            info["tercheckout"] = int(fn_checkout())
            info["tercheckin"] = int(fn_checkin())
        except (TypeError, ValueError):
            pass
    return info
