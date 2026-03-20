"""Add performance indexes for catalog and alert queries

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_pa_user_enabled",
        "price_alerts",
        ["user_id", "enabled"],
        unique=False,
    )
    op.create_index(
        "idx_mph_product_changed",
        "my_price_history",
        ["product_id", "changed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_mph_product_changed", table_name="my_price_history")
    op.drop_index("idx_pa_user_enabled", table_name="price_alerts")
