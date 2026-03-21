"""Create enterprise analytics tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _require_postgresql() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Migration 0013_create_analytics_tables requires PostgreSQL.")


def upgrade() -> None:
    _require_postgresql()

    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.create_table(
        "product_metrics_current",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products_monitored.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("competitor_count", sa.Integer(), nullable=False),
        sa.Column("in_stock_competitor_count", sa.Integer(), nullable=False),
        sa.Column("lowest_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("highest_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("avg_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_gap_vs_mine", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_gap_pct_vs_mine", sa.Numeric(5, 2), nullable=True),
        sa.Column("review_velocity_7d", sa.Integer(), nullable=True),
        sa.Column("review_velocity_30d", sa.Integer(), nullable=True),
        sa.Column("rating_drop_30d", sa.Numeric(5, 2), nullable=True),
        sa.Column("buy_box_volatility_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("seller_diversity_count", sa.Integer(), nullable=True),
        sa.Column("amazon_1p_present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active_alert_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("threat_score", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("priority_bucket", sa.String(length=16), nullable=False, server_default=sa.text("'low'")),
        schema="analytics",
    )
    op.create_index(
        "idx_pmc_workspace_threat_desc",
        "product_metrics_current",
        ["workspace_id", "threat_score"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "idx_pmc_workspace_priority_threat",
        "product_metrics_current",
        ["workspace_id", "priority_bucket", "threat_score"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "idx_pmc_workspace_review_velocity",
        "product_metrics_current",
        ["workspace_id", "review_velocity_7d"],
        unique=False,
        schema="analytics",
    )

    op.create_table(
        "product_metrics_daily",
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products_monitored.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("competitor_count", sa.Integer(), nullable=False),
        sa.Column("lowest_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("avg_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("review_velocity_7d", sa.Integer(), nullable=True),
        sa.Column("buy_box_volatility_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("threat_score", sa.Numeric(5, 2), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", "product_id", "metric_date"),
        schema="analytics",
    )
    op.create_index(
        "idx_pmd_workspace_metric_date",
        "product_metrics_daily",
        ["workspace_id", "metric_date"],
        unique=False,
        schema="analytics",
    )

    op.create_table(
        "portfolio_metrics_current",
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("total_products", sa.Integer(), nullable=False),
        sa.Column("total_active_listings", sa.Integer(), nullable=False),
        sa.Column("total_active_alerts", sa.Integer(), nullable=False),
        sa.Column("products_with_threats", sa.Integer(), nullable=False),
        sa.Column("products_with_surging_reviews", sa.Integer(), nullable=False),
        sa.Column("products_with_price_drops", sa.Integer(), nullable=False),
        sa.Column("average_competitor_count", sa.Numeric(8, 2), nullable=True),
        sa.Column("average_price_gap_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("data_freshness_seconds", sa.Integer(), nullable=False),
        schema="analytics",
    )

    op.create_table(
        "seller_metrics_current",
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("seller_name_normalized", sa.Text(), nullable=False),
        sa.Column("seller_name", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("product_coverage_count", sa.Integer(), nullable=False),
        sa.Column("active_listing_count", sa.Integer(), nullable=False),
        sa.Column("avg_price_position", sa.Numeric(8, 2), nullable=True),
        sa.Column("avg_rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("buy_box_win_rate_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("volatility_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("amazon_is_1p", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("workspace_id", "seller_name_normalized"),
        schema="analytics",
    )
    op.create_index(
        "idx_smc_workspace_coverage_desc",
        "seller_metrics_current",
        ["workspace_id", "product_coverage_count"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "idx_smc_workspace_volatility_desc",
        "seller_metrics_current",
        ["workspace_id", "volatility_score"],
        unique=False,
        schema="analytics",
    )


def downgrade() -> None:
    _require_postgresql()

    op.drop_index("idx_smc_workspace_coverage_desc", table_name="seller_metrics_current", schema="analytics")
    op.drop_index("idx_smc_workspace_volatility_desc", table_name="seller_metrics_current", schema="analytics")
    op.drop_table("seller_metrics_current", schema="analytics")

    op.drop_table("portfolio_metrics_current", schema="analytics")

    op.drop_index("idx_pmd_workspace_metric_date", table_name="product_metrics_daily", schema="analytics")
    op.drop_table("product_metrics_daily", schema="analytics")

    op.drop_index("idx_pmc_workspace_threat_desc", table_name="product_metrics_current", schema="analytics")
    op.drop_index("idx_pmc_workspace_priority_threat", table_name="product_metrics_current", schema="analytics")
    op.drop_index("idx_pmc_workspace_review_velocity", table_name="product_metrics_current", schema="analytics")
    op.drop_table("product_metrics_current", schema="analytics")

    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
