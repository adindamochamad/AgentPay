from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.crypto import Ed25519Crypto
from app.routes.agents import get_balance, layanan_simpan_agent
from app.routes.transactions import (
    get_transaction,
    layanan_inisiasi_pembayaran,
    layanan_konfirmasi_transaksi,
    layanan_terima_transaksi,
)
from app.schemas import AgentCreateSigned, TransactionCreateSigned
from app.utils.exceptions import InsufficientBalanceException, InvalidTransactionStateException


def _buat_agen_dengan_kunci(agent_id: str, saldo: str) -> tuple[AgentCreateSigned, str]:
    """Mengembalikan muatan agen dan kunci privat yang cocok dengan public_key terdaftar."""
    privat, publik = Ed25519Crypto.generate_keypair()
    stempel = datetime.now(timezone.utc).isoformat()
    pesan = {
        "agent_id": agent_id,
        "initial_balance": saldo,
        "public_key": publik,
        "timestamp": stempel,
    }
    tanda = Ed25519Crypto.sign_message(privat, pesan)
    return AgentCreateSigned.model_validate({**pesan, "signature": tanda}), privat


def _transaksi_tanda(dari: str, ke: str, jumlah: str, privat_pengirim: str) -> TransactionCreateSigned:
    stempel = datetime.now(timezone.utc).isoformat()
    pesan = {
        "from_agent": dari,
        "to_agent": ke,
        "amount": jumlah,
        "nonce": str(uuid4()),
        "timestamp": stempel,
    }
    tanda = Ed25519Crypto.sign_message(privat_pengirim, pesan)
    return TransactionCreateSigned.model_validate({**pesan, "signature": tanda})


@pytest.mark.asyncio
async def test_unit_alur_agent(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi_database:
        muatan, _ = _buat_agen_dengan_kunci("agen_unit", "120.00")
        respons_buat = await layanan_simpan_agent(sesi_database, muatan)
        assert respons_buat.agent_id == "agen_unit"

        respons_saldo = await get_balance("agen_unit", sesi_database)
        assert respons_saldo.balance == Decimal("120.00000000")


@pytest.mark.asyncio
async def test_unit_transaksi_lengkap(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi_database:
        muatan_p, privat_p = _buat_agen_dengan_kunci("pengirim_unit", "200.00")
        muatan_r, _ = _buat_agen_dengan_kunci("penerima_unit", "20.00")
        await layanan_simpan_agent(sesi_database, muatan_p)
        await layanan_simpan_agent(sesi_database, muatan_r)

        respons_mulai = await layanan_inisiasi_pembayaran(
            sesi_database,
            _transaksi_tanda("pengirim_unit", "penerima_unit", "15.00", privat_p),
            None,
        )
        id_transaksi = UUID(str(respons_mulai.id))

    async with pabrik_sesi_uji() as sesi_database:
        respons_terima = await layanan_terima_transaksi(sesi_database, id_transaksi)
        assert respons_terima.status == "PENDING"

    async with pabrik_sesi_uji() as sesi_database:
        respons_konfirmasi = await layanan_konfirmasi_transaksi(sesi_database, id_transaksi)
        assert respons_konfirmasi.status == "SETTLED"

    async with pabrik_sesi_uji() as sesi_database:
        respons_detail = await get_transaction(id_transaksi, sesi_database)
        assert respons_detail.status == "SETTLED"


@pytest.mark.asyncio
async def test_unit_transaksi_gagal_saldo(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi_database:
        muatan_p, privat_p = _buat_agen_dengan_kunci("pengirim_gagal_unit", "2.00")
        muatan_r, _ = _buat_agen_dengan_kunci("penerima_gagal_unit", "1.00")
        await layanan_simpan_agent(sesi_database, muatan_p)
        await layanan_simpan_agent(sesi_database, muatan_r)

        with pytest.raises(InsufficientBalanceException):
            await layanan_inisiasi_pembayaran(
                sesi_database,
                _transaksi_tanda(
                    "pengirim_gagal_unit",
                    "penerima_gagal_unit",
                    "9.00",
                    privat_p,
                ),
                None,
            )


@pytest.mark.asyncio
async def test_unit_accept_status_tidak_valid(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi_database:
        muatan_p, privat_p = _buat_agen_dengan_kunci("pengirim_status", "50.00")
        muatan_r, _ = _buat_agen_dengan_kunci("penerima_status", "5.00")
        await layanan_simpan_agent(sesi_database, muatan_p)
        await layanan_simpan_agent(sesi_database, muatan_r)
        respons_mulai = await layanan_inisiasi_pembayaran(
            sesi_database,
            _transaksi_tanda("pengirim_status", "penerima_status", "10.00", privat_p),
            None,
        )
        id_transaksi = UUID(str(respons_mulai.id))

    async with pabrik_sesi_uji() as sesi_database:
        await layanan_terima_transaksi(sesi_database, id_transaksi)

    async with pabrik_sesi_uji() as sesi_database:
        with pytest.raises(InvalidTransactionStateException):
            await layanan_terima_transaksi(sesi_database, id_transaksi)
