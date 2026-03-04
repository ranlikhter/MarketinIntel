"""Add snoozed_until column to price_alerts.

Allows users to temporarily silence an alert without deleting it.
The alert resumes firing normally once the snooze period expires.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_alerts",
        sa.Column("snoozed_until", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("price_alerts", "snoozed_until")
