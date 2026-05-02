"""day2 state machine columns and EXPIRED enum

Revision ID: b2c3d4e5f6a7
Revises: a5e9a8305f40
Create Date: 2026-05-01 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a5e9a8305f40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                DO $enum_add$
                BEGIN
                    ALTER TYPE transaction_status ADD VALUE 'EXPIRED';
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END
                $enum_add$;
                """
            )
        )

    op.add_column(
        "transactions",
        sa.Column("timeout_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("transactions", sa.Column("failure_reason", sa.String(length=512), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("rolled_back_reason", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_transactions_from_agent_idempotency_key",
        "transactions",
        ["from_agent_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_transactions_from_agent_idempotency_key", "transactions", type_="unique")
    op.drop_column("transactions", "idempotency_key")
    op.drop_column("transactions", "confirmed_at")
    op.drop_column("transactions", "rolled_back_reason")
    op.drop_column("transactions", "failure_reason")
    op.drop_column("transactions", "timeout_at")
    # Menghapus nilai ENUM di PostgreSQL tidak didukung dengan aman; lewati pada downgrade.
