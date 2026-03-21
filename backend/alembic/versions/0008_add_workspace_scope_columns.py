"""Add workspace ownership columns to enterprise-scoped tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORKSPACE_SCOPED_TABLES: tuple[str, ...] = (
    "products_monitored",
    "competitor_matches",
    "price_history",
    "review_snapshots",
    "listing_quality_snapshots",
    "keyword_ranks",
    "competitor_promotions",
    "my_price_history",
    "price_alerts",
    "repricing_rules",
    "api_keys",
    "store_connections",
    "activity_logs",
    "notification_logs",
    "push_subscriptions",
)


def _require_postgresql() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError(
            "Migration 0008_add_workspace_scope_columns requires PostgreSQL. "
            "Run it after the PostgreSQL cutover, not on the legacy SQLite database."
        )


def upgrade() -> None:
    _require_postgresql()

    op.add_column("users", sa.Column("default_workspace_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_default_workspace_id_workspaces",
        "users",
        "workspaces",
        ["default_workspace_id"],
        ["id"],
    )
    op.create_index(
        "idx_users_default_workspace",
        "users",
        ["default_workspace_id"],
        unique=False,
    )

    for table_name in WORKSPACE_SCOPED_TABLES:
        op.add_column(table_name, sa.Column("workspace_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table_name}_workspace_id_workspaces",
            table_name,
            "workspaces",
            ["workspace_id"],
            ["id"],
        )

    op.create_index(
        "idx_pm_workspace_created",
        "products_monitored",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_cm_workspace_product",
        "competitor_matches",
        ["workspace_id", "monitored_product_id"],
        unique=False,
    )
    op.create_index(
        "idx_cm_workspace_product_price",
        "competitor_matches",
        ["workspace_id", "monitored_product_id", "latest_price"],
        unique=False,
    )
    op.create_index(
        "idx_ph_workspace_match_time",
        "price_history",
        ["workspace_id", "match_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "idx_rs_workspace_match_time",
        "review_snapshots",
        ["workspace_id", "match_id", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "idx_lqs_workspace_match_time",
        "listing_quality_snapshots",
        ["workspace_id", "match_id", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "idx_kr_workspace_product_time",
        "keyword_ranks",
        ["workspace_id", "product_id", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "idx_cp_workspace_match_active",
        "competitor_promotions",
        ["workspace_id", "match_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_mph_workspace_product_changed",
        "my_price_history",
        ["workspace_id", "product_id", "changed_at"],
        unique=False,
    )
    op.create_index(
        "idx_pa_workspace_enabled",
        "price_alerts",
        ["workspace_id", "enabled"],
        unique=False,
    )
    op.create_index(
        "idx_rr_workspace_enabled_priority",
        "repricing_rules",
        ["workspace_id", "enabled", "priority"],
        unique=False,
    )
    op.create_index(
        "idx_ak_workspace_active",
        "api_keys",
        ["workspace_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_sc_workspace_platform_active",
        "store_connections",
        ["workspace_id", "platform", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_al_workspace_created",
        "activity_logs",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_nl_workspace_sent",
        "notification_logs",
        ["workspace_id", "sent_at"],
        unique=False,
    )
    op.create_index(
        "idx_ps_workspace_active",
        "push_subscriptions",
        ["workspace_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    _require_postgresql()

    op.drop_index("idx_ps_workspace_active", table_name="push_subscriptions")
    op.drop_index("idx_nl_workspace_sent", table_name="notification_logs")
    op.drop_index("idx_al_workspace_created", table_name="activity_logs")
    op.drop_index("idx_sc_workspace_platform_active", table_name="store_connections")
    op.drop_index("idx_ak_workspace_active", table_name="api_keys")
    op.drop_index("idx_rr_workspace_enabled_priority", table_name="repricing_rules")
    op.drop_index("idx_pa_workspace_enabled", table_name="price_alerts")
    op.drop_index("idx_mph_workspace_product_changed", table_name="my_price_history")
    op.drop_index("idx_cp_workspace_match_active", table_name="competitor_promotions")
    op.drop_index("idx_kr_workspace_product_time", table_name="keyword_ranks")
    op.drop_index("idx_lqs_workspace_match_time", table_name="listing_quality_snapshots")
    op.drop_index("idx_rs_workspace_match_time", table_name="review_snapshots")
    op.drop_index("idx_ph_workspace_match_time", table_name="price_history")
    op.drop_index("idx_cm_workspace_product_price", table_name="competitor_matches")
    op.drop_index("idx_cm_workspace_product", table_name="competitor_matches")
    op.drop_index("idx_pm_workspace_created", table_name="products_monitored")

    for table_name in reversed(WORKSPACE_SCOPED_TABLES):
        op.drop_constraint(
            f"fk_{table_name}_workspace_id_workspaces",
            table_name,
            type_="foreignkey",
        )
        op.drop_column(table_name, "workspace_id")

    op.drop_index("idx_users_default_workspace", table_name="users")
    op.drop_constraint(
        "fk_users_default_workspace_id_workspaces",
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "default_workspace_id")
