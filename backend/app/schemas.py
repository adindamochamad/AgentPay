from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SignedRequest(BaseModel):
    """Dasar untuk semua permintaan bertanda."""

    timestamp: str = Field(
        ...,
        description="Timestamp ISO8601 UTC; harus sama persis dengan nilai yang ditandatangani",
    )
    signature: str


class AgentCreateSigned(SignedRequest):
    """Pembuatan agen dengan kunci publik Ed25519."""

    agent_id: str
    initial_balance: Decimal = Field(default=Decimal("100.0"), ge=Decimal("0"))
    public_key: str


class TransactionCreateSigned(SignedRequest):
    """Inisiasi transaksi dengan nonce anti-replay."""

    from_agent: str
    to_agent: str
    amount: Decimal = Field(
        gt=Decimal("0"),
        ge=Decimal("0.00000001"),
        le=Decimal("1000000"),
    )
    nonce: str = Field(..., min_length=8, max_length=128)


class TransactionActionSigned(SignedRequest):
    """Aksi terima / konfirmasi / batal pada transaksi."""

    agent_id: str
    transaction_id: UUID
    nonce: str = Field(..., min_length=8, max_length=128)
    reason: Optional[str] = Field(default=None, max_length=512)


class TransactionDisputeSigned(SignedRequest):
    """Sengketa transaksi yang ditandatangani."""

    agent_id: str
    transaction_id: UUID
    justification: str = Field(min_length=1, max_length=2000)
    nonce: str = Field(..., min_length=8, max_length=128)


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    balance: Decimal
    created_at: datetime


class TransactionResponse(BaseModel):
    id: UUID
    from_agent: str
    to_agent: str
    amount: Decimal
    status: str
    created_at: datetime
    timeout_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    rolled_back_reason: Optional[str] = None


class TransactionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_agent: str
    to_agent: str
    amount: Decimal
    status: str
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionListItem]
    total: int
    limit: int
    offset: int


class BalanceResponse(BaseModel):
    agent_id: str
    balance: Decimal
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    status: str
