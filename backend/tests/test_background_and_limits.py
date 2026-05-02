from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

import app.background_tasks as mod_latar
from app.background_tasks import expire_transactions_task
from app.config import get_settings
from app.database import SessionLocal
from app.crypto import Ed25519Crypto
from app.models import Agent, Transaction, TransactionStatus, utcnow
from app.routes.transactions import pembatas_laju
from app.utils.exceptions import RateLimitExceededException


@pytest.mark.asyncio
async def test_pembatas_laju_melewati_seratus_per_jam():
    id_agent = f"rl_{uuid4().hex[:10]}"
    for _ in range(100):
        await pembatas_laju.catat_dan_cek(id_agent)
    with pytest.raises(RateLimitExceededException):
        await pembatas_laju.catat_dan_cek(id_agent)


@pytest.mark.asyncio
async def test_expire_transactions_task_menjalankan_rollback(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_TASKS", "true")
    get_settings.cache_clear()
    async with SessionLocal() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"bg_{uuid4().hex[:8]}", balance=Decimal("50"), public_key=pub_p)
            q = Agent(agent_id=f"bh_{uuid4().hex[:8]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("2")
            p.balance -= jumlah
            t = Transaction(
                from_agent_id=p.id,
                to_agent_id=q.id,
                amount=jumlah,
                status=TransactionStatus.INITIATED,
                timeout_at=utcnow() - timedelta(minutes=2),
                nonce=str(uuid4()),
            )
            sesi.add(t)
            await sesi.flush()
            id_pengirim = p.id

    await expire_transactions_task()

    async with SessionLocal() as sesi:
        pengirim = (await sesi.execute(select(Agent).where(Agent.id == id_pengirim))).scalar_one()
        assert pengirim.balance == Decimal("50")

    get_settings.cache_clear()


def test_start_dan_shutdown_background_tasks_dengan_scheduler_palsu(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_TASKS", "true")
    get_settings.cache_clear()
    penjadwal_palsu = MagicMock()
    penjadwal_palsu.running = False
    with patch.object(mod_latar, "scheduler", penjadwal_palsu):
        mod_latar.start_background_tasks()
    penjadwal_palsu.add_job.assert_called_once()
    penjadwal_palsu.start.assert_called_once()

    penjadwal_palsu.running = True
    with patch.object(mod_latar, "scheduler", penjadwal_palsu):
        mod_latar.shutdown_background_tasks()
    penjadwal_palsu.shutdown.assert_called_once_with(wait=False)
    get_settings.cache_clear()
