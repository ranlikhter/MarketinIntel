"""Create enterprise state and ops tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _require_postgresql() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Migration 0012_create_state_and_ops_tables requires PostgreSQL.")


def upgrade() -> None:
    _require_postgresql()

    op.execute("CREATE SCHEMA IF NOT EXISTS ops")
    op.execute("CREATE SCHEMA IF NOT EXISTS state")

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("products_scanned", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("listings_scanned", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("listings_changed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_summary", sa.Text(), nullable=True),
        schema="ops",
    )
    op.create_index(
        "idx_scrape_runs_workspace_started",
        "scrape_runs",
        ["workspace_id", "started_at"],
        unique=False,
        schema="ops",
    )
    op.create_index(
        "idx_scrape_runs_workspace_status_started",
        "scrape_runs",
        ["workspace_id", "status", "started_at"],
        unique=False,
        schema="ops",
    )

    op.create_table(
        "product_state_current",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products_monitored.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("competitor_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("in_stock_competitor_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("lowest_competitor_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("highest_competitor_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("avg_competitor_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("cheapest_match_id", sa.Integer(), sa.ForeignKey("competitor_matches.id"), nullable=True),
        sa.Column("most_expensive_match_id", sa.Integer(), sa.ForeignKey("competitor_matches.id"), nullable=True),
        sa.Column("latest_competitor_change_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_scrape_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amazon_1p_present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="state",
    )
    op.create_index(
        "idx_psc_workspace_updated",
        "product_state_current",
        ["workspace_id", "updated_at"],
        unique=False,
        schema="state",
    )
    op.create_index(
        "idx_psc_workspace_lowest_price",
        "product_state_current",
        ["workspace_id", "lowest_competitor_price"],
        unique=False,
        schema="state",
    )
    op.create_index(
        "idx_psc_workspace_latest_scrape",
        "product_state_current",
        ["workspace_id", "latest_scrape_at"],
        unique=False,
        schema="state",
    )
    op.execute(
        """
        CREATE INDEX idx_psc_workspace_amazon_1p
        ON state.product_state_current (workspace_id, amazon_1p_present)
        WHERE amazon_1p_present = true
        """
    )

    op.create_table(
        "competitor_listing_state_current",
        sa.Column("competitor_match_id", sa.Integer(), sa.ForeignKey("competitor_matches.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products_monitored.id", ondelete="CASCADE"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("stock_status", sa.String(length=50), nullable=True),
        sa.Column("seller_name", sa.String(length=200), nullable=True),
        sa.Column("amazon_is_seller", sa.Boolean(), nullable=True),
        sa.Column("seller_feedback_count", sa.Integer(), nullable=True),
        sa.Column("seller_positive_feedback_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("questions_count", sa.Integer(), nullable=True),
        sa.Column("listing_quality_score", sa.Integer(), nullable=True),
        sa.Column("fulfillment_type", sa.String(length=20), nullable=True),
        sa.Column("is_prime", sa.Boolean(), nullable=True),
        sa.Column("delivery_fastest_days", sa.Integer(), nullable=True),
        sa.Column("delivery_standard_days", sa.Integer(), nullable=True),
        sa.Column("has_same_day", sa.Boolean(), nullable=True),
        sa.Column("has_free_returns", sa.Boolean(), nullable=True),
        sa.Column("lowest_new_offer_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="state",
    )
    op.create_index(
        "idx_clsc_workspace_product_price",
        "competitor_listing_state_current",
        ["workspace_id", "product_id", "latest_price"],
        unique=False,
        schema="state",
    )
    op.create_index(
        "idx_clsc_workspace_seller",
        "competitor_listing_state_current",
        ["workspace_id", "seller_name"],
        unique=False,
        schema="state",
    )
    op.create_index(
        "idx_clsc_workspace_observed",
        "competitor_listing_state_current",
        ["workspace_id", "observed_at"],
        unique=False,
        schema="state",
    )
    op.execute(
        """
        CREATE INDEX idx_clsc_workspace_amazon_1p
        ON state.competitor_listing_state_current (workspace_id, amazon_is_seller)
        WHERE amazon_is_seller = true
        """
    )

    op.create_table(
        "seller_state_current",
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("seller_name_normalized", sa.Text(), nullable=False),
        sa.Column("seller_name", sa.Text(), nullable=False),
        sa.Column("storefront_url", sa.Text(), nullable=True),
        sa.Column("amazon_is_1p", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("feedback_rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("feedback_count", sa.Integer(), nullable=True),
        sa.Column("positive_feedback_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("active_listing_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("product_coverage_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("workspace_id", "seller_name_normalized"),
        schema="state",
    )
    op.create_index(
        "idx_ssc_workspace_coverage_desc",
        "seller_state_current",
        ["workspace_id", "product_coverage_count"],
        unique=False,
        schema="state",
    )
    op.execute(
        """
        CREATE INDEX idx_ssc_workspace_amazon_1p
        ON state.seller_state_current (workspace_id, amazon_is_1p)
        WHERE amazon_is_1p = true
        """
    )


def downgrade() -> None:
    _require_postgresql()

    op.drop_index("idx_ssc_workspace_coverage_desc", table_name="seller_state_current", schema="state")
    op.execute("DROP INDEX IF EXISTS state.idx_ssc_workspace_amazon_1p")
    op.drop_table("seller_state_current", schema="state")

    op.drop_index("idx_clsc_workspace_product_price", table_name="competitor_listing_state_current", schema="state")
    op.drop_index("idx_clsc_workspace_seller", table_name="competitor_listing_state_current", schema="state")
    op.drop_index("idx_clsc_workspace_observed", table_name="competitor_listing_state_current", schema="state")
    op.execute("DROP INDEX IF EXISTS state.idx_clsc_workspace_amazon_1p")
    op.drop_table("competitor_listing_state_current", schema="state")

    op.drop_index("idx_psc_workspace_updated", table_name="product_state_current", schema="state")
    op.drop_index("idx_psc_workspace_lowest_price", table_name="product_state_current", schema="state")
    op.drop_index("idx_psc_workspace_latest_scrape", table_name="product_state_current", schema="state")
    op.execute("DROP INDEX IF EXISTS state.idx_psc_workspace_amazon_1p")
    op.drop_table("product_state_current", schema="state")

    op.drop_index("idx_scrape_runs_workspace_started", table_name="scrape_runs", schema="ops")
    op.drop_index("idx_scrape_runs_workspace_status_started", table_name="scrape_runs", schema="ops")
    op.drop_table("scrape_runs", schema="ops")

    op.execute("DROP SCHEMA IF EXISTS state CASCADE")
    op.execute("DROP SCHEMA IF EXISTS ops CASCADE")
