"""
Backfill workspace ownership after copying legacy SQLite data into PostgreSQL.

Usage:
    python backend/scripts/backfill_workspace_scope.py

Environment variables:
    DATABASE_URL    required PostgreSQL target URL
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text


def _require_postgres(database_url: str) -> None:
    if not database_url or "postgresql" not in database_url:
        raise RuntimeError("DATABASE_URL must point to the PostgreSQL cutover database")


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    _require_postgres(database_url)
    engine = create_engine(database_url)
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        users = conn.execute(
            text(
                """
                SELECT id, email, full_name, default_workspace_id
                FROM users
                ORDER BY id
                """
            )
        ).mappings().all()

        if not users:
            print("[DONE] No users found; workspace backfill skipped")
            return

        default_workspace_by_user: dict[int, int] = {}
        for user in users:
            user_id = int(user["id"])
            workspace_id = user["default_workspace_id"]

            if workspace_id is None:
                existing = conn.execute(
                    text(
                        """
                        SELECT id
                        FROM workspaces
                        WHERE owner_id = :user_id
                        ORDER BY is_active DESC, id ASC
                        LIMIT 1
                        """
                    ),
                    {"user_id": user_id},
                ).scalar()
                workspace_id = int(existing) if existing is not None else None

            if workspace_id is None:
                full_name = (user["full_name"] or "").strip() if user["full_name"] else ""
                email = (user["email"] or "").strip() if user["email"] else ""
                base = full_name or (email.split("@", 1)[0] if email else f"user-{user_id}")
                workspace_name = f"{base[:220]} Personal Workspace"[:255]
                workspace_id = conn.execute(
                    text(
                        """
                        INSERT INTO workspaces (name, owner_id, is_active, created_at, updated_at)
                        VALUES (:name, :owner_id, true, :created_at, :updated_at)
                        RETURNING id
                        """
                    ),
                    {
                        "name": workspace_name,
                        "owner_id": user_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                ).scalar_one()

            default_workspace_by_user[user_id] = int(workspace_id)
            conn.execute(
                text(
                    """
                    UPDATE users
                    SET default_workspace_id = :workspace_id
                    WHERE id = :user_id
                    """
                ),
                {"workspace_id": workspace_id, "user_id": user_id},
            )

        for user_id, workspace_id in default_workspace_by_user.items():
            membership_id = conn.execute(
                text(
                    """
                    SELECT id
                    FROM workspace_members
                    WHERE workspace_id = :workspace_id AND user_id = :user_id
                    """
                ),
                {"workspace_id": workspace_id, "user_id": user_id},
            ).scalar()

            if membership_id is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO workspace_members (
                            workspace_id, user_id, role, is_active, invited_at, joined_at
                        ) VALUES (
                            :workspace_id, :user_id, 'ADMIN', true, :invited_at, :joined_at
                        )
                        """
                    ),
                    {
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "invited_at": now,
                        "joined_at": now,
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        UPDATE workspace_members
                        SET role = 'ADMIN',
                            is_active = true,
                            joined_at = COALESCE(joined_at, :joined_at)
                        WHERE id = :membership_id
                        """
                    ),
                    {"membership_id": membership_id, "joined_at": now},
                )

        conn.execute(
            text(
                """
                UPDATE products_monitored AS p
                SET workspace_id = u.default_workspace_id
                FROM users AS u
                WHERE p.workspace_id IS NULL
                  AND p.user_id = u.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE competitor_matches AS m
                SET workspace_id = p.workspace_id
                FROM products_monitored AS p
                WHERE m.workspace_id IS NULL
                  AND m.monitored_product_id = p.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE price_history AS ph
                SET workspace_id = m.workspace_id
                FROM competitor_matches AS m
                WHERE ph.workspace_id IS NULL
                  AND ph.match_id = m.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE review_snapshots AS rs
                SET workspace_id = m.workspace_id
                FROM competitor_matches AS m
                WHERE rs.workspace_id IS NULL
                  AND rs.match_id = m.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE listing_quality_snapshots AS lqs
                SET workspace_id = m.workspace_id
                FROM competitor_matches AS m
                WHERE lqs.workspace_id IS NULL
                  AND lqs.match_id = m.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE keyword_ranks AS kr
                SET workspace_id = p.workspace_id
                FROM products_monitored AS p
                WHERE kr.workspace_id IS NULL
                  AND kr.product_id = p.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE competitor_promotions AS cp
                SET workspace_id = m.workspace_id
                FROM competitor_matches AS m
                WHERE cp.workspace_id IS NULL
                  AND cp.match_id = m.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE my_price_history AS mph
                SET workspace_id = p.workspace_id
                FROM products_monitored AS p
                WHERE mph.workspace_id IS NULL
                  AND mph.product_id = p.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE price_alerts AS pa
                SET workspace_id = COALESCE(
                    (SELECT u.default_workspace_id FROM users AS u WHERE u.id = pa.user_id),
                    (SELECT p.workspace_id FROM products_monitored AS p WHERE p.id = pa.product_id)
                )
                WHERE pa.workspace_id IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE saved_views AS sv
                SET workspace_id = u.default_workspace_id
                FROM users AS u
                WHERE sv.workspace_id IS NULL
                  AND sv.user_id = u.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE repricing_rules AS rr
                SET workspace_id = COALESCE(
                    (SELECT u.default_workspace_id FROM users AS u WHERE u.id = rr.user_id),
                    (SELECT p.workspace_id FROM products_monitored AS p WHERE p.id = rr.product_id)
                )
                WHERE rr.workspace_id IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE api_keys AS ak
                SET workspace_id = u.default_workspace_id
                FROM users AS u
                WHERE ak.workspace_id IS NULL
                  AND ak.user_id = u.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE store_connections AS sc
                SET workspace_id = u.default_workspace_id
                FROM users AS u
                WHERE sc.workspace_id IS NULL
                  AND sc.user_id = u.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE activity_logs AS al
                SET workspace_id = u.default_workspace_id
                FROM users AS u
                WHERE al.workspace_id IS NULL
                  AND al.user_id = u.id
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE notification_logs AS nl
                SET workspace_id = COALESCE(
                    (SELECT pa.workspace_id FROM price_alerts AS pa WHERE pa.id = nl.alert_id),
                    (SELECT u.default_workspace_id FROM users AS u WHERE u.id = nl.user_id)
                )
                WHERE nl.workspace_id IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE push_subscriptions AS ps
                SET workspace_id = u.default_workspace_id
                FROM users AS u
                WHERE ps.workspace_id IS NULL
                  AND ps.user_id = u.id
                """
            )
        )

        validation_queries = {
            "users.default_workspace_id": "SELECT COUNT(*) FROM users WHERE default_workspace_id IS NULL",
            "products_monitored.workspace_id": "SELECT COUNT(*) FROM products_monitored WHERE workspace_id IS NULL",
            "competitor_matches.workspace_id": "SELECT COUNT(*) FROM competitor_matches WHERE workspace_id IS NULL",
            "price_history.workspace_id": "SELECT COUNT(*) FROM price_history WHERE workspace_id IS NULL",
            "review_snapshots.workspace_id": "SELECT COUNT(*) FROM review_snapshots WHERE workspace_id IS NULL",
            "listing_quality_snapshots.workspace_id": "SELECT COUNT(*) FROM listing_quality_snapshots WHERE workspace_id IS NULL",
            "keyword_ranks.workspace_id": "SELECT COUNT(*) FROM keyword_ranks WHERE workspace_id IS NULL",
            "competitor_promotions.workspace_id": "SELECT COUNT(*) FROM competitor_promotions WHERE workspace_id IS NULL",
            "my_price_history.workspace_id": "SELECT COUNT(*) FROM my_price_history WHERE workspace_id IS NULL",
            "price_alerts.workspace_id": "SELECT COUNT(*) FROM price_alerts WHERE workspace_id IS NULL",
            "saved_views.workspace_id": "SELECT COUNT(*) FROM saved_views WHERE workspace_id IS NULL",
            "repricing_rules.workspace_id": "SELECT COUNT(*) FROM repricing_rules WHERE workspace_id IS NULL",
            "api_keys.workspace_id": "SELECT COUNT(*) FROM api_keys WHERE workspace_id IS NULL",
            "store_connections.workspace_id": "SELECT COUNT(*) FROM store_connections WHERE workspace_id IS NULL",
            "activity_logs.workspace_id": "SELECT COUNT(*) FROM activity_logs WHERE workspace_id IS NULL",
            "notification_logs.workspace_id": "SELECT COUNT(*) FROM notification_logs WHERE workspace_id IS NULL",
            "push_subscriptions.workspace_id": "SELECT COUNT(*) FROM push_subscriptions WHERE workspace_id IS NULL",
        }

        failures = []
        for label, query in validation_queries.items():
            count = conn.execute(text(query)).scalar_one()
            if count:
                failures.append(f"{label}={count}")

        if failures:
            raise RuntimeError(
                "Workspace backfill left null ownership on enterprise-scoped rows: "
                + ", ".join(failures)
            )

        workspace_count = conn.execute(text("SELECT COUNT(*) FROM workspaces")).scalar_one()
        print(
            f"[DONE] Backfilled workspace ownership for {len(users)} user(s); "
            f"{workspace_count} workspace row(s) now exist"
        )


if __name__ == "__main__":
    main()
