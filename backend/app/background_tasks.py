"""
Penjadwal tugas latar belakang (misalnya expiry transaksi).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.services.settlement import SettlementService

logger = logging.getLogger("agentpay.background")

scheduler = AsyncIOScheduler()


async def expire_transactions_task() -> None:
    """Menjalankan expiry transaksi setiap interval (dijadwalkan)."""
    pengaturan = get_settings()
    if not pengaturan.ENABLE_BACKGROUND_TASKS:
        return
    try:
        async with SessionLocal() as db:
            async with db.begin():
                jumlah = await SettlementService.expire_old_transactions(db)
        if jumlah > 0:
            logger.info("Transaksi kedaluwarsa diproses", extra={"jumlah": jumlah})
    except Exception:
        logger.exception("Gagal menjalankan expire_transactions_task")


def start_background_tasks() -> None:
    """Memulai penjadwal APScheduler jika diaktifkan."""
    pengaturan = get_settings()
    if not pengaturan.ENABLE_BACKGROUND_TASKS:
        logger.info("Background tasks dinonaktifkan lewat konfigurasi")
        return
    scheduler.add_job(
        expire_transactions_task,
        IntervalTrigger(minutes=5),
        id="expire_transactions",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Background tasks started")


def shutdown_background_tasks() -> None:
    """Menghentikan penjadwal dengan aman."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
