from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Transaction, TransactionStatus, utcnow
from app.services.settlement import SettlementService
from app.utils.exceptions import InvalidStateTransition

logger = logging.getLogger("agentpay.state_machine")


class TransactionStateMachine:
    """
    Mengelola transisi status transaksi dengan validasi ketat.

    Memastikan alur konsisten dan mencegah perubahan status yang tidak sah.
    """

    VALID_TRANSITIONS: dict[TransactionStatus, list[TransactionStatus]] = {
        TransactionStatus.INITIATED: [
            TransactionStatus.PENDING,
            TransactionStatus.ROLLED_BACK,
            TransactionStatus.FAILED,
        ],
        TransactionStatus.PENDING: [
            TransactionStatus.CONFIRMED,
            TransactionStatus.ROLLED_BACK,
            TransactionStatus.FAILED,
        ],
        TransactionStatus.CONFIRMED: [
            TransactionStatus.SETTLED,
            TransactionStatus.FAILED,
            TransactionStatus.ROLLED_BACK,
        ],
        TransactionStatus.SETTLED: [],
        TransactionStatus.FAILED: [],
        TransactionStatus.ROLLED_BACK: [],
        TransactionStatus.EXPIRED: [],
    }

    @classmethod
    def can_transition(
        cls, dari_status: TransactionStatus, ke_status: TransactionStatus
    ) -> bool:
        """Mengecek apakah transisi diizinkan oleh matriks transisi."""
        daftar_diizinkan = cls.VALID_TRANSITIONS.get(dari_status, [])
        return ke_status in daftar_diizinkan

    @classmethod
    def is_terminal(cls, status: TransactionStatus) -> bool:
        """True jika status terminal (tidak ada transisi keluar)."""
        return len(cls.VALID_TRANSITIONS.get(status, [])) == 0

    @classmethod
    async def transition(
        cls,
        sesi: AsyncSession,
        transaksi: Transaction,
        ke_status: TransactionStatus,
        *,
        alasan_gagal: Optional[str] = None,
        alasan_rollback: Optional[str] = None,
    ) -> Transaction:
        """
        Menjalankan transisi status beserta efek samping saldo yang diperlukan.

        Raises:
            InvalidStateTransition: Jika transisi tidak diizinkan.
        """
        status_lama = transaksi.status
        if not cls.can_transition(status_lama, ke_status):
            raise InvalidStateTransition(status_lama.value, ke_status.value)

        if ke_status == TransactionStatus.ROLLED_BACK:
            alasan_final = alasan_rollback or "ROLLED_BACK"
            transaksi_terbaru = await SettlementService.rollback_transaction(
                transaksi.id, alasan_final, sesi
            )
        elif ke_status == TransactionStatus.FAILED:
            alasan_final = alasan_gagal or "FAILED"
            transaksi_terbaru = await SettlementService.fail_transaction(
                transaksi.id, alasan_final, sesi
            )
        elif status_lama == TransactionStatus.INITIATED and ke_status == TransactionStatus.PENDING:
            transaksi.status = TransactionStatus.PENDING
            await sesi.flush()
            transaksi_terbaru = transaksi
        elif status_lama == TransactionStatus.PENDING and ke_status == TransactionStatus.CONFIRMED:
            transaksi.confirmed_at = utcnow()
            transaksi.status = TransactionStatus.CONFIRMED
            await sesi.flush()
            transaksi_terbaru = transaksi
        elif status_lama == TransactionStatus.CONFIRMED and ke_status == TransactionStatus.SETTLED:
            transaksi_terbaru = await SettlementService.settle_transaction(transaksi.id, sesi)
        else:
            raise InvalidStateTransition(status_lama.value, ke_status.value)

        await cls._catat_log_transisi(sesi, transaksi_terbaru, status_lama, ke_status)
        return transaksi_terbaru

    @classmethod
    async def _catat_log_transisi(
        cls,
        sesi: AsyncSession,
        transaksi: Transaction,
        status_lama: TransactionStatus,
        status_baru: TransactionStatus,
    ) -> None:
        """Mencatat transisi status dengan konteks agent untuk observabilitas."""
        kueri_id = select(Agent.agent_id).where(Agent.id == transaksi.from_agent_id)
        hasil_pengirim = await sesi.execute(kueri_id)
        id_pengirim = hasil_pengirim.scalar_one()

        kueri_id_penerima = select(Agent.agent_id).where(Agent.id == transaksi.to_agent_id)
        hasil_penerima = await sesi.execute(kueri_id_penerima)
        id_penerima = hasil_penerima.scalar_one()

        logger.info(
            "State transition",
            extra={
                "transaction_id": str(transaksi.id),
                "from_status": status_lama.value,
                "to_status": status_baru.value,
                "agent_from": id_pengirim,
                "agent_to": id_penerima,
                "amount": str(transaksi.amount),
            },
        )
