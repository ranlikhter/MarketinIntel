"""
Backfill enterprise state and analytics tables from the legacy schema.

Usage:
    python backend/scripts/backfill_enterprise_rollups.py

Requires:
    DATABASE_URL to point to the PostgreSQL cutover database
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.connection import SessionLocal
from database.models import ProductMonitored
from services.enterprise_rollup_service import (
    enterprise_rollups_ready,
    refresh_workspace_product_rollups,
)


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if "postgresql" not in database_url:
        raise RuntimeError("DATABASE_URL must point to the PostgreSQL cutover database")

    db = SessionLocal()
    try:
        if not enterprise_rollups_ready(db):
            raise RuntimeError(
                "Enterprise rollup tables are not available yet. Run Alembic through 0013 first."
            )

        workspace_ids = [
            workspace_id
            for (workspace_id,) in db.query(ProductMonitored.workspace_id)
            .filter(ProductMonitored.workspace_id.is_not(None))
            .distinct()
            .all()
        ]

        total_products = 0
        for workspace_id in workspace_ids:
            product_count = db.query(ProductMonitored.id).filter(
                ProductMonitored.workspace_id == workspace_id
            ).count()
            refresh_workspace_product_rollups(db, workspace_id=workspace_id)
            total_products += product_count
            db.commit()
            print(f"[ROLLUP] workspace {workspace_id}: refreshed {product_count} product(s)")

        print(
            f"[DONE] Refreshed enterprise projections for {len(workspace_ids)} workspace(s) "
            f"and {total_products} product(s)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
