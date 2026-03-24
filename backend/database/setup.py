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
from database.secure_types import encrypt_existing_sensitive_values
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
        "ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN auth_provider_subject TEXT",
        "ALTER TABLE users ADD COLUMN avatar_url TEXT",
        "ALTER TABLE users ADD COLUMN password_login_enabled INTEGER DEFAULT 1",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_auth_provider_subject ON users(auth_provider_subject)",
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
        # v9 — Tier 1: effective pricing on competitor_matches
        "ALTER TABLE competitor_matches ADD COLUMN subscribe_save_price REAL",
        "ALTER TABLE competitor_matches ADD COLUMN coupon_value REAL",
        "ALTER TABLE competitor_matches ADD COLUMN coupon_pct REAL",
        "ALTER TABLE competitor_matches ADD COLUMN effective_price REAL",
        "ALTER TABLE competitor_matches ADD COLUMN is_lightning_deal INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN deal_end_time TIMESTAMP",
        "ALTER TABLE competitor_matches ADD COLUMN stock_quantity INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN low_stock_warning INTEGER",
        # v9 — Tier 1: market position on competitor_matches
        "ALTER TABLE competitor_matches ADD COLUMN best_seller_rank INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN best_seller_rank_category TEXT",
        # v9 — Tier 2: demand & visibility on competitor_matches
        "ALTER TABLE competitor_matches ADD COLUMN units_sold_past_month INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN badge_amazons_choice INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN badge_best_seller INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN badge_new_release INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN is_sponsored INTEGER",
        "ALTER TABLE competitor_matches ADD COLUMN rating_distribution TEXT",
        # v9 — Tier 3: product attributes on competitor_matches
        "ALTER TABLE competitor_matches ADD COLUMN specifications TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN variant_options TEXT",
        "ALTER TABLE competitor_matches ADD COLUMN date_first_available TEXT",
        # v9 — volatile pricing & demand snapshot on price_history
        "ALTER TABLE price_history ADD COLUMN subscribe_save_price REAL",
        "ALTER TABLE price_history ADD COLUMN coupon_value REAL",
        "ALTER TABLE price_history ADD COLUMN coupon_pct REAL",
        "ALTER TABLE price_history ADD COLUMN effective_price REAL",
        "ALTER TABLE price_history ADD COLUMN is_lightning_deal INTEGER",
        "ALTER TABLE price_history ADD COLUMN deal_end_time TIMESTAMP",
        "ALTER TABLE price_history ADD COLUMN stock_quantity INTEGER",
        "ALTER TABLE price_history ADD COLUMN units_sold_past_month INTEGER",
        "ALTER TABLE price_history ADD COLUMN best_seller_rank INTEGER",
        "ALTER TABLE price_history ADD COLUMN badge_amazons_choice INTEGER",
        "ALTER TABLE price_history ADD COLUMN badge_best_seller INTEGER",
        "ALTER TABLE price_history ADD COLUMN is_sponsored INTEGER",
        # v11 — notification delivery log
        """CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER REFERENCES price_alerts(id) ON DELETE SET NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_nl_alert ON notification_logs(alert_id)",
        "CREATE INDEX IF NOT EXISTS idx_nl_user_sent ON notification_logs(user_id, sent_at DESC)",
        # v10 — composite indexes (biggest query performance win: eliminates full-table scans)
        "CREATE INDEX IF NOT EXISTS idx_cm_product_url ON competitor_matches(monitored_product_id, competitor_url)",
        "CREATE INDEX IF NOT EXISTS idx_cm_product_price ON competitor_matches(monitored_product_id, latest_price)",
        "CREATE INDEX IF NOT EXISTS idx_cm_last_scraped ON competitor_matches(last_scraped_at)",
        "CREATE INDEX IF NOT EXISTS idx_ph_match_time ON price_history(match_id, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_pa_product_enabled ON price_alerts(product_id, enabled)",
        # price_alerts: dashboards and scanners frequently filter enabled alerts per user
        "CREATE INDEX IF NOT EXISTS idx_pa_user_enabled ON price_alerts(user_id, enabled)",
        # products_monitored: user owns many products; user_id queries are extremely common
        "CREATE INDEX IF NOT EXISTS idx_pm_user_created ON products_monitored(user_id, created_at DESC)",
        # my_price_history: product detail pages always load price changes per product in time order
        "CREATE INDEX IF NOT EXISTS idx_mph_product_changed ON my_price_history(product_id, changed_at)",
    ]
    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"[MIGRATION] Applied: {sql}")
                except Exception:
                    conn.rollback()
        else:
            print("[MIGRATION] Skipping legacy additive SQL migrations on non-SQLite database")

        encrypted_rows = encrypt_existing_sensitive_values(conn)
        if encrypted_rows:
            conn.commit()
            print(f"[MIGRATION] Encrypted legacy sensitive rows: {encrypted_rows}")


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
