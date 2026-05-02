"""Dependensi FastAPI untuk verifikasi tanda Ed25519."""

from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.crypto import Ed25519Crypto
from app.database import SessionLocal
from app.models import Agent, JejakNonce, Transaction
from app.schemas import (
    AgentCreateSigned,
    TransactionActionSigned,
    TransactionCreateSigned,
    TransactionDisputeSigned,
)


def waktu_utc_dari_iso(teks_timestamp: str) -> datetime:
    """Mengurai string ISO ke datetime timezone-aware UTC."""
    teks_normal = teks_timestamp.strip()
    if teks_normal.endswith("Z"):
        teks_normal = teks_normal[:-1] + "+00:00"
    hasil = datetime.fromisoformat(teks_normal)
    if hasil.tzinfo is None:
        hasil = hasil.replace(tzinfo=timezone.utc)
    return hasil.astimezone(timezone.utc)


def muatan_tanpa_tanda(body: dict[str, Any]) -> dict[str, Any]:
    """Menyalin body permintaan tanpa field signature (untuk verifikasi)."""
    return {k: v for k, v in body.items() if k != "signature"}


async def catat_nonce_terkomit(nonce: str) -> None:
    """
    Mencatat nonce di basis data dengan transaksi terpisah agar tidak ikut rollback
    jika logika rute gagal setelah verifikasi tanda.
    """
    async with SessionLocal() as sesi_pendek:
        async with sesi_pendek.begin():
            sesi_pendek.add(JejakNonce(nonce=nonce))


async def verifikasi_umum_timestamp_dan_tanda(
    body: dict[str, Any],
    kunci_publik_base64: str,
) -> None:
    """Memvalidasi usia timestamp dan kecocokan tanda Ed25519."""
    tanda = body.get("signature")
    teks_timestamp = body.get("timestamp")
    if not tanda or not teks_timestamp:
        raise HTTPException(status_code=400, detail="Tanda atau timestamp hilang")

    try:
        waktu_permintaan = waktu_utc_dari_iso(str(teks_timestamp))
    except ValueError as galat:
        raise HTTPException(status_code=400, detail="Format timestamp tidak valid") from galat

    pengaturan = get_settings()
    sekarang_utc = datetime.now(timezone.utc)
    usia_detik = (sekarang_utc - waktu_permintaan).total_seconds()
    if usia_detik > float(pengaturan.SIGNATURE_MAX_AGE_SECONDS):
        raise HTTPException(
            status_code=400,
            detail=(
                "Timestamp permintaan terlalu lama "
                f"(maksimal {pengaturan.SIGNATURE_MAX_AGE_SECONDS} detik)"
            ),
        )
    if usia_detik < -float(pengaturan.SIGNATURE_MAX_FUTURE_SKEW_SECONDS):
        raise HTTPException(status_code=400, detail="Timestamp permintaan di masa depan tidak diizinkan")

    pesan = muatan_tanpa_tanda(body)
    if not Ed25519Crypto.verify_signature(kunci_publik_base64, pesan, str(tanda)):
        raise HTTPException(status_code=401, detail="Tanda tidak valid")


async def dependensi_pembuatan_agen(permintaan: Request) -> AgentCreateSigned:
    """Memverifikasi tanda permintaan pembuatan agen (kunci publik ada di body)."""
    try:
        body = await permintaan.json()
    except Exception as galat:
        raise HTTPException(status_code=400, detail="Body JSON tidak valid") from galat

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body harus berupa objek JSON")

    kunci_publik = body.get("public_key")
    if not kunci_publik or not isinstance(kunci_publik, str):
        raise HTTPException(status_code=400, detail="public_key wajib diisi")

    await verifikasi_umum_timestamp_dan_tanda(body, kunci_publik)

    try:
        return AgentCreateSigned.model_validate(body)
    except Exception as galat:
        raise HTTPException(status_code=422, detail="Skema pembuatan agen tidak valid") from galat


