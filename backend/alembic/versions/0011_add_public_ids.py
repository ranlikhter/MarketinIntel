"""Add stable public UUIDs for externally-addressable entities

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PUBLIC_ID_TABLES: tuple[str, ...] = (
    "users",
    "workspaces",
    "products_monitored",
    "competitor_matches",
    "price_alerts",
    "saved_views",
    "repricing_rules",
    "api_keys",
    "store_connections",
)


def _require_postgresql() -> sa.engine.Connection:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError(
            "Migration 0011_add_public_ids requires PostgreSQL. "
            "Run it after the PostgreSQL cutover, not on the legacy SQLite database."
        )
    return bind


def upgrade() -> None:
    _require_postgresql()

    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    for table_name in PUBLIC_ID_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "public_id",
                sa.String(length=36),
                nullable=False,
                server_default=sa.text("gen_random_uuid()::text"),
            ),
        )
        op.create_index(
            f"ux_{table_name}_public_id",
            table_name,
            ["public_id"],
            unique=True,
        )


def downgrade() -> None:
    _require_postgresql()

    for table_name in reversed(PUBLIC_ID_TABLES):
        op.drop_index(f"ux_{table_name}_public_id", table_name=table_name)
        op.drop_column(table_name, "public_id")
