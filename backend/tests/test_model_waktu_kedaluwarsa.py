"""Cabang is_expired untuk datetime naive vs aware."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import Transaction, TransactionStatus, utcnow


def test_is_expired_timeout_naive_dibandingkan_dengan_referensi_aware() -> None:
    batas_naive = (utcnow() - timedelta(minutes=1)).replace(tzinfo=None)
    txn = Transaction(
        from_agent_id=uuid4(),
        to_agent_id=uuid4(),
        amount=Decimal("1"),
        status=TransactionStatus.INITIATED,
        nonce=str(uuid4()),
        timeout_at=batas_naive,
    )
    assert txn.is_expired(utcnow()) is True


def test_is_expired_tanpa_timeout() -> None:
    txn = Transaction(
        from_agent_id=uuid4(),
        to_agent_id=uuid4(),
        amount=Decimal("1"),
        status=TransactionStatus.INITIATED,
        nonce=str(uuid4()),
        timeout_at=None,
    )
    assert txn.is_expired() is False


def test_is_expired_acuan_naive_disamakan_ke_utc() -> None:
    batas = (utcnow() - timedelta(minutes=2)).replace(tzinfo=timezone.utc)
    acuan_naif = datetime.utcnow()
    txn = Transaction(
        from_agent_id=uuid4(),
        to_agent_id=uuid4(),
        amount=Decimal("1"),
        status=TransactionStatus.INITIATED,
        nonce=str(uuid4()),
        timeout_at=batas,
    )
    assert txn.is_expired(acuan_naif) is True
