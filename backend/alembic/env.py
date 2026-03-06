"""
Alembic environment configuration.

Uses the existing SQLAlchemy models so `alembic revision --autogenerate`
can detect schema differences automatically.

Usage:
    # Apply all pending migrations
    alembic upgrade head

    # Roll back the last migration
    alembic downgrade -1

    # Generate a new migration from model changes
    alembic revision --autogenerate -m "add some_column to some_table"
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make the backend package importable from this file's location
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base  # noqa: E402 — must come after sys.path update

# Alembic Config object (gives access to values in alembic.ini)
config = context.config

# Interpret logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the DATABASE_URL env var if set; otherwise fall back to alembic.ini value
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# The MetaData object from our models — drives autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Render column types properly for SQLite
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
