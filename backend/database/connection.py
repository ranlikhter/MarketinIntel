"""
Database Connection Setup

This file handles the connection to our SQLite database.
SQLite is a simple file-based database - perfect for getting started!
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment (defaults to local SQLite file)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/products.db")

# Create the database engine
# check_same_thread=False is needed for SQLite to work with FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # Set to True to see SQL queries in console (useful for debugging)
)

# Create a session factory
# Sessions are how we interact with the database (like opening a connection)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function that provides a database session.

    This is used by FastAPI to automatically provide a database connection
    to our API endpoints. The session is automatically closed after use.

    Usage:
        @app.get("/products")
        def get_products(db: Session = Depends(get_db)):
            return db.query(Product).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
