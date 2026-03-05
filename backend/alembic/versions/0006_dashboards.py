"""Add dashboards and dashboard_widgets tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-05

Changes:
  NEW TABLE: dashboards        — user-owned named dashboard canvases
  NEW TABLE: dashboard_widgets — individual chart/KPI widgets on each dashboard
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column("id",          sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("user_id",     sa.Integer(),     sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",        sa.String(200),   nullable=False),
        sa.Column("description", sa.Text(),        nullable=True),
        sa.Column("is_default",  sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("created_at",  sa.DateTime(),    server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(),    server_default=sa.func.now()),
    )
    op.create_index("idx_db_user", "dashboards", ["user_id"])

    op.create_table(
        "dashboard_widgets",
        sa.Column("id",           sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column("dashboard_id", sa.Integer(),    sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("widget_type",  sa.String(50),   nullable=False),
        sa.Column("title",        sa.String(200),  nullable=True),
        # Layout: flex-wrap order + width class
        sa.Column("position",     sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("size",         sa.String(20),   nullable=False, server_default="medium"),  # small|medium|large|tall-medium|tall-large
        # Widget data config stored as JSON
        sa.Column("config",       sa.JSON(),       nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.DateTime(),   server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(),   server_default=sa.func.now()),
    )
    op.create_index("idx_dw_dashboard", "dashboard_widgets", ["dashboard_id", "position"])


def downgrade() -> None:
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
