"""day4 constraints balance amount selfpay metadata jsonb

Revision ID: e3f4a5b6c7d8
Revises: c1d2e3f4a5b6
Create Date: 2026-05-02 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "cek_saldo_agents_tidak_negatif",
        "agents",
        "balance >= 0",
    )
    op.create_check_constraint(
        "cek_nominal_transaksi_positif",
        "transactions",
        "amount > 0",
    )
    op.create_check_constraint(
        "cek_transaksi_bukan_bayar_diri",
        "transactions",
        "from_agent_id <> to_agent_id",
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "transactions",
            "metadata",
            existing_type=sa.JSON(),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_nullable=True,
            postgresql_using="metadata::jsonb",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "ALTER TABLE transactions ALTER COLUMN metadata "
                "TYPE JSON USING metadata::json"
            )
        )

    op.drop_constraint("cek_transaksi_bukan_bayar_diri", "transactions", type_="check")
    op.drop_constraint("cek_nominal_transaksi_positif", "transactions", type_="check")
    op.drop_constraint("cek_saldo_agents_tidak_negatif", "agents", type_="check")
