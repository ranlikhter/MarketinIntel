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


def create_tables():
    """
    Creates all database tables defined in models.py
    """
    print("Creating database tables...")

    # This creates all tables that don't exist yet
    Base.metadata.create_all(bind=engine)

    print("[SUCCESS] Database tables created successfully!")
    print(f"[INFO] Database location: {engine.url}")

    # Print the tables that were created
    print("\n[INFO] Tables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")


if __name__ == "__main__":
    create_tables()
