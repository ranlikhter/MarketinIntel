"""
Copy legacy SQLite data into the PostgreSQL cutover database.

Usage:
    python backend/scripts/sqlite_to_postgres.py

Environment variables:
    SQLITE_DATABASE_URL    optional, defaults to sqlite:///./marketintel.db
    DATABASE_URL           required PostgreSQL target URL
"""

from __future__ import annotations

import os
import sqlite3
import json
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Json
from sqlalchemy.engine import make_url


TABLE_ORDER = [
    "users",
    "workspaces",
    "workspace_members",
    "competitor_websites",
    "products_monitored",
    "competitor_matches",
    "price_history",
    "review_snapshots",
    "listing_quality_snapshots",
    "keyword_ranks",
    "price_alerts",
    "my_price_history",
    "competitor_promotions",
    "saved_views",
    "repricing_rules",
    "api_keys",
    "store_connections",
    "activity_logs",
    "push_subscriptions",
    "notification_logs",
]


def _sqlite_path_from_url(url: str) -> Path:
    if not url.startswith("sqlite:///"):
        raise RuntimeError("SQLITE_DATABASE_URL must use sqlite:/// path format")
    return Path(url.replace("sqlite:///", "", 1)).resolve()


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    return [row[1] for row in cursor.fetchall()]


def _sync_sequence(pg_cursor: psycopg.Cursor, table_name: str) -> None:
    pg_cursor.execute(
        sql.SQL(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = 'id'
            """
        ),
        (table_name,),
    )
    if pg_cursor.fetchone() is None:
        return

    pg_cursor.execute(
        sql.SQL(
            """
            SELECT setval(
                pg_get_serial_sequence(%s, 'id'),
                COALESCE((SELECT MAX(id) FROM {}), 1),
                (SELECT COUNT(*) > 0 FROM {})
            )
            """
        ).format(sql.Identifier(table_name), sql.Identifier(table_name)),
        (table_name,),
    )


def _postgres_column_types(pg_cursor: psycopg.Cursor, table_name: str) -> dict[str, str]:
    pg_cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return {row[0]: row[1] for row in pg_cursor.fetchall()}


def _normalize_value(value, data_type: str):
    if value is None:
        return None

    if data_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "t", "yes", "y"}:
                return True
            if lowered in {"0", "false", "f", "no", "n"}:
                return False
        return value

    if data_type in {"json", "jsonb"}:
        if isinstance(value, (dict, list)):
            return Json(value)
        if isinstance(value, str):
            try:
                return Json(json.loads(value))
            except json.JSONDecodeError:
                return Json(value)
        return Json(value)

    return value


def main() -> None:
    sqlite_url = os.getenv("SQLITE_DATABASE_URL", "sqlite:///./marketintel.db")
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url:
        raise RuntimeError("DATABASE_URL must point to the PostgreSQL cutover database")
    if "postgresql" not in postgres_url:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL for this script")

    sqlite_path = _sqlite_path_from_url(sqlite_url)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_url = make_url(postgres_url)
    with psycopg.connect(
        host=pg_url.host,
        port=pg_url.port,
        dbname=pg_url.database,
        user=pg_url.username,
        password=pg_url.password,
    ) as pg_conn:
        with pg_conn.cursor() as pg_cur:
            for table_name in TABLE_ORDER:
                sqlite_cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                    (table_name,),
                )
                if sqlite_cur.fetchone() is None:
                    print(f"[SKIP] {table_name}: not present in SQLite source")
                    continue

                columns = _table_columns(sqlite_cur, table_name)
                if not columns:
                    print(f"[SKIP] {table_name}: no columns discovered")
                    continue

                target_column_types = _postgres_column_types(pg_cur, table_name)
                columns = [column for column in columns if column in target_column_types]
                if not columns:
                    print(f"[SKIP] {table_name}: no overlapping target columns")
                    continue

                select_columns = ", ".join(f'"{column}"' for column in columns)
                select_sql = f'SELECT {select_columns} FROM "{table_name}"'
                sqlite_cur.execute(select_sql)
                rows = sqlite_cur.fetchall()

                if not rows:
                    print(f"[COPY] {table_name}: 0 rows")
                    continue

                insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                    sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                )
                values = [
                    tuple(
                        _normalize_value(row[column], target_column_types[column])
                        for column in columns
                    )
                    for row in rows
                ]
                pg_cur.executemany(insert_sql, values)
                _sync_sequence(pg_cur, table_name)
                print(f"[COPY] {table_name}: {len(values)} rows")

        pg_conn.commit()

    sqlite_conn.close()
    print("[DONE] SQLite to PostgreSQL copy completed")


if __name__ == "__main__":
    main()
