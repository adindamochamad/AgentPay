from __future__ import annotations

import asyncio
import threading
from decimal import Decimal
from typing import List
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import Ed25519Crypto
from app.models import Agent, Transaction, TransactionStatus
from app.state_machine import TransactionStateMachine
from app.utils.exceptions import InvalidStateTransition


async def _siapkan_transaksi_initiated(sesi: AsyncSession) -> Transaction:
    _, pub_p = Ed25519Crypto.generate_keypair()
    _, pub_r = Ed25519Crypto.generate_keypair()
    pengirim = Agent(agent_id=f"p_{uuid4().hex[:8]}", balance=Decimal("500"), public_key=pub_p)
    penerima = Agent(agent_id=f"r_{uuid4().hex[:8]}", balance=Decimal("10"), public_key=pub_r)
    sesi.add_all([pengirim, penerima])
    await sesi.flush()
    jumlah = Decimal("25")
    pengirim.balance -= jumlah
    txn = Transaction(
        from_agent_id=pengirim.id,
        to_agent_id=penerima.id,
        amount=jumlah,
        status=TransactionStatus.INITIATED,
        nonce=str(uuid4()),
    )
    sesi.add(txn)
    await sesi.flush()
    return txn


@pytest.mark.asyncio
async def test_can_transition_semua_valid(pabrik_sesi_uji):
    pasangan = [
        (TransactionStatus.INITIATED, TransactionStatus.PENDING),
        (TransactionStatus.INITIATED, TransactionStatus.ROLLED_BACK),
        (TransactionStatus.INITIATED, TransactionStatus.FAILED),
        (TransactionStatus.PENDING, TransactionStatus.CONFIRMED),
        (TransactionStatus.PENDING, TransactionStatus.ROLLED_BACK),
        (TransactionStatus.PENDING, TransactionStatus.FAILED),
        (TransactionStatus.CONFIRMED, TransactionStatus.SETTLED),
        (TransactionStatus.CONFIRMED, TransactionStatus.FAILED),
        (TransactionStatus.CONFIRMED, TransactionStatus.ROLLED_BACK),
    ]
    for dari, ke in pasangan:
        assert TransactionStateMachine.can_transition(dari, ke)


@pytest.mark.asyncio
async def test_can_transition_invalid(pabrik_sesi_uji):
    assert not TransactionStateMachine.can_transition(TransactionStatus.SETTLED, TransactionStatus.PENDING)
    assert not TransactionStateMachine.can_transition(TransactionStatus.FAILED, TransactionStatus.INITIATED)
    assert not TransactionStateMachine.can_transition(TransactionStatus.ROLLED_BACK, TransactionStatus.CONFIRMED)
    assert not TransactionStateMachine.can_transition(TransactionStatus.PENDING, TransactionStatus.INITIATED)
    assert not TransactionStateMachine.can_transition(TransactionStatus.CONFIRMED, TransactionStatus.INITIATED)
    assert not TransactionStateMachine.can_transition(TransactionStatus.EXPIRED, TransactionStatus.INITIATED)


@pytest.mark.asyncio
async def test_terminal_state_immutability(pabrik_sesi_uji):
    for status_terminal in (
        TransactionStatus.SETTLED,
        TransactionStatus.FAILED,
        TransactionStatus.ROLLED_BACK,
        TransactionStatus.EXPIRED,
    ):
        assert TransactionStateMachine.is_terminal(status_terminal)
        assert not TransactionStateMachine.can_transition(status_terminal, TransactionStatus.PENDING)


@pytest.mark.asyncio
async def test_transition_initiated_ke_pending_tanpa_ubah_saldo(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            pengirim = (
                await sesi.execute(select(Agent).where(Agent.id == txn.from_agent_id))
            ).scalar_one()
            saldo_nilai = pengirim.balance
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.PENDING)
        await sesi.refresh(pengirim)
        assert pengirim.balance == saldo_nilai
        assert txn.status == TransactionStatus.PENDING


@pytest.mark.asyncio
async def test_transition_side_effect_settlement(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.PENDING)
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.CONFIRMED)
            penerima = (
                await sesi.execute(select(Agent).where(Agent.id == txn.to_agent_id))
            ).scalar_one()
            saldo_awal_penerima = penerima.balance
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.SETTLED)
        await sesi.refresh(penerima)
        assert penerima.balance == saldo_awal_penerima + txn.amount
        assert txn.status == TransactionStatus.SETTLED


