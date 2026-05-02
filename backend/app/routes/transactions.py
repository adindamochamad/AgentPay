from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.middleware.signature_verification import (
    dependensi_pembuatan_transaksi,
    dependensi_sengketa_transaksi,
    verifikasi_batal_transaksi,
    verifikasi_konfirmasi_transaksi,
    verifikasi_terima_transaksi,
)
from app.models import Agent, Transaction, TransactionStatus, utcnow
from app.schemas import (
    TransactionActionSigned,
    TransactionCreateSigned,
    TransactionDisputeSigned,
    TransactionListItem,
    TransactionListResponse,
    TransactionResponse,
)
from app.state_machine import TransactionStateMachine
from app.utils.exceptions import (
    AgentNotFoundException,
    InsufficientBalanceException,
    InvalidAmountException,
    InvalidStateTransition,
    InvalidTransactionStateException,
    RateLimitExceededException,
    SelfPaymentNotAllowedException,
    TransactionExpiredException,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


class PembatasLajuTransaksi:
    """Pembatasan sederhana in-memory per agent (sliding window 1 jam)."""

    def __init__(self, batas: int, jendela_detik: int) -> None:
        self._batas = batas
        self._jendela_detik = jendela_detik
        self._kunci = asyncio.Lock()
        self._stempel: dict[str, list[float]] = defaultdict(list)

    async def catat_dan_cek(self, agent_id: str) -> None:
        """Mencatat satu percobaan transaksi dan menolak jika melewati batas."""
        async with self._kunci:
            sekarang = time.monotonic()
            daftar = self._stempel[agent_id]
            daftar[:] = [t for t in daftar if sekarang - t < self._jendela_detik]
            if len(daftar) >= self._batas:
                raise RateLimitExceededException(agent_id, self._batas)
            daftar.append(sekarang)


def _bangun_pembatas_laju() -> PembatasLajuTransaksi:
    pengaturan = get_settings()
    return PembatasLajuTransaksi(pengaturan.MAX_TRANSACTIONS_PER_HOUR, 3600)


pembatas_laju = _bangun_pembatas_laju()


def _validasi_jumlah(muatan: TransactionCreateSigned) -> None:
    pengaturan = get_settings()
    if muatan.amount < pengaturan.MIN_TRANSACTION_AMOUNT:
        raise InvalidAmountException(
            f"Jumlah minimum adalah {pengaturan.MIN_TRANSACTION_AMOUNT} (setara satoshi minimal)"
        )
    if muatan.amount > pengaturan.MAX_TRANSACTION_AMOUNT:
        raise InvalidAmountException(
            f"Jumlah maksimum adalah {pengaturan.MAX_TRANSACTION_AMOUNT} untuk mencegah kesalahan input"
        )


async def _tulis_log_sengketa(jalur_berkas: str, baris: str) -> None:
    """Menulis baris log sengketa secara non-blocking (thread pool)."""

    def _tulis() -> None:
        path_obj = Path(jalur_berkas)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with path_obj.open("a", encoding="utf-8") as berkas:
            berkas.write(baris + "\n")

    await asyncio.to_thread(_tulis)


def _bangun_respons_transaksi(
    transaksi: Transaction, agent_pengirim: Agent, agent_penerima: Agent
) -> TransactionResponse:
    return TransactionResponse(
        id=transaksi.id,
        from_agent=agent_pengirim.agent_id,
        to_agent=agent_penerima.agent_id,
        amount=transaksi.amount,
        status=transaksi.status.value,
        created_at=transaksi.created_at,
        timeout_at=transaksi.timeout_at,
        confirmed_at=transaksi.confirmed_at,
        settled_at=transaksi.settled_at,
        failure_reason=transaksi.failure_reason,
        rolled_back_reason=transaksi.rolled_back_reason,
    )


async def _ambil_agent_pasangan(
    sesi_database: AsyncSession, transaksi: Transaction
) -> tuple[Agent, Agent]:
    kueri_agent = select(Agent).where(Agent.id.in_([transaksi.from_agent_id, transaksi.to_agent_id]))
    hasil_agent = await sesi_database.execute(kueri_agent)
    daftar_agent = hasil_agent.scalars().all()
    peta_agent = {agent.id: agent for agent in daftar_agent}

    agent_pengirim = peta_agent.get(transaksi.from_agent_id)
    agent_penerima = peta_agent.get(transaksi.to_agent_id)
    if agent_pengirim is None:
        raise AgentNotFoundException(str(transaksi.from_agent_id))
    if agent_penerima is None:
        raise AgentNotFoundException(str(transaksi.to_agent_id))
    return agent_pengirim, agent_penerima


async def layanan_inisiasi_pembayaran(
    sesi_database: AsyncSession,
    muatan: TransactionCreateSigned,
    kunci_idempotensi: Optional[str],
) -> TransactionResponse:
    _validasi_jumlah(muatan)
    if muatan.from_agent == muatan.to_agent:
        raise SelfPaymentNotAllowedException(muatan.from_agent)

    await pembatas_laju.catat_dan_cek(muatan.from_agent)

    transaksi_baru: Transaction | None = None
    agent_pengirim: Agent | None = None
    agent_penerima: Agent | None = None

    async with sesi_database.begin():
        if kunci_idempotensi:
            kueri_pengirim = select(Agent).where(Agent.agent_id == muatan.from_agent)
            hasil_pengirim = await sesi_database.execute(kueri_pengirim)
            agent_pengirim_idempotensi = hasil_pengirim.scalar_one_or_none()
            if agent_pengirim_idempotensi is None:
                raise AgentNotFoundException(muatan.from_agent)
            kueri_existing = (
                select(Transaction)
                .where(
                    Transaction.from_agent_id == agent_pengirim_idempotensi.id,
                    Transaction.idempotency_key == kunci_idempotensi,
                )
                .options(selectinload(Transaction.from_agent), selectinload(Transaction.to_agent))
            )
            hasil_existing = await sesi_database.execute(kueri_existing)
            transaksi_existing = hasil_existing.scalar_one_or_none()
            if transaksi_existing is not None:
                if transaksi_existing.from_agent is None or transaksi_existing.to_agent is None:
                    agent_a, agent_b = await _ambil_agent_pasangan(sesi_database, transaksi_existing)
                else:
                    agent_a, agent_b = transaksi_existing.from_agent, transaksi_existing.to_agent
                return _bangun_respons_transaksi(transaksi_existing, agent_a, agent_b)

        async with sesi_database.begin_nested():
            kueri_pengirim = (
                select(Agent).where(Agent.agent_id == muatan.from_agent).with_for_update()
            )
            hasil_pengirim = await sesi_database.execute(kueri_pengirim)
            agent_pengirim = hasil_pengirim.scalar_one_or_none()
            if agent_pengirim is None:
                raise AgentNotFoundException(muatan.from_agent)

            kueri_penerima = select(Agent).where(Agent.agent_id == muatan.to_agent)
            hasil_penerima = await sesi_database.execute(kueri_penerima)
            agent_penerima = hasil_penerima.scalar_one_or_none()
            if agent_penerima is None:
                raise AgentNotFoundException(muatan.to_agent)

            if agent_pengirim.balance < muatan.amount:
                raise InsufficientBalanceException(muatan.from_agent)

            agent_pengirim.balance -= muatan.amount
            pengaturan_batas = get_settings()
            batas_waktu = utcnow() + timedelta(
                hours=float(pengaturan_batas.TRANSACTION_TIMEOUT_HOURS)
            )
            transaksi_baru = Transaction(
                from_agent_id=agent_pengirim.id,
                to_agent_id=agent_penerima.id,
                amount=muatan.amount,
                status=TransactionStatus.INITIATED,
                timeout_at=batas_waktu,
                idempotency_key=kunci_idempotensi,
                nonce=muatan.nonce,
                signature=muatan.signature,
            )
            sesi_database.add(transaksi_baru)
            try:
                await sesi_database.flush()
            except IntegrityError as galat:
                teks_galat = str(galat).lower()
                if "nonce" in teks_galat or "unique" in teks_galat:
                    raise HTTPException(
                        status_code=400,
                        detail="Nonce sudah pernah digunakan (replay)",
                    ) from galat
                raise

    assert transaksi_baru is not None and agent_pengirim is not None and agent_penerima is not None
    await sesi_database.refresh(transaksi_baru)
    return _bangun_respons_transaksi(transaksi_baru, agent_pengirim, agent_penerima)


async def layanan_terima_transaksi(sesi_database: AsyncSession, txn_id: UUID) -> TransactionResponse:
    async with sesi_database.begin():
        kueri_transaksi = (
            select(Transaction).where(Transaction.id == txn_id).with_for_update()
        )
        hasil_transaksi = await sesi_database.execute(kueri_transaksi)
        transaksi_aktif = hasil_transaksi.scalar_one_or_none()
        if transaksi_aktif is None:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

        if transaksi_aktif.is_expired() and transaksi_aktif.status in (
            TransactionStatus.INITIATED,
            TransactionStatus.PENDING,
        ):
            raise TransactionExpiredException(str(txn_id))

        if transaksi_aktif.status != TransactionStatus.INITIATED:
            raise InvalidTransactionStateException(
                transaksi_aktif.status.value, TransactionStatus.INITIATED.value
            )

        await TransactionStateMachine.transition(
            sesi_database,
            transaksi_aktif,
            TransactionStatus.PENDING,
        )

    agent_pengirim, agent_penerima = await _ambil_agent_pasangan(sesi_database, transaksi_aktif)
    return _bangun_respons_transaksi(transaksi_aktif, agent_pengirim, agent_penerima)


async def layanan_konfirmasi_transaksi(sesi_database: AsyncSession, txn_id: UUID) -> TransactionResponse:
    async with sesi_database.begin():
        async with sesi_database.begin_nested():
            kueri_transaksi = (
                select(Transaction).where(Transaction.id == txn_id).with_for_update()
            )
            hasil_transaksi = await sesi_database.execute(kueri_transaksi)
            transaksi_aktif = hasil_transaksi.scalar_one_or_none()
            if transaksi_aktif is None:
                raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

            if transaksi_aktif.is_expired():
                raise TransactionExpiredException(str(txn_id))

            if transaksi_aktif.status != TransactionStatus.PENDING:
                raise InvalidTransactionStateException(
                    transaksi_aktif.status.value, TransactionStatus.PENDING.value
                )

            await TransactionStateMachine.transition(
                sesi_database,
                transaksi_aktif,
                TransactionStatus.CONFIRMED,
            )

        async with sesi_database.begin_nested():
            await TransactionStateMachine.transition(
                sesi_database,
                transaksi_aktif,
                TransactionStatus.SETTLED,
            )

    agent_pengirim, agent_penerima = await _ambil_agent_pasangan(sesi_database, transaksi_aktif)
    return _bangun_respons_transaksi(transaksi_aktif, agent_pengirim, agent_penerima)


async def layanan_batal_transaksi(
    sesi_database: AsyncSession, txn_id: UUID, alasan: str
) -> TransactionResponse:
    async with sesi_database.begin():
        kueri_transaksi = (
            select(Transaction).where(Transaction.id == txn_id).with_for_update()
        )
        hasil_transaksi = await sesi_database.execute(kueri_transaksi)
        transaksi_aktif = hasil_transaksi.scalar_one_or_none()
        if transaksi_aktif is None:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

        if transaksi_aktif.status not in (
            TransactionStatus.INITIATED,
            TransactionStatus.PENDING,
        ):
            raise InvalidStateTransition(
                transaksi_aktif.status.value, TransactionStatus.ROLLED_BACK.value
            )

        await TransactionStateMachine.transition(
            sesi_database,
            transaksi_aktif,
            TransactionStatus.ROLLED_BACK,
            alasan_rollback=alasan,
        )

    agent_pengirim, agent_penerima = await _ambil_agent_pasangan(sesi_database, transaksi_aktif)
    return _bangun_respons_transaksi(transaksi_aktif, agent_pengirim, agent_penerima)


async def layanan_sengketa_transaksi(
    sesi_database: AsyncSession, txn_id: UUID, muatan: TransactionDisputeSigned
) -> TransactionResponse:
    pengaturan = get_settings()
    waktu_sekarang = utcnow().isoformat()
    baris_log = (
        f"{waktu_sekarang}\ttxn={txn_id}\tjustification={muatan.justification.replace(chr(9), ' ')}"
    )
    await _tulis_log_sengketa(pengaturan.DISPUTE_LOG_PATH, baris_log)

    async with sesi_database.begin():
        kueri_transaksi = (
            select(Transaction).where(Transaction.id == txn_id).with_for_update()
        )
        hasil_transaksi = await sesi_database.execute(kueri_transaksi)
        transaksi_aktif = hasil_transaksi.scalar_one_or_none()
        if transaksi_aktif is None:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

        if transaksi_aktif.status not in (
            TransactionStatus.PENDING,
            TransactionStatus.CONFIRMED,
        ):
            raise InvalidStateTransition(
                transaksi_aktif.status.value, TransactionStatus.ROLLED_BACK.value
            )

        await TransactionStateMachine.transition(
            sesi_database,
            transaksi_aktif,
            TransactionStatus.ROLLED_BACK,
            alasan_rollback=f"DISPUTE:{muatan.justification[:200]}",
        )

    agent_pengirim, agent_penerima = await _ambil_agent_pasangan(sesi_database, transaksi_aktif)
    return _bangun_respons_transaksi(transaksi_aktif, agent_pengirim, agent_penerima)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    muatan: TransactionCreateSigned = Depends(dependensi_pembuatan_transaksi),
    sesi_database: AsyncSession = Depends(get_db),
    kunci_idempotensi: Annotated[Optional[str], Header(alias="Idempotency-Key")] = None,
) -> TransactionResponse:
    return await layanan_inisiasi_pembayaran(sesi_database, muatan, kunci_idempotensi)


