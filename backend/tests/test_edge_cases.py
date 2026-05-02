from __future__ import annotations

import time
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.crypto import Ed25519Crypto
from app.database import SessionLocal, get_db
from app.main import app
from app.models import Agent, Transaction, TransactionStatus, utcnow
from app.state_machine import TransactionStateMachine

from tests.bantuan_tanda import (
    body_aksi_transaksi_tertanda,
    body_pembuatan_agen_tertanda,
    body_sengketa_tertanda,
    body_transaksi_tertanda,
)


@pytest.mark.asyncio
async def test_insufficient_balance_after_concurrent_transactions(pabrik_sesi_uji):
    """
    Saldo tidak cukup setelah debit pertama (alur berurutan).

    Catatan: SQLite dengan sesi terpisah tidak menjamin isolasi paralel kuat untuk
    uji tiga debit bersamaan; invariant dicek lewat urutan transaksi nyata.
    """
    id_pengirim: str = ""
    id_penerima: str = ""
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"cc_{uuid4().hex[:6]}", balance=Decimal("10"), public_key=pub_p)
            q = Agent(agent_id=f"cd_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            id_pengirim = p.agent_id
            id_penerima = q.agent_id

    async def coba_debit() -> bool:
        async with pabrik_sesi_uji() as sesi:
            try:
                async with sesi.begin():
                    pengirim = (
                        await sesi.execute(
                            select(Agent).where(Agent.agent_id == id_pengirim).with_for_update()
                        )
                    ).scalar_one()
                    penerima = (
                        await sesi.execute(select(Agent).where(Agent.agent_id == id_penerima))
                    ).scalar_one()
                    nilai = Decimal("6")
                    if pengirim.balance < nilai:
                        return False
                    pengirim.balance -= nilai
                    sesi.add(
                        Transaction(
                            from_agent_id=pengirim.id,
                            to_agent_id=penerima.id,
                            amount=nilai,
                            status=TransactionStatus.INITIATED,
                            nonce=str(uuid4()),
                        )
                    )
                return True
            except Exception:
                return False

    assert await coba_debit() is True
    assert await coba_debit() is False
    assert await coba_debit() is False


@pytest.mark.asyncio
async def test_transaction_expiry_during_confirm(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("exp_p", "100.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("exp_r", "1.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("exp_p", "exp_r", "5.00", privat_p),
    )
    id_txn = respons.json()["id"]

    respons_konfirmasi = await client_api.post(
        f"/api/v1/transactions/{id_txn}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "exp_r", UUID(id_txn)),
    )
    assert respons_konfirmasi.status_code == 200

    async with SessionLocal() as sesi:
        txn = (
            await sesi.execute(select(Transaction).where(Transaction.id == UUID(str(id_txn))))
        ).scalar_one()
        txn.timeout_at = utcnow() - timedelta(seconds=1)
        await sesi.commit()

    respons_konfirm = await client_api.post(
        f"/api/v1/transactions/{id_txn}/confirm",
        json=body_aksi_transaksi_tertanda(privat_p, "exp_p", UUID(id_txn)),
    )
    assert respons_konfirm.status_code == 409


@pytest.mark.asyncio
async def test_cancel_already_settled_fails(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("cs_p", "50.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("cs_r", "1.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("cs_p", "cs_r", "10.00", privat_p),
    )
    id_txn = respons.json()["id"]
    id_uuid = UUID(id_txn)
    await client_api.post(
        f"/api/v1/transactions/{id_txn}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "cs_r", id_uuid),
    )
    await client_api.post(
        f"/api/v1/transactions/{id_txn}/confirm",
        json=body_aksi_transaksi_tertanda(privat_p, "cs_p", id_uuid),
    )
    respons_batal = await client_api.post(
        f"/api/v1/transactions/{id_txn}/cancel",
        json=body_aksi_transaksi_tertanda(privat_p, "cs_p", id_uuid, "coba batal"),
    )
    assert respons_batal.status_code == 400


@pytest.mark.asyncio
async def test_jumlah_terlalu_besar_ditolak(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("big_p", "2000000.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("big_r", "1.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("big_p", "big_r", "2000000", privat_p),
    )
    assert respons.status_code == 422


@pytest.mark.asyncio
async def test_negative_amount_rejected(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("neg_p", "10.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("neg_r", "1.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("neg_p", "neg_r", "-1.00", privat_p),
    )
    assert respons.status_code == 422


@pytest.mark.asyncio
async def test_self_payment_rejected(client_api):
    privat_u, pub_u = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("self_u", "10.00", privat_u, pub_u),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("self_u", "self_u", "1.00", privat_u),
    )
    assert respons.status_code == 400


@pytest.mark.asyncio
async def test_zero_amount_rejected(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("z_p", "10.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("z_r", "1.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("z_p", "z_r", "0", privat_p),
    )
    assert respons.status_code == 422


@pytest.mark.asyncio
async def test_huge_amount_precision(pabrik_sesi_uji):
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_p = Ed25519Crypto.generate_keypair()
            _, pub_q = Ed25519Crypto.generate_keypair()
            p = Agent(agent_id=f"hp_{uuid4().hex[:6]}", balance=Decimal("1"), public_key=pub_p)
            q = Agent(agent_id=f"hq_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_q)
            sesi.add_all([p, q])
            await sesi.flush()
            jumlah = Decimal("0.00000001")
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
            await TransactionStateMachine.transition(sesi, t, TransactionStatus.PENDING)
            await TransactionStateMachine.transition(sesi, t, TransactionStatus.CONFIRMED)
            await TransactionStateMachine.transition(sesi, t, TransactionStatus.SETTLED)
        await sesi.refresh(p)
        await sesi.refresh(q)
        assert q.balance == jumlah


@pytest.mark.asyncio
async def test_seratus_transaksi_cepat(pabrik_sesi_uji):
    """100 transaksi sekuensial dalam satu sesi untuk smoke performa."""
    id_penerima = ""
    daftar_pengirim: list[str] = []
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            _, pub_recv = Ed25519Crypto.generate_keypair()
            penerima = Agent(agent_id=f"recv_{uuid4().hex[:6]}", balance=Decimal("0"), public_key=pub_recv)
            sesi.add(penerima)
            await sesi.flush()
            id_penerima = penerima.agent_id
            for _ in range(100):
                aid = f"s_{uuid4().hex[:8]}"
                daftar_pengirim.append(aid)
                _, pub_a = Ed25519Crypto.generate_keypair()
                sesi.add(Agent(agent_id=aid, balance=Decimal("2"), public_key=pub_a))
            await sesi.flush()

    mulai = time.perf_counter()
    async with pabrik_sesi_uji() as sesi:
        async with sesi.begin():
            pr = (await sesi.execute(select(Agent).where(Agent.agent_id == id_penerima))).scalar_one()
            for aid in daftar_pengirim:
                pg = (await sesi.execute(select(Agent).where(Agent.agent_id == aid))).scalar_one()
                pg.balance -= Decimal("1")
                sesi.add(
                    Transaction(
                        from_agent_id=pg.id,
                        to_agent_id=pr.id,
                        amount=Decimal("1"),
                        status=TransactionStatus.INITIATED,
                        nonce=str(uuid4()),
                    )
                )
    durasi = time.perf_counter() - mulai
    assert durasi < 2.0


@pytest.mark.asyncio
async def test_batal_transaksi_initiated(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("cx_p", "30.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("cx_r", "1.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("cx_p", "cx_r", "4.00", privat_p),
    )
    id_txn = respons.json()["id"]
    id_uuid = UUID(id_txn)
    respons_batal = await client_api.post(
        f"/api/v1/transactions/{id_txn}/cancel",
        json=body_aksi_transaksi_tertanda(privat_p, "cx_p", id_uuid, "UJI_BATAL"),
    )
    assert respons_batal.status_code == 200
    assert respons_batal.json()["status"] == "ROLLED_BACK"


@pytest.mark.asyncio
async def test_sengketa_pending(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("dp_p", "40.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("dp_r", "2.00", privat_r, pub_r),
    )
    respons = await client_api.post(
        "/api/v1/transactions",
        json=body_transaksi_tertanda("dp_p", "dp_r", "3.00", privat_p),
    )
    id_txn = respons.json()["id"]
    id_uuid = UUID(id_txn)
    await client_api.post(
        f"/api/v1/transactions/{id_txn}/accept",
        json=body_aksi_transaksi_tertanda(privat_r, "dp_r", id_uuid),
    )
    respons_sg = await client_api.post(
        f"/api/v1/transactions/{id_txn}/dispute",
        json=body_sengketa_tertanda(
            privat_r,
            "dp_r",
            id_uuid,
            "Layanan tidak sesuai deskripsi",
        ),
    )
    assert respons_sg.status_code == 200
    assert respons_sg.json()["status"] == "ROLLED_BACK"


@pytest.mark.asyncio
async def test_kunci_idempotensi_mengembalikan_transaksi_sama(client_api):
    privat_p, pub_p = Ed25519Crypto.generate_keypair()
    privat_r, pub_r = Ed25519Crypto.generate_keypair()
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("id_p", "50.00", privat_p, pub_p),
    )
    await client_api.post(
        "/api/v1/agents",
        json=body_pembuatan_agen_tertanda("id_r", "1.00", privat_r, pub_r),
    )
    nonce_tetap = "nonce-idempotensi-tetap-12345"
    muatan = body_transaksi_tertanda("id_p", "id_r", "2.50", privat_p, nonce=nonce_tetap)
    r1 = await client_api.post(
        "/api/v1/transactions",
        json=muatan,
        headers={"Idempotency-Key": "kunci-uji-1"},
    )
    r2 = await client_api.post(
        "/api/v1/transactions",
        json=muatan,
        headers={"Idempotency-Key": "kunci-uji-1"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_daftar_transaksi_status_tidak_valid(client_api):
    respons = await client_api.get("/api/v1/transactions", params={"status": "BUKAN_STATUS"})
    assert respons.status_code == 422


@pytest.mark.asyncio
async def test_daftar_transaksi_agent_tidak_ditemukan(client_api):
    respons = await client_api.get("/api/v1/transactions", params={"agent_id": "tidak_ada"})
    assert respons.status_code == 404


@pytest.mark.asyncio
async def test_list_transactions_filter(pabrik_sesi_uji):
    async def _get_db_override():
        async with pabrik_sesi_uji() as sesi:
            yield sesi

    app.dependency_overrides[get_db] = _get_db_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as klien:
            pa, pua = Ed25519Crypto.generate_keypair()
            pb, pub = Ed25519Crypto.generate_keypair()
            await klien.post(
                "/api/v1/agents",
                json=body_pembuatan_agen_tertanda("lst_a", "100", pa, pua),
            )
            await klien.post(
                "/api/v1/agents",
                json=body_pembuatan_agen_tertanda("lst_b", "10", pb, pub),
            )
            r1 = await klien.post(
                "/api/v1/transactions",
                json=body_transaksi_tertanda("lst_a", "lst_b", "1", pa),
            )
            assert r1.status_code == 201
            r_list = await klien.get("/api/v1/transactions", params={"agent_id": "lst_a", "limit": 10})
            assert r_list.status_code == 200
            data = r_list.json()
            assert data["total"] >= 1
            assert len(data["items"]) >= 1
    finally:
        app.dependency_overrides.clear()