async def dependensi_pembuatan_transaksi(permintaan: Request) -> TransactionCreateSigned:
    """Memverifikasi tanda pengirim untuk inisiasi transaksi (sesi baca terpisah dari rute)."""
    try:
        body = await permintaan.json()
    except Exception as galat:
        raise HTTPException(status_code=400, detail="Body JSON tidak valid") from galat

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body harus berupa objek JSON")

    id_pengirim = body.get("from_agent")
    if not id_pengirim:
        raise HTTPException(status_code=400, detail="from_agent wajib untuk mengidentifikasi penandatangan")

    async with SessionLocal() as sesi_baca:
        kueri_agent = select(Agent).where(Agent.agent_id == str(id_pengirim))
        hasil = await sesi_baca.execute(kueri_agent)
        agent_pengirim = hasil.scalar_one_or_none()
    if agent_pengirim is None:
        raise HTTPException(status_code=404, detail=f"Agent pengirim '{id_pengirim}' tidak ditemukan")
    if not agent_pengirim.public_key:
        raise HTTPException(status_code=400, detail="Agent pengirim belum memiliki kunci publik terdaftar")

    await verifikasi_umum_timestamp_dan_tanda(body, agent_pengirim.public_key)

    try:
        return TransactionCreateSigned.model_validate(body)
    except Exception as galat:
        raise HTTPException(status_code=422, detail="Skema transaksi tidak valid") from galat


def pabrik_verifikasi_aksi(
    peran_yang_diizinkan: Literal["penerima", "pengirim", "pengirim_atau_penerima"],
) -> Callable[[Request, UUID], Awaitable[TransactionActionSigned]]:
    """
    Membangun dependensi verifikasi untuk aksi transaksi (terima / konfirmasi / batal).

    peran_yang_diizinkan:
        penerima — hanya to_agent (mis. accept)
        pengirim — hanya from_agent (mis. confirm)
        pengirim_atau_penerima — cancel
    """

    async def dependensi(permintaan: Request, txn_id: UUID) -> TransactionActionSigned:
        try:
            body = await permintaan.json()
        except Exception as galat:
            raise HTTPException(status_code=400, detail="Body JSON tidak valid") from galat

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Body harus berupa objek JSON")

        id_body = body.get("transaction_id")
        if id_body is None:
            raise HTTPException(status_code=400, detail="transaction_id wajib di body dan harus cocok dengan URL")
        try:
            id_transaksi_body = UUID(str(id_body))
        except ValueError as galat:
            raise HTTPException(status_code=400, detail="transaction_id tidak valid") from galat

        if id_transaksi_body != txn_id:
            raise HTTPException(status_code=400, detail="transaction_id tidak cocok dengan path")

        id_agen_aksi = body.get("agent_id")
        if not id_agen_aksi:
            raise HTTPException(status_code=400, detail="agent_id wajib")

        async with SessionLocal() as sesi_baca:
            kueri_txn = select(Transaction).where(Transaction.id == txn_id)
            hasil_txn = await sesi_baca.execute(kueri_txn)
            transaksi = hasil_txn.scalar_one_or_none()
            if transaksi is None:
                raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

            kueri_kedua_agen = select(Agent).where(
                Agent.id.in_([transaksi.from_agent_id, transaksi.to_agent_id])
            )
            hasil_agens = await sesi_baca.execute(kueri_kedua_agen)
            daftar_agent = hasil_agens.scalars().all()
        peta = {a.id: a for a in daftar_agent}
        agen_pengirim = peta.get(transaksi.from_agent_id)
        agen_penerima = peta.get(transaksi.to_agent_id)
        if agen_pengirim is None or agen_penerima is None:
            raise HTTPException(status_code=500, detail="Data agen transaksi tidak lengkap")

        agen_penandatangan: Agent | None = None
        if peran_yang_diizinkan == "penerima":
            if str(id_agen_aksi) != agen_penerima.agent_id:
                raise HTTPException(status_code=403, detail="Hanya penerima yang dapat menandatangani aksi ini")
            agen_penandatangan = agen_penerima
        elif peran_yang_diizinkan == "pengirim":
            if str(id_agen_aksi) != agen_pengirim.agent_id:
                raise HTTPException(status_code=403, detail="Hanya pengirim yang dapat menandatangani aksi ini")
            agen_penandatangan = agen_pengirim
        else:
            if str(id_agen_aksi) == agen_pengirim.agent_id:
                agen_penandatangan = agen_pengirim
            elif str(id_agen_aksi) == agen_penerima.agent_id:
                agen_penandatangan = agen_penerima
            else:
                raise HTTPException(
                    status_code=403,
                    detail="agent_id harus pengirim atau penerima untuk aksi ini",
                )

        if not agen_penandatangan.public_key:
            raise HTTPException(status_code=400, detail="Agent penandatangan belum memiliki kunci publik")

        await verifikasi_umum_timestamp_dan_tanda(body, agen_penandatangan.public_key)

        try:
            muatan = TransactionActionSigned.model_validate(body)
        except Exception as galat:
            raise HTTPException(status_code=422, detail="Skema aksi transaksi tidak valid") from galat

        try:
            await catat_nonce_terkomit(muatan.nonce)
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Nonce sudah pernah digunakan (replay)") from None

        return muatan

    return dependensi


