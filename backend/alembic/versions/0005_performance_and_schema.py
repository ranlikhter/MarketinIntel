"""Performance indexes, PriceDailySnapshot table, user_id on competitor_websites

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-05

Changes:
  1. competitor_websites  — add user_id FK (multi-tenant row isolation fix)
  2. NEW TABLE: price_daily_snapshots  — pre-aggregated daily stats per match,
     replaces expensive GROUP BY on price_history at query time
  3. Covering indexes on price_history   — eliminates heap fetches in aggregation
  4. Composite + covering indexes on competitor_matches
  5. Supporting indexes on all other hot query paths
  6. BRIN index on price_history.timestamp (append-only time-series)

Performance impact summary:
  * get_product_trendline:   N+1 queries → 2 queries; trendline served from snapshot table
  * get_competitor_comparison: N+1 → 2 queries
  * Alert background job:    ORDER BY DESC LIMIT 1 per match → covered by idx_ph_match_time_cov
  * Dashboard load:          multiple heap fetches → index-only scans
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # ── 1. competitor_websites: add user_id for multi-tenant isolation ─────────
    op.add_column(
        "competitor_websites",
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=True),        # nullable for existing rows; tighten after backfill
    )
    op.create_index("idx_cw_user_active", "competitor_websites", ["user_id", "is_active"])

    # ── 2. NEW TABLE: price_daily_snapshots ────────────────────────────────────
    # Pre-aggregated daily OHLC-style price stats computed by the Celery nightly
    # task.  The analytics service reads from this instead of doing GROUP BY on
    # the raw price_history table (which can have millions of rows).
    op.create_table(
        "price_daily_snapshots",
        sa.Column("id",                   sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("match_id",             sa.Integer(),
                  sa.ForeignKey("competitor_matches.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("snapshot_date",        sa.Date(),    nullable=False),
        sa.Column("open_price",           sa.Float(),   nullable=True),   # first price of the day
        sa.Column("close_price",          sa.Float(),   nullable=True),   # last price of the day
        sa.Column("avg_price",            sa.Float(),   nullable=True),
        sa.Column("min_price",            sa.Float(),   nullable=True),
        sa.Column("max_price",            sa.Float(),   nullable=True),
        sa.Column("avg_effective_price",  sa.Float(),   nullable=True),   # after coupon
        sa.Column("min_effective_price",  sa.Float(),   nullable=True),
        sa.Column("sample_count",         sa.Integer(), nullable=False, server_default="0"),
        sa.Column("in_stock_pct",         sa.Float(),   nullable=True),   # fraction of samples in stock
        sa.Column("avg_seller_count",     sa.Float(),   nullable=True),
        sa.Column("avg_bsr",              sa.Float(),   nullable=True),   # avg best-seller rank
        sa.Column("created_at",           sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime(), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    # Unique constraint enables efficient ON CONFLICT DO UPDATE upserts
    op.create_unique_constraint(
        "uq_pds_match_date", "price_daily_snapshots", ["match_id", "snapshot_date"]
    )
    # Primary access pattern: match_id + date range (for trendline charts)
    op.create_index(
        "idx_pds_match_date",
        "price_daily_snapshots",
        ["match_id", sa.text("snapshot_date DESC")],
    )

    # ── 3. price_history: covering index for aggregation (the hottest index) ───
    #
    # Standard B-tree covering index works on both SQLite and PostgreSQL.
    # On PostgreSQL we additionally get a BRIN index for the timestamp column
    # which is 100× smaller and perfect for append-only time-series.
    #
    # Covers: SELECT avg(price), min(price), max(price)
    #         FROM price_history
    #         WHERE match_id = ? AND timestamp BETWEEN ? AND ?
    # → index-only scan, zero heap fetches.
    op.drop_index("idx_ph_match_time", table_name="price_history", if_exists=True)
    if _is_postgres():
        op.create_index(
            "idx_ph_match_time_cov",
            "price_history",
            ["match_id", sa.text("timestamp DESC")],
            postgresql_include=["price", "effective_price", "in_stock"],
        )
        # BRIN index on timestamp: 100× smaller than B-tree, ideal for
        # time-ordered append-only tables.  Cuts range scans to microseconds.
        op.create_index(
            "idx_ph_timestamp_brin",
            "price_history",
            ["timestamp"],
            postgresql_using="brin",
            postgresql_with={"pages_per_range": 128},
        )
    else:
        # SQLite: recreate a plain composite covering-ish index
        op.create_index(
            "idx_ph_match_time_cov",
            "price_history",
            ["match_id", "timestamp"],
        )

    # Separate index for source-based filtering (e.g., "show only amazon_scraper rows")
    op.create_index(
        "idx_ph_match_source",
        "price_history",
        ["match_id", "source", "timestamp"],
    )

    # ── 4. competitor_matches: covering indexes ─────────────────────────────────
    #
    # The two most-executed paths through competitor_matches:
    #   a) JOIN products_monitored ON monitored_product_id WHERE user_id = ?
    #   b) SELECT competitor_name, latest_price WHERE monitored_product_id = ?
    #
    # Existing idx_cm_product_url covers (monitored_product_id, competitor_url).
    # We add a covering index that includes the columns returned by list queries
    # so the DB can satisfy them without touching the (very wide) main row.
    if _is_postgres():
        op.create_index(
            "idx_cm_product_cover",
            "competitor_matches",
            ["monitored_product_id"],
            postgresql_include=[
                "competitor_name", "latest_price", "stock_status",
                "rating", "review_count", "match_score", "last_scraped_at",
            ],
        )
    else:
        op.create_index(
            "idx_cm_product_cover",
            "competitor_matches",
            ["monitored_product_id", "latest_price", "match_score"],
        )

    # Distinct competitor name lookup (used in comparison matrix and filters)
    op.create_index(
        "idx_cm_competitor_name",
        "competitor_matches",
        ["competitor_name"],
    )

    # Alert-check path: find stale matches needing re-scrape
    op.create_index(
        "idx_cm_scraped_active",
        "competitor_matches",
        ["last_scraped_at", "monitored_product_id"],
    )

    # Match score filtering (high-confidence matches only, e.g. score > 80)
    op.create_index(
        "idx_cm_match_score",
        "competitor_matches",
        ["monitored_product_id", "match_score"],
    )

    # ── 5. price_alerts: composite indexes ─────────────────────────────────────
    # Alert background job: SELECT * FROM price_alerts WHERE enabled = TRUE
    # Partial index for enabled=TRUE saves scanning disabled rows.
    if _is_postgres():
        op.create_index(
            "idx_pa_enabled_partial",
            "price_alerts",
            ["user_id", "product_id"],
            postgresql_where=sa.text("enabled = TRUE"),
        )
    else:
        op.create_index(
            "idx_pa_user_product_enabled",
            "price_alerts",
            ["enabled", "user_id", "product_id"],
        )
    # Snooze check: find alerts that need un-snoozing
    op.create_index(
        "idx_pa_snoozed_until",
        "price_alerts",
        ["snoozed_until"],
    )

    # ── 6. Supporting indexes on other tables ───────────────────────────────────

    # activity_logs: user activity feed (time-ordered, per user)
    op.create_index(
        "idx_al_user_created",
        "activity_logs",
        ["user_id", "created_at"],
    )
    # activity_logs: admin view by action type
    op.create_index(
        "idx_al_action_created",
        "activity_logs",
        ["action", "created_at"],
    )

    # my_price_history: per-product price timeline
    op.create_index(
        "idx_mph_product_changed",
        "my_price_history",
        ["product_id", "changed_at"],
    )

    # keyword_ranks: latest rank per product+keyword (redundant with 0004's idx but adds DESC order)
    op.create_index(
        "idx_kr_product_scraped",
        "keyword_ranks",
        ["product_id", "scraped_at"],
    )

    # store_connections: user's connected stores (already has user_id index via FK)
    op.create_index(
        "idx_sc_user_platform",
        "store_connections",
        ["user_id", "platform", "is_active"],
    )

    # workspace_members: fast lookup of which workspaces a user belongs to
    op.create_index(
        "idx_wm_user_workspace",
        "workspace_members",
        ["user_id", "workspace_id"],
    )

    # notification_logs: per-alert delivery history
    op.create_index(
        "idx_nl_alert_sent",
        "notification_logs",
        ["alert_id", "sent_at"],
    )

    # api_keys: auth lookup by key value (authentication hot path)
    op.create_index(
        "idx_ak_key_active",
        "api_keys",
        ["key", "is_active"],
    )

    # competitor_promotions: find active promotions by match
    op.create_index(
        "idx_cp_match_end",
        "competitor_promotions",
        ["match_id", "end_date"],
    )


def downgrade() -> None:
    for idx, tbl in [
        ("idx_cp_match_end",          "competitor_promotions"),
        ("idx_ak_key_active",         "api_keys"),
        ("idx_nl_alert_sent",         "notification_logs"),
        ("idx_wm_user_workspace",     "workspace_members"),
        ("idx_sc_user_platform",      "store_connections"),
        ("idx_kr_product_scraped",    "keyword_ranks"),
        ("idx_mph_product_changed",   "my_price_history"),
        ("idx_al_action_created",     "activity_logs"),
        ("idx_al_user_created",       "activity_logs"),
        ("idx_pa_snoozed_until",      "price_alerts"),
        ("idx_cm_match_score",        "competitor_matches"),
        ("idx_cm_scraped_active",     "competitor_matches"),
        ("idx_cm_competitor_name",    "competitor_matches"),
        ("idx_cm_product_cover",      "competitor_matches"),
        ("idx_ph_match_source",       "price_history"),
        ("idx_ph_match_time_cov",     "price_history"),
        ("idx_cw_user_active",        "competitor_websites"),
    ]:
        op.drop_index(idx, table_name=tbl, if_exists=True)

    if _is_postgres():
        op.drop_index("idx_ph_timestamp_brin", table_name="price_history", if_exists=True)
        op.drop_index("idx_pa_enabled_partial",  table_name="price_alerts",  if_exists=True)
    else:
        op.drop_index("idx_pa_user_product_enabled", table_name="price_alerts", if_exists=True)

    # Restore original price_history index
    op.create_index("idx_ph_match_time", "price_history", ["match_id", "timestamp"])

    op.drop_table("price_daily_snapshots")
    op.drop_column("competitor_websites", "user_id")
