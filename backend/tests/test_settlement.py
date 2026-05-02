from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.crypto import Ed25519Crypto
from app.models import Agent, Transaction, TransactionStatus, utcnow
from app.services.settlement import SettlementService
from app.state_machine import TransactionStateMachine
from app.utils.exceptions import InvalidStateTransition


async def _buat_agents_dan_txn_confirmed(sesi, jumlah: Decimal = Decimal("12")) -> Transaction:
    _, pub_p = Ed25519Crypto.generate_keypair()
    _, pub_q = Ed25519Crypto.generate_keypair()
    p = Agent(agent_id=f"sp_{uuid4().hex[:6]}", balance=Decimal("200"), public_key=pub_p)
    q = Agent(agent_id=f"sr_{uuid4().hex[:6]}", balance=Decimal("1"), public_key=pub_q)
    sesi.add_all([p, q])
    await sesi.flush()
    p.balance -= jumlah
    t = Transaction(
        from_agent_id=p.id,
        to_agent_id=q.id,
        amount=jumlah,
        status=TransactionStatus.CONFIRMED,
        confirmed_at=utcnow(),
        nonce=str(uuid4()),
    )
    sesi.add(t)
    await sesi.flush()
    return t


@pytest.mark.asyncio
async def test_settle_confirmed_transaction(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _buat_agents_dan_txn_confirmed(sesi)
            penerima = (await sesi.execute(select(Agent).where(Agent.id == txn.to_agent_id))).scalar_one()
            saldo_awal = penerima.balance
            await SettlementService.settle_transaction(txn.id, sesi)
        await sesi.refresh(penerima)
        assert penerima.balance == saldo_awal + txn.amount
        assert txn.status == TransactionStatus.SETTLED


@pytest.mark.asyncio
async def test_rollback_pending_transaction(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"rp_{uuid4().hex[:6]}", balance=Decimal("50"), public_key=pub_p)
            q = Agent(agent_id=f"rq_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("7")
            p.balance -= jumlah
            t = Transaction(
                from_agent_id=p.id,
                to_agent_id=q.id,
                amount=jumlah,
                status=TransactionStatus.PENDING,
                nonce=str(uuid4()),
            )
            sesi.add(t)
            await sesi.flush()
            saldo_p = p.balance
            await SettlementService.rollback_transaction(t.id, "UJI_ROLLBACK", sesi)
        await sesi.refresh(p)
        assert p.balance == saldo_p + jumlah
        assert t.status == TransactionStatus.ROLLED_BACK


@pytest.mark.asyncio
async def test_expire_old_transactions(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"ex_{uuid4().hex[:6]}", balance=Decimal("80"), public_key=pub_p)
            q = Agent(agent_id=f"ey_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("4")
            p.balance -= jumlah
            t = Transaction(
                from_agent_id=p.id,
                to_agent_id=q.id,
                amount=jumlah,
                status=TransactionStatus.INITIATED,
                timeout_at=utcnow() - timedelta(minutes=1),
                nonce=str(uuid4()),
            )
            sesi.add(t)
            await sesi.flush()
            id_txn = t.id
            saldo_sebelum = p.balance

        async with sesi.begin():
            jumlah_exp = await SettlementService.expire_old_transactions(sesi)

        await sesi.refresh(p)
        t2 = (await sesi.execute(select(Transaction).where(Transaction.id == id_txn))).scalar_one()
        assert jumlah_exp == 1
        assert t2.status == TransactionStatus.ROLLED_BACK
        assert p.balance == saldo_sebelum + jumlah


@pytest.mark.asyncio
async def test_cannot_settle_wrong_status(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"ws_{uuid4().hex[:6]}", balance=Decimal("30"), public_key=pub_p)
            q = Agent(agent_id=f"wt_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("3")
            p.balance -= jumlah
            t = Transaction(
                from_agent_id=p.id,
                to_agent_id=q.id,
                amount=jumlah,
                status=TransactionStatus.PENDING,
                nonce=str(uuid4()),
            )
            sesi.add(t)
            await sesi.flush()
            with pytest.raises(InvalidStateTransition):
                await SettlementService.settle_transaction(t.id, sesi)


@pytest.mark.asyncio
async def test_rollback_returns_correct_amount(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"ra_{uuid4().hex[:6]}", balance=Decimal("100"), public_key=pub_p)
            q = Agent(agent_id=f"rb_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("11.12345678")
            p.balance -= jumlah
            t = Transaction(
                from_agent_id=p.id,
                to_agent_id=q.id,
                amount=jumlah,
                status=TransactionStatus.INITIATED,
                nonce=str(uuid4()),
            )
            sesi.add(t)
            await sesi.flush()
            saldo = p.balance
            await SettlementService.rollback_transaction(t.id, "UJI", sesi)
        await sesi.refresh(p)
        assert p.balance == saldo + jumlah


@pytest.mark.asyncio
async def test_double_settlement_prevented(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _buat_agents_dan_txn_confirmed(sesi)
            await SettlementService.settle_transaction(txn.id, sesi)
            with pytest.raises(InvalidStateTransition):
                await SettlementService.settle_transaction(txn.id, sesi)


@pytest.mark.asyncio
async def test_fail_transaction_mengembalikan_saldo(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"fa_{uuid4().hex[:6]}", balance=Decimal("40"), public_key=pub_p)
            q = Agent(agent_id=f"fb_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("2")
            p.balance -= jumlah
            t = Transaction(
                from_agent_id=p.id,
                to_agent_id=q.id,
                amount=jumlah,
                status=TransactionStatus.INITIATED,
                nonce=str(uuid4()),
            )
            sesi.add(t)
            await sesi.flush()
            saldo = p.balance
            await SettlementService.fail_transaction(t.id, "SYS", sesi)
        await sesi.refresh(p)
        assert p.balance == saldo + jumlah
        assert t.status == TransactionStatus.FAILED