async def dependensi_sengketa_transaksi(permintaan: Request, txn_id: UUID) -> TransactionDisputeSigned:
    try:
        body = await permintaan.json()
    except Exception as galat:
        raise HTTPException(status_code=400, detail="Body JSON tidak valid") from galat

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body harus berupa objek JSON")

    id_body = body.get("transaction_id")
    if id_body is None:
        raise HTTPException(status_code=400, detail="transaction_id wajib")
    try:
        id_transaksi_body = UUID(str(id_body))
    except ValueError as galat:
        raise HTTPException(status_code=400, detail="transaction_id tidak valid") from galat

    if id_transaksi_body != txn_id:
        raise HTTPException(status_code=400, detail="transaction_id tidak cocok dengan path")

    id_agen_aksi = body.get("agent_id")
    if not id_agen_aksi:
        raise HTTPException(status_code=400, detail="agent_id wajib")

    async with SessionLocal() as sesi_baca:
        kueri_txn = select(Transaction).where(Transaction.id == txn_id)
        hasil_txn = await sesi_baca.execute(kueri_txn)
        transaksi = hasil_txn.scalar_one_or_none()
        if transaksi is None:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

        kueri_kedua_agen = select(Agent).where(
            Agent.id.in_([transaksi.from_agent_id, transaksi.to_agent_id])
        )
        hasil_agens = await sesi_baca.execute(kueri_kedua_agen)
        daftar_agent = hasil_agens.scalars().all()
    peta = {a.id: a for a in daftar_agent}
    agen_pengirim = peta.get(transaksi.from_agent_id)
    agen_penerima = peta.get(transaksi.to_agent_id)
    if agen_pengirim is None or agen_penerima is None:
        raise HTTPException(status_code=500, detail="Data agen transaksi tidak lengkap")

    agen_penandatangan: Agent | None = None
    if str(id_agen_aksi) == agen_pengirim.agent_id:
        agen_penandatangan = agen_pengirim
    elif str(id_agen_aksi) == agen_penerima.agent_id:
        agen_penandatangan = agen_penerima
    else:
        raise HTTPException(status_code=403, detail="agent_id harus pengirim atau penerima transaksi")

    if not agen_penandatangan.public_key:
        raise HTTPException(status_code=400, detail="Agent penandatangan belum memiliki kunci publik")

    await verifikasi_umum_timestamp_dan_tanda(body, agen_penandatangan.public_key)

    try:
        muatan = TransactionDisputeSigned.model_validate(body)
    except Exception as galat:
        raise HTTPException(status_code=422, detail="Skema sengketa tidak valid") from galat

    try:
        await catat_nonce_terkomit(muatan.nonce)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Nonce sudah pernah digunakan (replay)") from None

    return muatan


verifikasi_terima_transaksi = pabrik_verifikasi_aksi("penerima")
verifikasi_konfirmasi_transaksi = pabrik_verifikasi_aksi("pengirim")
verifikasi_batal_transaksi = pabrik_verifikasi_aksi("pengirim_atau_penerima")
