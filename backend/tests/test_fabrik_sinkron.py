"""Pengujian pabrik Factory Boy dengan SQLite sinkron (terpisah dari engine async aplikasi)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Agent, Transaction, TransactionStatus
from tests.pabrik_model import PabrikAgent, PabrikTransaksi


def test_pabrik_agent_dan_transaksi_sinkron() -> None:
    mesin = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(mesin)
    pabrik_sesi = sessionmaker(bind=mesin, expire_on_commit=False)
    sesi = pabrik_sesi()
    PabrikAgent._meta.sqlalchemy_session = sesi
    PabrikTransaksi._meta.sqlalchemy_session = sesi
    try:
        pengirim = PabrikAgent.create(balance=Decimal("50"))
        penerima = PabrikAgent.create(agent_id="penerima_khusus")
        txn = PabrikTransaksi.create(
            from_agent_id=pengirim.id,
            to_agent_id=penerima.id,
            amount=Decimal("5"),
            status=TransactionStatus.INITIATED,
        )
        assert txn.from_agent_id == pengirim.id
        assert txn.amount == Decimal("5")
        disimpan = sesi.get(Transaction, txn.id)
        assert disimpan is not None
    finally:
        sesi.close()
