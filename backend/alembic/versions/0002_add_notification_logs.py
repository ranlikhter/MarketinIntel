"""Add notification_logs table (v11).

Tracks every notification attempt (email/SMS/Slack/Discord/push) so users can
view their alert delivery history and ops can diagnose channel failures.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.Integer, sa.ForeignKey("price_alerts.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )
    op.create_index("idx_nl_user_sent", "notification_logs", ["user_id", sa.text("sent_at DESC")])


def downgrade() -> None:
    op.drop_index("idx_nl_user_sent", table_name="notification_logs")
    op.drop_table("notification_logs")
