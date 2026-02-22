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
        "ALTER TABLE products_monitored ADD COLUMN my_price REAL",
        "ALTER TABLE users ADD COLUMN notification_prefs TEXT",
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
