from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Transaction, TransactionStatus, utcnow
from app.utils.exceptions import InvalidStateTransition

logger = logging.getLogger("agentpay.settlement")


class SettlementService:
    """Menangani settlement otomatis, rollback, dan expiry batch."""

    @staticmethod
    async def settle_transaction(id_transaksi: UUID, sesi: AsyncSession) -> Transaction:
        """
        Menyelesaikan transaksi berstatus CONFIRMED.

        Langkah:
        1. Kunci baris transaksi (SELECT FOR UPDATE)
        2. Pastikan status CONFIRMED
        3. Kunci baris penerima
        4. Tambahkan amount ke saldo penerima
        5. Ubah status SETTLED dan settled_at
        """
        kueri_transaksi = (
            select(Transaction).where(Transaction.id == id_transaksi).with_for_update()
        )
        hasil_transaksi = await sesi.execute(kueri_transaksi)
        transaksi = hasil_transaksi.scalar_one_or_none()
        if transaksi is None:
            raise ValueError(f"Transaksi '{id_transaksi}' tidak ditemukan")

        if transaksi.status != TransactionStatus.CONFIRMED:
            raise InvalidStateTransition(transaksi.status.value, TransactionStatus.SETTLED.value)

        kueri_penerima = select(Agent).where(Agent.id == transaksi.to_agent_id).with_for_update()
        hasil_penerima = await sesi.execute(kueri_penerima)
        agent_penerima = hasil_penerima.scalar_one_or_none()
        if agent_penerima is None:
            raise ValueError("Agent penerima tidak ditemukan")

        agent_penerima.balance += transaksi.amount
        transaksi.status = TransactionStatus.SETTLED
        transaksi.settled_at = utcnow()
        await sesi.flush()
        return transaksi

    @staticmethod
    async def rollback_transaction(id_transaksi: UUID, alasan: str, sesi: AsyncSession) -> Transaction:
        """
        Mengembalikan dana ke pengirim dan menandai ROLLED_BACK.

        Diizinkan dari status INITIATED, PENDING, atau CONFIRMED (belum terminal).
        """
        kueri_transaksi = (
            select(Transaction).where(Transaction.id == id_transaksi).with_for_update()
        )
        hasil_transaksi = await sesi.execute(kueri_transaksi)
        transaksi = hasil_transaksi.scalar_one_or_none()
        if transaksi is None:
            raise ValueError(f"Transaksi '{id_transaksi}' tidak ditemukan")

        if transaksi.is_terminal():
            raise InvalidStateTransition(transaksi.status.value, TransactionStatus.ROLLED_BACK.value)

        if transaksi.status not in (
            TransactionStatus.INITIATED,
            TransactionStatus.PENDING,
            TransactionStatus.CONFIRMED,
        ):
            raise InvalidStateTransition(transaksi.status.value, TransactionStatus.ROLLED_BACK.value)

        kueri_pengirim = select(Agent).where(Agent.id == transaksi.from_agent_id).with_for_update()
        hasil_pengirim = await sesi.execute(kueri_pengirim)
        agent_pengirim = hasil_pengirim.scalar_one_or_none()
        if agent_pengirim is None:
            raise ValueError("Agent pengirim tidak ditemukan")

        agent_pengirim.balance += transaksi.amount
        transaksi.status = TransactionStatus.ROLLED_BACK
        transaksi.rolled_back_reason = alasan
        await sesi.flush()
        return transaksi

    @staticmethod
    async def fail_transaction(id_transaksi: UUID, alasan: str, sesi: AsyncSession) -> Transaction:
        """Mengembalikan dana ke pengirim dan menandai FAILED beserta alasan kegagalan."""
        kueri_transaksi = (
            select(Transaction).where(Transaction.id == id_transaksi).with_for_update()
        )
        hasil_transaksi = await sesi.execute(kueri_transaksi)
        transaksi = hasil_transaksi.scalar_one_or_none()
        if transaksi is None:
            raise ValueError(f"Transaksi '{id_transaksi}' tidak ditemukan")

        if transaksi.is_terminal():
            raise InvalidStateTransition(transaksi.status.value, TransactionStatus.FAILED.value)

        if transaksi.status not in (
            TransactionStatus.INITIATED,
            TransactionStatus.PENDING,
            TransactionStatus.CONFIRMED,
        ):
            raise InvalidStateTransition(transaksi.status.value, TransactionStatus.FAILED.value)

        kueri_pengirim = select(Agent).where(Agent.id == transaksi.from_agent_id).with_for_update()
        hasil_pengirim = await sesi.execute(kueri_pengirim)
        agent_pengirim = hasil_pengirim.scalar_one_or_none()
        if agent_pengirim is None:
            raise ValueError("Agent pengirim tidak ditemukan")

        agent_pengirim.balance += transaksi.amount
        transaksi.status = TransactionStatus.FAILED
        transaksi.failure_reason = alasan
        await sesi.flush()
        return transaksi

    @staticmethod
    async def expire_old_transactions(sesi: AsyncSession) -> int:
        """
        Mencari transaksi INITIATED/PENDING yang timeout_at < sekarang.

        Untuk tiap transaksi memanggil rollback dengan alasan TIMEOUT.
        """
        sekarang = utcnow()
        kueri_kedaluwarsa = (
            select(Transaction.id)
            .where(
                Transaction.status.in_(
                    (TransactionStatus.INITIATED, TransactionStatus.PENDING),
                ),
                Transaction.timeout_at.is_not(None),
                Transaction.timeout_at < sekarang,
            )
            .order_by(Transaction.created_at.asc())
        )
        hasil_id = await sesi.execute(kueri_kedaluwarsa)
        daftar_id = [baris[0] for baris in hasil_id.all()]
        jumlah = 0
        for satu_id in daftar_id:
            await SettlementService.rollback_transaction(satu_id, "TIMEOUT", sesi)
            jumlah += 1
        if jumlah:
            logger.info("Kedaluwarsa transaksi selesai diproses", extra={"jumlah": jumlah})
        return jumlah