@pytest.mark.asyncio
async def test_transition_rollback_mengembalikan_saldo(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            pengirim = (
                await sesi.execute(select(Agent).where(Agent.id == txn.from_agent_id))
            ).scalar_one()
            saldo_setelah_debit = pengirim.balance
            await TransactionStateMachine.transition(
                sesi, txn, TransactionStatus.ROLLED_BACK, alasan_rollback="UJI"
            )
        await sesi.refresh(pengirim)
        assert pengirim.balance == saldo_setelah_debit + txn.amount
        assert txn.status == TransactionStatus.ROLLED_BACK


@pytest.mark.asyncio
async def test_transition_fail_mengembalikan_saldo(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            pengirim = (
                await sesi.execute(select(Agent).where(Agent.id == txn.from_agent_id))
            ).scalar_one()
            saldo_setelah_debit = pengirim.balance
            await TransactionStateMachine.transition(
                sesi, txn, TransactionStatus.FAILED, alasan_gagal="ERROR_UJI"
            )
        await sesi.refresh(pengirim)
        assert pengirim.balance == saldo_setelah_debit + txn.amount
        assert txn.failure_reason == "ERROR_UJI"


@pytest.mark.asyncio
async def test_invalid_transition_raises(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.PENDING)
            with pytest.raises(InvalidStateTransition):
                await TransactionStateMachine.transition(sesi, txn, TransactionStatus.INITIATED)


@pytest.mark.asyncio
async def test_settle_ganda_kedua_gagal(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.PENDING)
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.CONFIRMED)
            await TransactionStateMachine.transition(sesi, txn, TransactionStatus.SETTLED)
        with pytest.raises(InvalidStateTransition):
            async with sesi.begin():
                kueri = select(Transaction).where(Transaction.id == txn.id).with_for_update()
                txn2 = (await sesi.execute(kueri)).scalar_one()
                await TransactionStateMachine.transition(sesi, txn2, TransactionStatus.SETTLED)


@pytest.mark.asyncio
async def test_concurrent_dua_settle_salah_satu_gagal_atau_sukses(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi_setup:
        async with sesi_setup.begin():
            txn = await _siapkan_transaksi_initiated(sesi_setup)
            await TransactionStateMachine.transition(sesi_setup, txn, TransactionStatus.PENDING)
            await TransactionStateMachine.transition(sesi_setup, txn, TransactionStatus.CONFIRMED)
            id_transaksi = txn.id

    async def coba_settle() -> str:
        async with pabrik_sesi_uji() as sesi:
            try:
                async with sesi.begin():
                    kueri = select(Transaction).where(Transaction.id == id_transaksi).with_for_update()
                    baris = (await sesi.execute(kueri)).scalar_one()
                    await TransactionStateMachine.transition(sesi, baris, TransactionStatus.SETTLED)
                return "ok"
            except InvalidStateTransition:
                return "gagal"

    hasil = await asyncio.gather(coba_settle(), coba_settle())
    assert hasil.count("ok") >= 1
    assert all(x in ("ok", "gagal") for x in hasil)


@pytest.mark.asyncio
async def test_threading_satu_accept_thread_kedua_melihat_pending(pabrik_sesi_uji):
    """Satu thread melakukan accept; memastikan tidak error saat dua sesi berbeda."""
    id_transaksi: list = []
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            txn = await _siapkan_transaksi_initiated(sesi)
            id_transaksi.append(txn.id)

    kunci = threading.Lock()
    daftar_status: List[str] = []

    def jalankan() -> None:
        async def dalam() -> None:
            async with pabrik_sesi_uji() as sesi:
                async with sesi.begin():
                    kueri = select(Transaction).where(Transaction.id == id_transaksi[0]).with_for_update()
                    baris = (await sesi.execute(kueri)).scalar_one()
                    if baris.status == TransactionStatus.INITIATED:
                        await TransactionStateMachine.transition(sesi, baris, TransactionStatus.PENDING)
                        with kunci:
                            daftar_status.append("pending")

        asyncio.run(dalam())

    t1 = threading.Thread(target=jalankan)
    t2 = threading.Thread(target=jalankan)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert "pending" in daftar_status
