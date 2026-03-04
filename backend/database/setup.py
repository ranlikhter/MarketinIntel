"""
Database Setup Script

Run this script to create all database tables.

Usage:
    python backend/database/setup.py
"""

import sys
import os

# Add the backend directory to the Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base
from database.connection import engine
from sqlalchemy import text


def run_migrations():
    """
    Apply lightweight column migrations for existing databases.
    SQLAlchemy's create_all won't add columns to existing tables,
    so we handle new columns manually here.
    """
    migrations = [
        # v1
        "ALTER TABLE products_monitored ADD COLUMN my_price REAL",
        # v2
        "ALTER TABLE users ADD COLUMN notification_prefs TEXT",
        # v4 — match-rate identifiers + margin intelligence on products_monitored
        "ALTER TABLE products_monitored ADD COLUMN description TEXT",
        "ALTER TABLE products_monitored ADD COLUMN mpn TEXT",
        "ALTER TABLE products_monitored ADD COLUMN upc_ean TEXT",
        "ALTER TABLE products_monitored ADD COLUMN cost_price REAL",
        # v4 — match-rate identifiers on competitor_matches
        "ALTER TABLE competitor_matches ADD COLUMN brand TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN description TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN mpn TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN upc_ean TEXT",
        # v3 — rich competitor intelligence on competitor_matches
        "ALTER TABLE competitor_matches ADD COLUMN external_id TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN rating REAL",
        "ALTER TABLE competitor_matches ADD COLUMN review_count INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN is_prime INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN fulfillment_type TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN product_condition TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN seller_name TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN category TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN variant TEXT",
        # v3 — rich price snapshots on price_history
        "ALTER TABLE price_history ADD COLUMN was_price REAL",
        "ALTER TABLE price_history ADD COLUMN discount_pct REAL",
        "ALTER TABLE price_history ADD COLUMN shipping_cost REAL",
        "ALTER TABLE price_history ADD COLUMN total_price REAL",
        "ALTER TABLE price_history ADD COLUMN promotion_label TEXT",
        "ALTER TABLE price_history ADD COLUMN seller_name TEXT",
        "ALTER TABLE price_history ADD COLUMN seller_count INTEGER",
        "ALTER TABLE price_history ADD COLUMN is_buy_box_winner INTEGER",
        "ALTER TABLE price_history ADD COLUMN scrape_quality TEXT",
        # v5 — inventory quantity on monitored products
        "ALTER TABLE products_monitored ADD COLUMN inventory_quantity INTEGER",
        # v6 — created_at on competitor_matches (was missing, needed by insights/filters/alerts)
        "ALTER TABLE competitor_matches ADD COLUMN created_at TIMESTAMP",
        # v7 — seller_count on competitor_matches (was only in price_history, now also on match for latest-value access)
        "ALTER TABLE competitor_matches ADD COLUMN seller_count INTEGER",
        # v7 — intelligence snapshot columns on price_history (preserve historical trends, not just latest)
        "ALTER TABLE price_history ADD COLUMN rating REAL",
        "ALTER TABLE price_history ADD COLUMN review_count INTEGER",
        "ALTER TABLE price_history ADD COLUMN is_prime INTEGER",
        "ALTER TABLE price_history ADD COLUMN fulfillment_type TEXT",
        "ALTER TABLE price_history ADD COLUMN product_condition TEXT",
        # v8 — enriched product identifiers for better competitor discovery
        "ALTER TABLE products_monitored ADD COLUMN asin TEXT",
        "ALTER TABLE products_monitored ADD COLUMN model_number TEXT",
        "ALTER TABLE products_monitored ADD COLUMN keywords TEXT",
        "ALTER TABLE products_monitored ADD COLUMN category TEXT",
        # v8 — match diagnostics: record HOW each match was made and how confident
        "ALTER TABLE competitor_matches ADD COLUMN match_method TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN ai_match_score REAL",
        "ALTER TABLE competitor_matches ADD COLUMN title_similarity REAL",
        "ALTER TABLE competitor_matches ADD COLUMN brand_match INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN match_explanation TEXT",
        # v8 — track which scraper produced each price snapshot
        "ALTER TABLE price_history ADD COLUMN source TEXT",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[MIGRATION] Applied: {sql}")
            except Exception:
                # Column already exists or table doesn't exist yet — safe to ignore
                pass


def create_tables():
    """
    Creates all database tables defined in models.py
    """
    print("Creating database tables...")

    # This creates all tables that don't exist yet
    Base.metadata.create_all(bind=engine)

    # Apply any additive column migrations for existing tables
    run_migrations()

    print("[SUCCESS] Database tables created successfully!")
    print(f"[INFO] Database location: {engine.url}")

    # Print the tables that were created
    print("\n[INFO] Tables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")


if __name__ == "__main__":
    create_tables()
