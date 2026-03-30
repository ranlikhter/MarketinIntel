"""
0015 — Extended product fields (pricing controls, dimensions, lifecycle, variants, scraping)

Adds 23 new columns to products_monitored across 5 groups:

  Group 1 — Pricing controls:
    map_price, rrp_msrp, compare_at_price, min_price, max_price, target_margin_pct

  Group 2 — Dimensions / shipping:
    weight, weight_unit, length, width, height, dimension_unit

  Group 3 — Product lifecycle & catalog:
    status, currency, product_url, tags, notes, is_bundle, bundle_skus

  Group 4 — Variant tracking:
    parent_sku, variant_attributes

  Group 5 — Scraping control:
    scrape_frequency, scrape_priority, track_all_variants, match_threshold

Revision ID: 0015
Revises: 0014
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels = None
depends_on = None

# Columns grouped for clarity
_NEW_COLUMNS = [
    # Group 1 — Pricing controls
    sa.Column("map_price",          sa.Float,       nullable=True),
    sa.Column("rrp_msrp",           sa.Float,       nullable=True),
    sa.Column("compare_at_price",   sa.Float,       nullable=True),
    sa.Column("min_price",          sa.Float,       nullable=True),
    sa.Column("max_price",          sa.Float,       nullable=True),
    sa.Column("target_margin_pct",  sa.Float,       nullable=True),
    # Group 2 — Dimensions
    sa.Column("weight",             sa.Float,       nullable=True),
    sa.Column("weight_unit",        sa.String(10),  nullable=True, server_default="kg"),
    sa.Column("length",             sa.Float,       nullable=True),
    sa.Column("width",              sa.Float,       nullable=True),
    sa.Column("height",             sa.Float,       nullable=True),
    sa.Column("dimension_unit",     sa.String(5),   nullable=True, server_default="cm"),
    # Group 3 — Lifecycle / catalog
    sa.Column("status",             sa.String(20),  nullable=True, server_default="active"),
    sa.Column("currency",           sa.String(3),   nullable=True, server_default="USD"),
    sa.Column("product_url",        sa.Text,        nullable=True),
    sa.Column("tags",               sa.JSON,        nullable=True),
    sa.Column("notes",              sa.Text,        nullable=True),
    sa.Column("is_bundle",          sa.Boolean,     nullable=True, server_default="0"),
    sa.Column("bundle_skus",        sa.JSON,        nullable=True),
    # Group 4 — Variants
    sa.Column("parent_sku",         sa.String(100), nullable=True),
    sa.Column("variant_attributes", sa.JSON,        nullable=True),
    # Group 5 — Scraping control
    sa.Column("scrape_frequency",   sa.String(20),  nullable=True, server_default="daily"),
    sa.Column("scrape_priority",    sa.String(10),  nullable=True, server_default="medium"),
    sa.Column("track_all_variants", sa.Boolean,     nullable=True, server_default="0"),
    sa.Column("match_threshold",    sa.Float,       nullable=True, server_default="60.0"),
]


def upgrade() -> None:
    for col in _NEW_COLUMNS:
        op.add_column("products_monitored", col)

    # Index for variant grouping (parent → children lookups)
    op.create_index("idx_pm_parent_sku",        "products_monitored", ["workspace_id", "parent_sku"])
    # Index for status-filtered queries (skip inactive/discontinued in scrape queue)
    op.create_index("idx_pm_status",            "products_monitored", ["workspace_id", "status"])
    # Index for priority queue ordering
    op.create_index("idx_pm_scrape_priority",   "products_monitored", ["workspace_id", "scrape_priority", "scrape_frequency"])


def downgrade() -> None:
    op.drop_index("idx_pm_scrape_priority",   table_name="products_monitored")
    op.drop_index("idx_pm_status",            table_name="products_monitored")
    op.drop_index("idx_pm_parent_sku",        table_name="products_monitored")

    for col in reversed(_NEW_COLUMNS):
        op.drop_column("products_monitored", col.name)
