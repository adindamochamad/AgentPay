from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TransactionStatus(str, Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    EXPIRED = "EXPIRED"


STATUS_TERMINAL: frozenset[TransactionStatus] = frozenset(
    {
        TransactionStatus.SETTLED,
        TransactionStatus.FAILED,
        TransactionStatus.ROLLED_BACK,
        TransactionStatus.EXPIRED,
    }
)


class JejakNonce(Base):
    """Nonce aksi yang sudah dipakai (anti-replay di luar baris transaksi)."""

    __tablename__ = "jejak_nonce"

    nonce: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (CheckConstraint("balance >= 0", name="cek_saldo_agents_tidak_negatif"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    public_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    sent_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction",
        foreign_keys="Transaction.from_agent_id",
        back_populates="from_agent",
    )
    received_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction",
        foreign_keys="Transaction.to_agent_id",
        back_populates="to_agent",
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_status_created_at", "status", "created_at"),
        Index("ix_transactions_from_agent_id_status", "from_agent_id", "status"),
        Index("ix_transactions_to_agent_id_status", "to_agent_id", "status"),
        Index("ix_transactions_timeout_at_status", "timeout_at", "status"),
        UniqueConstraint(
            "from_agent_id",
            "idempotency_key",
            name="uq_transactions_from_agent_idempotency_key",
        ),
        CheckConstraint("amount > 0", name="cek_nominal_transaksi_positif"),
        CheckConstraint("from_agent_id <> to_agent_id", name="cek_transaksi_bukan_bayar_diri"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    from_agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    to_agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        SqlEnum(TransactionStatus, name="transaction_status"),
        nullable=False,
        default=TransactionStatus.INITIATED,
    )
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB(astext_type=Text()).with_variant(JSON(), "sqlite"),  # type: ignore[no-untyped-call]
        nullable=True,
    )
    signature: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    rolled_back_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    from_agent: Mapped[Agent] = relationship(
        "Agent",
        foreign_keys=[from_agent_id],
        back_populates="sent_transactions",
    )
    to_agent: Mapped[Agent] = relationship(
        "Agent",
        foreign_keys=[to_agent_id],
        back_populates="received_transactions",
    )

    def is_expired(self, waktu_referensi: datetime | None = None) -> bool:
        """
        Mengembalikan True jika waktu referensi sudah melewati batas timeout_at.

        Catatan: pemanggil biasanya juga mengecek status agar tidak menandai transaksi
        terminal sebagai kedaluwarsa untuk alur bisnis.
        """
        if self.timeout_at is None:
            return False
        acuan = waktu_referensi or utcnow()
        batas = self.timeout_at
        # SQLite sering mengembalikan datetime naive; samakan zona agar perbandingan aman
        if batas.tzinfo is None:
            batas = batas.replace(tzinfo=timezone.utc)
        if acuan.tzinfo is None:
            acuan = acuan.replace(tzinfo=timezone.utc)
        return acuan > batas

    def is_terminal(self) -> bool:
        """True jika status transaksi tidak boleh bertransisi lagi."""
        return self.status in STATUS_TERMINAL
