"""Add user_id to competitor_websites for per-user isolation (IDOR fix)

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-10

Changes:
  competitor_websites — add user_id FK (nullable for backwards-compat with
  existing rows; new rows are always created with the authenticated user's id)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "competitor_websites",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_competitor_websites_user_id", "competitor_websites", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_competitor_websites_user_id", table_name="competitor_websites")
    op.drop_column("competitor_websites", "user_id")
