"""Enforce workspace ownership constraints for enterprise tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NOT_NULL_TABLES: tuple[str, ...] = (
    "products_monitored",
    "competitor_matches",
    "price_history",
    "review_snapshots",
    "listing_quality_snapshots",
    "keyword_ranks",
    "competitor_promotions",
    "my_price_history",
    "price_alerts",
    "saved_views",
    "repricing_rules",
    "api_keys",
    "store_connections",
    "activity_logs",
    "notification_logs",
    "push_subscriptions",
)


def _require_postgresql() -> sa.engine.Connection:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError(
            "Migration 0010_enforce_workspace_scope_constraints requires PostgreSQL. "
            "Run it after the PostgreSQL cutover, not on the legacy SQLite database."
        )
    return bind


def _assert_no_nulls(bind: sa.engine.Connection, table_name: str, column_name: str) -> None:
    count = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL")
    ).scalar_one()
    if count:
        raise RuntimeError(
            f"Cannot enforce NOT NULL on {table_name}.{column_name}: found {count} null rows."
        )


def _assert_no_duplicate_groups(
    bind: sa.engine.Connection,
    table_name: str,
    columns: Sequence[str],
    where_sql: str | None = None,
) -> None:
    cols_sql = ", ".join(columns)
    where_clause = f"WHERE {where_sql}" if where_sql else ""
    count_sql = (
        f"SELECT COUNT(*) FROM ("
        f"SELECT {cols_sql} FROM {table_name} {where_clause} "
        f"GROUP BY {cols_sql} HAVING COUNT(*) > 1"
        f") dup"
    )
    duplicate_groups = bind.execute(sa.text(count_sql)).scalar_one()
    if duplicate_groups:
        sample_sql = (
            f"SELECT {cols_sql}, COUNT(*) AS row_count FROM {table_name} {where_clause} "
            f"GROUP BY {cols_sql} HAVING COUNT(*) > 1 "
            f"ORDER BY row_count DESC LIMIT 3"
        )
        sample_rows = bind.execute(sa.text(sample_sql)).mappings().all()
        raise RuntimeError(
            f"Cannot create unique constraint on {table_name}({cols_sql}): "
            f"found {duplicate_groups} duplicate groups. Sample rows: {sample_rows}"
        )


def upgrade() -> None:
    bind = _require_postgresql()

    _assert_no_nulls(bind, "users", "default_workspace_id")
    for table_name in NOT_NULL_TABLES:
        _assert_no_nulls(bind, table_name, "workspace_id")

    _assert_no_duplicate_groups(bind, "workspace_members", ("workspace_id", "user_id"))
    _assert_no_duplicate_groups(bind, "products_monitored", ("workspace_id", "sku"), "sku IS NOT NULL")
    _assert_no_duplicate_groups(bind, "products_monitored", ("workspace_id", "asin"), "asin IS NOT NULL")
    _assert_no_duplicate_groups(bind, "store_connections", ("workspace_id", "platform", "store_url"))
    _assert_no_duplicate_groups(bind, "saved_views", ("workspace_id", "user_id", "name"))

    op.alter_column("users", "default_workspace_id", existing_type=sa.Integer(), nullable=False)
    for table_name in NOT_NULL_TABLES:
        op.alter_column(table_name, "workspace_id", existing_type=sa.Integer(), nullable=False)

    op.create_index(
        "uq_workspace_members_workspace_user",
        "workspace_members",
        ["workspace_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "uq_products_workspace_sku",
        "products_monitored",
        ["workspace_id", "sku"],
        unique=True,
        postgresql_where=sa.text("sku IS NOT NULL"),
    )
    op.create_index(
        "uq_products_workspace_asin",
        "products_monitored",
        ["workspace_id", "asin"],
        unique=True,
        postgresql_where=sa.text("asin IS NOT NULL"),
    )
    op.create_index(
        "uq_store_connections_workspace_platform_url",
        "store_connections",
        ["workspace_id", "platform", "store_url"],
        unique=True,
    )
    op.create_index(
        "uq_saved_views_workspace_user_name",
        "saved_views",
        ["workspace_id", "user_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    _require_postgresql()

    op.drop_index("uq_saved_views_workspace_user_name", table_name="saved_views")
    op.drop_index("uq_store_connections_workspace_platform_url", table_name="store_connections")
    op.drop_index("uq_products_workspace_asin", table_name="products_monitored")
    op.drop_index("uq_products_workspace_sku", table_name="products_monitored")
    op.drop_index("uq_workspace_members_workspace_user", table_name="workspace_members")

    for table_name in reversed(NOT_NULL_TABLES):
        op.alter_column(table_name, "workspace_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("users", "default_workspace_id", existing_type=sa.Integer(), nullable=True)