@router.post("/{txn_id}/accept", response_model=TransactionResponse)
async def accept_transaction(
    txn_id: UUID,
    _muatan_tanda: TransactionActionSigned = Depends(verifikasi_terima_transaksi),
    sesi_database: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    return await layanan_terima_transaksi(sesi_database, txn_id)


@router.post("/{txn_id}/confirm", response_model=TransactionResponse)
async def confirm_transaction(
    txn_id: UUID,
    _muatan_tanda: TransactionActionSigned = Depends(verifikasi_konfirmasi_transaksi),
    sesi_database: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    return await layanan_konfirmasi_transaksi(sesi_database, txn_id)


@router.post("/{txn_id}/cancel", response_model=TransactionResponse)
async def cancel_transaction(
    txn_id: UUID,
    muatan_tanda: TransactionActionSigned = Depends(verifikasi_batal_transaksi),
    sesi_database: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    alasan = (muatan_tanda.reason if muatan_tanda.reason else None) or "CANCELLED_BY_USER"
    return await layanan_batal_transaksi(sesi_database, txn_id, alasan)


@router.post("/{txn_id}/dispute", response_model=TransactionResponse)
async def dispute_transaction(
    txn_id: UUID,
    muatan: TransactionDisputeSigned = Depends(dependensi_sengketa_transaksi),
    sesi_database: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    return await layanan_sengketa_transaksi(sesi_database, txn_id, muatan)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    sesi_database: AsyncSession = Depends(get_db),
    agent_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TransactionListResponse:
    kueri_dasar = select(Transaction)
    jumlah_kueri = select(func.count()).select_from(Transaction)

    if agent_id is not None:
        kueri_agent = select(Agent).where(Agent.agent_id == agent_id)
        hasil_agent = await sesi_database.execute(kueri_agent)
        agent_target = hasil_agent.scalar_one_or_none()
        if agent_target is None:
            raise AgentNotFoundException(agent_id)
        filter_agent = or_(
            Transaction.from_agent_id == agent_target.id,
            Transaction.to_agent_id == agent_target.id,
        )
        kueri_dasar = kueri_dasar.where(filter_agent)
        jumlah_kueri = jumlah_kueri.where(filter_agent)

    if status_filter is not None:
        try:
            enum_status = TransactionStatus(status_filter)
        except ValueError as galat:
            raise HTTPException(status_code=422, detail="Parameter status tidak valid") from galat
        kueri_dasar = kueri_dasar.where(Transaction.status == enum_status)
        jumlah_kueri = jumlah_kueri.where(Transaction.status == enum_status)

    hasil_total = await sesi_database.execute(jumlah_kueri)
    total = int(hasil_total.scalar_one())

    kueri_dasar = (
        kueri_dasar.options(selectinload(Transaction.from_agent), selectinload(Transaction.to_agent))
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    hasil_daftar = await sesi_database.execute(kueri_dasar)
    daftar_transaksi = hasil_daftar.scalars().unique().all()

    items: list[TransactionListItem] = []
    for txn in daftar_transaksi:
        if txn.from_agent is None or txn.to_agent is None:
            pengirim, penerima = await _ambil_agent_pasangan(sesi_database, txn)
        else:
            pengirim, penerima = txn.from_agent, txn.to_agent
        items.append(
            TransactionListItem(
                id=txn.id,
                from_agent=pengirim.agent_id,
                to_agent=penerima.agent_id,
                amount=txn.amount,
                status=txn.status.value,
                created_at=txn.created_at,
            )
        )

    return TransactionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(txn_id: UUID, sesi_database: AsyncSession = Depends(get_db)) -> TransactionResponse:
    kueri_transaksi = select(Transaction).where(Transaction.id == txn_id)
    hasil_transaksi = await sesi_database.execute(kueri_transaksi)
    transaksi_aktif = hasil_transaksi.scalar_one_or_none()
    if transaksi_aktif is None:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    agent_pengirim, agent_penerima = await _ambil_agent_pasangan(sesi_database, transaksi_aktif)
    return _bangun_respons_transaksi(transaksi_aktif, agent_pengirim, agent_penerima)
