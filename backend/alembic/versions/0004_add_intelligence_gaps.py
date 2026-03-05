"""Add intelligence gap fields: seller intel, listing quality, delivery, variations, new tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-05

Changes:
  competitor_matches  — 22 new columns (seller intel, listing quality, delivery, variation, badges)
  price_history       — 4 new snapshot columns
  NEW: review_snapshots, seller_profiles, listing_quality_snapshots, keyword_ranks tables
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── competitor_matches: Seller Intelligence ─────────────────────────────
    op.add_column("competitor_matches", sa.Column("amazon_is_seller",            sa.Boolean(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("seller_feedback_count",       sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("seller_positive_feedback_pct",sa.Float(),       nullable=True))
    op.add_column("competitor_matches", sa.Column("lowest_new_offer_price",      sa.Float(),       nullable=True))
    op.add_column("competitor_matches", sa.Column("number_of_used_offers",       sa.Integer(),     nullable=True))

    # ── competitor_matches: Listing Quality ─────────────────────────────────
    op.add_column("competitor_matches", sa.Column("image_count",           sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("has_video",             sa.Boolean(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("has_aplus_content",     sa.Boolean(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("has_brand_story",       sa.Boolean(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("bullet_point_count",    sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("title_char_count",      sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("questions_count",       sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("listing_quality_score", sa.Integer(),     nullable=True))

    # ── competitor_matches: Delivery & Fulfillment ──────────────────────────
    op.add_column("competitor_matches", sa.Column("delivery_fastest_days",  sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("delivery_standard_days", sa.Integer(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("has_same_day",           sa.Boolean(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("ships_from_location",    sa.String(100),   nullable=True))
    op.add_column("competitor_matches", sa.Column("has_free_returns",       sa.Boolean(),     nullable=True))
    op.add_column("competitor_matches", sa.Column("return_window_days",     sa.Integer(),     nullable=True))

    # ── competitor_matches: Variation Intelligence ──────────────────────────
    op.add_column("competitor_matches", sa.Column("parent_asin",                 sa.String(20),  nullable=True))
    op.add_column("competitor_matches", sa.Column("total_variations",            sa.Integer(),   nullable=True))
    op.add_column("competitor_matches", sa.Column("is_best_seller_variation",    sa.Boolean(),   nullable=True))

    # ── competitor_matches: Extended Badges ─────────────────────────────────
    op.add_column("competitor_matches", sa.Column("climate_pledge_friendly", sa.Boolean(), nullable=True))
    op.add_column("competitor_matches", sa.Column("small_business_badge",    sa.Boolean(), nullable=True))

    # ── price_history: new snapshot columns ─────────────────────────────────
    op.add_column("price_history", sa.Column("amazon_is_seller",      sa.Boolean(),     nullable=True))
    op.add_column("price_history", sa.Column("seller_name_snapshot",  sa.String(200),   nullable=True))
    op.add_column("price_history", sa.Column("delivery_fastest_days", sa.Integer(),     nullable=True))
    op.add_column("price_history", sa.Column("has_free_returns",      sa.Boolean(),     nullable=True))

    # ── NEW TABLE: review_snapshots ─────────────────────────────────────────
    op.create_table(
        "review_snapshots",
        sa.Column("id",               sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("match_id",         sa.Integer(),  sa.ForeignKey("competitor_matches.id"), nullable=False),
        sa.Column("review_count",     sa.Integer(),  nullable=True),
        sa.Column("rating",           sa.Float(),    nullable=True),
        sa.Column("rating_distribution", sa.JSON(), nullable=True),
        sa.Column("questions_count",  sa.Integer(),  nullable=True),
        sa.Column("scraped_at",       sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_rs_match_time", "review_snapshots", ["match_id", "scraped_at"])

    # ── NEW TABLE: seller_profiles ──────────────────────────────────────────
    op.create_table(
        "seller_profiles",
        sa.Column("id",                      sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("seller_name",             sa.String(200),   nullable=False, unique=True),
        sa.Column("amazon_is_1p",            sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("feedback_rating",         sa.Float(),       nullable=True),
        sa.Column("feedback_count",          sa.Integer(),     nullable=True),
        sa.Column("positive_feedback_pct",   sa.Float(),       nullable=True),
        sa.Column("storefront_url",          sa.Text(),        nullable=True),
        sa.Column("first_seen_at",           sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.Column("last_updated_at",         sa.DateTime(),    nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_sp_seller_name", "seller_profiles", ["seller_name"])

    # ── NEW TABLE: listing_quality_snapshots ────────────────────────────────
    op.create_table(
        "listing_quality_snapshots",
        sa.Column("id",                  sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("match_id",            sa.Integer(),  sa.ForeignKey("competitor_matches.id"), nullable=False),
        sa.Column("image_count",         sa.Integer(),  nullable=True),
        sa.Column("has_video",           sa.Boolean(),  nullable=True),
        sa.Column("has_aplus_content",   sa.Boolean(),  nullable=True),
        sa.Column("has_brand_story",     sa.Boolean(),  nullable=True),
        sa.Column("bullet_point_count",  sa.Integer(),  nullable=True),
        sa.Column("title_char_count",    sa.Integer(),  nullable=True),
        sa.Column("questions_count",     sa.Integer(),  nullable=True),
        sa.Column("listing_score",       sa.Integer(),  nullable=True),
        sa.Column("scraped_at",          sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_lqs_match_time", "listing_quality_snapshots", ["match_id", "scraped_at"])

    # ── NEW TABLE: keyword_ranks ────────────────────────────────────────────
    op.create_table(
        "keyword_ranks",
        sa.Column("id",             sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("product_id",     sa.Integer(),     sa.ForeignKey("products_monitored.id"), nullable=False),
        sa.Column("keyword",        sa.String(300),   nullable=False),
        sa.Column("organic_rank",   sa.Integer(),     nullable=True),
        sa.Column("sponsored_rank", sa.Integer(),     nullable=True),
        sa.Column("total_results",  sa.Integer(),     nullable=True),
        sa.Column("scraped_at",     sa.DateTime(),    nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_kr_product_keyword_time", "keyword_ranks", ["product_id", "keyword", "scraped_at"])


def downgrade() -> None:
    # Drop new tables
    op.drop_table("keyword_ranks")
    op.drop_table("listing_quality_snapshots")
    op.drop_table("seller_profiles")
    op.drop_table("review_snapshots")

    # Drop new price_history columns
    for col in ["has_free_returns", "delivery_fastest_days", "seller_name_snapshot", "amazon_is_seller"]:
        op.drop_column("price_history", col)

    # Drop new competitor_matches columns
    for col in [
        "small_business_badge", "climate_pledge_friendly",
        "is_best_seller_variation", "total_variations", "parent_asin",
        "return_window_days", "has_free_returns", "ships_from_location",
        "has_same_day", "delivery_standard_days", "delivery_fastest_days",
        "listing_quality_score", "questions_count", "title_char_count",
        "bullet_point_count", "has_brand_story", "has_aplus_content",
        "has_video", "image_count",
        "number_of_used_offers", "lowest_new_offer_price",
        "seller_positive_feedback_pct", "seller_feedback_count", "amazon_is_seller",
    ]:
        op.drop_column("competitor_matches", col)
