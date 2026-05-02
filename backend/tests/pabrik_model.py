"""
Pabrik data uji (Factory Boy) untuk model ORM.

Dipakai dengan sesi SQLAlchemy sinkron kecil di test_fabrik_sinkron.py agar tidak bentrok
dengan async engine aplikasi utama.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.crypto import Ed25519Crypto
from app.models import Agent, Transaction, TransactionStatus


class PabrikAgent(SQLAlchemyModelFactory):
    """Pabrik baris Agent untuk pengujian."""

    class Meta:
        model = Agent
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    agent_id = factory.Sequence(lambda indeks: f"agen_uji_{indeks}")
    public_key = factory.LazyAttribute(lambda _: Ed25519Crypto.generate_keypair()[1])
    balance = Decimal("100.0")


class PabrikTransaksi(SQLAlchemyModelFactory):
    """Pabrik baris Transaction (perlu agen pengirim & penerima yang sudah ada)."""

    class Meta:
        model = Transaction
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    amount = Decimal("10.0")
    status = TransactionStatus.INITIATED
    signature = factory.LazyAttribute(lambda _: "tanda_uji_" + str(uuid.uuid4()))
    nonce = factory.LazyFunction(lambda: str(uuid.uuid4()))
