"""day3 ed25519 nonce jejak_nonce agents public_key required

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a7
Create Date: 2026-05-01 14:00:00.000000

"""
from __future__ import annotations

import base64
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import text


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jejak_nonce",
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("nonce"),
    )

    op.add_column("transactions", sa.Column("nonce", sa.String(length=128), nullable=True))

    bind = op.get_bind()
    hasil = bind.execute(text("SELECT id FROM transactions WHERE nonce IS NULL"))
    for baris in hasil.fetchall():
        bind.execute(
            text("UPDATE transactions SET nonce = :n WHERE id = :i"),
            {"n": str(uuid.uuid4()), "i": baris[0]},
        )

    op.alter_column("transactions", "nonce", existing_type=sa.String(length=128), nullable=False)
    op.create_index("ix_transactions_nonce", "transactions", ["nonce"], unique=True)

    hasil_agent = bind.execute(text("SELECT id FROM agents WHERE public_key IS NULL"))
    for baris in hasil_agent.fetchall():
        kunci_privat = Ed25519PrivateKey.generate()
        byte_publik = kunci_privat.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        teks_publik = base64.b64encode(byte_publik).decode("ascii")
        bind.execute(
            text("UPDATE agents SET public_key = :k WHERE id = :i"),
            {"k": teks_publik, "i": baris[0]},
        )

    op.alter_column("agents", "public_key", existing_type=sa.String(length=255), nullable=False)
    op.create_index("ix_agents_public_key", "agents", ["public_key"], unique=True)

    op.alter_column(
        "transactions",
        "signature",
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "transactions",
        "signature",
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.drop_index("ix_agents_public_key", table_name="agents")
    op.alter_column("agents", "public_key", existing_type=sa.String(length=255), nullable=True)
    op.drop_index("ix_transactions_nonce", table_name="transactions")
    op.drop_column("transactions", "nonce")
    op.drop_table("jejak_nonce")
