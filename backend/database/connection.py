"""
Database Connection Setup

Supports SQLite (development) and PostgreSQL (production).
PostgreSQL connections use connection pooling tuned for a typical web workload.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/products.db")

_is_sqlite = "sqlite" in DATABASE_URL

if _is_sqlite:
    # SQLite — minimal config, development only
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL (or other RDBMS) — production-grade pool settings
    _db_ssl_mode = os.getenv("DB_SSL_MODE", "prefer")

    engine = create_engine(
        DATABASE_URL,
        # Pool sizing: 20 base + 10 burst = 30 max simultaneous connections.
        # Tune to (max_connections / num_workers) for your deployment.
        pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
        max_overflow=int(os.getenv("DB_POOL_MAX_OVERFLOW", "10")),
        # Recycle connections hourly to avoid hitting server-side idle timeouts.
        pool_recycle=3600,
        # Verify connections are alive before using (avoids stale connection errors).
        pool_pre_ping=True,
        # Wait up to 30 s for a connection before raising a timeout error.
        pool_timeout=30,
        echo=False,  # Never True in production — logs every SQL statement
        connect_args={
            "sslmode": _db_ssl_mode,   # set DB_SSL_MODE=require in production
            "connect_timeout": 10,
            "application_name": "marketintel-api",
        },
    )

    # Enforce a per-statement timeout to prevent runaway queries from blocking
    # connection slots for extended periods.
    _STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))

    @event.listens_for(engine, "connect")
    def _set_statement_timeout(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET statement_timeout = {_STATEMENT_TIMEOUT_MS}")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session.

    The session is always closed when the request completes (even on error).

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
