"""Backfill workspace ownership for existing enterprise data

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-20
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _require_postgresql() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError(
            "Migration 0009_backfill_workspace_scope requires PostgreSQL. "
            "Run it after the PostgreSQL cutover, not on the legacy SQLite database."
        )


def _personal_workspace_name(user_row: dict[str, object]) -> str:
    full_name = (user_row.get("full_name") or "").strip() if user_row.get("full_name") else ""
    email = (user_row.get("email") or "").strip() if user_row.get("email") else ""
    base = full_name or (email.split("@", 1)[0] if email else f"user-{user_row['id']}")
    return f"{base[:220]} Personal Workspace"[:255]


def _scalar_subquery(table: sa.Table, source_column: sa.Column, target_column: sa.Column) -> sa.ScalarSelect:
    return sa.select(target_column).where(source_column == table.c.id).scalar_subquery()


def upgrade() -> None:
    _require_postgresql()
    bind = op.get_bind()
    metadata = sa.MetaData()

    users = sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("email", sa.String()),
        sa.Column("full_name", sa.String()),
        sa.Column("default_workspace_id", sa.Integer()),
    )
    workspaces = sa.Table(
        "workspaces",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("name", sa.String()),
        sa.Column("owner_id", sa.Integer()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    workspace_members = sa.Table(
        "workspace_members",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("role", sa.String()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("invited_at", sa.DateTime()),
        sa.Column("joined_at", sa.DateTime()),
    )
    products = sa.Table(
        "products_monitored",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    matches = sa.Table(
        "competitor_matches",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("monitored_product_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    price_history = sa.Table(
        "price_history",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("match_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    review_snapshots = sa.Table(
        "review_snapshots",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("match_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    listing_quality_snapshots = sa.Table(
        "listing_quality_snapshots",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("match_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    keyword_ranks = sa.Table(
        "keyword_ranks",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("product_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    competitor_promotions = sa.Table(
        "competitor_promotions",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("match_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    my_price_history = sa.Table(
        "my_price_history",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("product_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    price_alerts = sa.Table(
        "price_alerts",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("product_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    saved_views = sa.Table(
        "saved_views",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    repricing_rules = sa.Table(
        "repricing_rules",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("product_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    api_keys = sa.Table(
        "api_keys",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    store_connections = sa.Table(
        "store_connections",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    activity_logs = sa.Table(
        "activity_logs",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    notification_logs = sa.Table(
        "notification_logs",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("alert_id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )
    push_subscriptions = sa.Table(
        "push_subscriptions",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("workspace_id", sa.Integer()),
    )

    now = datetime.now(UTC)

    user_rows = bind.execute(
        sa.select(users.c.id, users.c.email, users.c.full_name).order_by(users.c.id)
    ).mappings().all()
    workspace_rows = bind.execute(
        sa.select(workspaces.c.id, workspaces.c.owner_id, workspaces.c.is_active).order_by(
            workspaces.c.owner_id, workspaces.c.id
        )
    ).mappings().all()

    active_workspace_by_owner: dict[int, int] = {}
    any_workspace_by_owner: dict[int, int] = {}
    for row in workspace_rows:
        owner_id = int(row["owner_id"])
        any_workspace_by_owner.setdefault(owner_id, int(row["id"]))
        if row["is_active"]:
            active_workspace_by_owner.setdefault(owner_id, int(row["id"]))

    default_workspace_by_user: dict[int, int] = {}
    for user_row in user_rows:
        user_id = int(user_row["id"])
        workspace_id = active_workspace_by_owner.get(user_id) or any_workspace_by_owner.get(user_id)
        if workspace_id is None:
            result = bind.execute(
                workspaces.insert().values(
                    name=_personal_workspace_name(user_row),
                    owner_id=user_id,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            workspace_id = int(result.inserted_primary_key[0])
            active_workspace_by_owner[user_id] = workspace_id
            any_workspace_by_owner[user_id] = workspace_id

        default_workspace_by_user[user_id] = workspace_id
        bind.execute(
            sa.update(users)
            .where(users.c.id == user_id)
            .values(default_workspace_id=workspace_id)
        )

    membership_rows = bind.execute(
        sa.select(workspace_members.c.id, workspace_members.c.workspace_id, workspace_members.c.user_id)
    ).mappings().all()
    membership_id_by_pair = {
        (int(row["workspace_id"]), int(row["user_id"])): int(row["id"])
        for row in membership_rows
    }

    for user_id, workspace_id in default_workspace_by_user.items():
        member_id = membership_id_by_pair.get((workspace_id, user_id))
        if member_id is None:
            result = bind.execute(
                workspace_members.insert().values(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role="ADMIN",
                    is_active=True,
                    invited_at=now,
                    joined_at=now,
                )
            )
            membership_id_by_pair[(workspace_id, user_id)] = int(result.inserted_primary_key[0])
        else:
            bind.execute(
                sa.update(workspace_members)
                .where(workspace_members.c.id == member_id)
                .values(
                    role="ADMIN",
                    is_active=True,
                    joined_at=sa.func.coalesce(workspace_members.c.joined_at, now),
                )
            )

    bind.execute(
        sa.update(products)
        .where(products.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(users.c.default_workspace_id)
            .where(users.c.id == products.c.user_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(matches)
        .where(matches.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(products.c.workspace_id)
            .where(products.c.id == matches.c.monitored_product_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(price_history)
        .where(price_history.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(matches.c.workspace_id)
            .where(matches.c.id == price_history.c.match_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(review_snapshots)
        .where(review_snapshots.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(matches.c.workspace_id)
            .where(matches.c.id == review_snapshots.c.match_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(listing_quality_snapshots)
        .where(listing_quality_snapshots.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(matches.c.workspace_id)
            .where(matches.c.id == listing_quality_snapshots.c.match_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(keyword_ranks)
        .where(keyword_ranks.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(products.c.workspace_id)
            .where(products.c.id == keyword_ranks.c.product_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(competitor_promotions)
        .where(competitor_promotions.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(matches.c.workspace_id)
            .where(matches.c.id == competitor_promotions.c.match_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(my_price_history)
        .where(my_price_history.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(products.c.workspace_id)
            .where(products.c.id == my_price_history.c.product_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(price_alerts)
        .where(price_alerts.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.func.coalesce(
                sa.select(users.c.default_workspace_id)
                .where(users.c.id == price_alerts.c.user_id)
                .scalar_subquery(),
                sa.select(products.c.workspace_id)
                .where(products.c.id == price_alerts.c.product_id)
                .scalar_subquery(),
            )
        )
    )
    bind.execute(
        sa.update(saved_views)
        .where(saved_views.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(users.c.default_workspace_id)
            .where(users.c.id == saved_views.c.user_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(repricing_rules)
        .where(repricing_rules.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.func.coalesce(
                sa.select(users.c.default_workspace_id)
                .where(users.c.id == repricing_rules.c.user_id)
                .scalar_subquery(),
                sa.select(products.c.workspace_id)
                .where(products.c.id == repricing_rules.c.product_id)
                .scalar_subquery(),
            )
        )
    )
    bind.execute(
        sa.update(api_keys)
        .where(api_keys.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(users.c.default_workspace_id)
            .where(users.c.id == api_keys.c.user_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(store_connections)
        .where(store_connections.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(users.c.default_workspace_id)
            .where(users.c.id == store_connections.c.user_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(activity_logs)
        .where(activity_logs.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(users.c.default_workspace_id)
            .where(users.c.id == activity_logs.c.user_id)
            .scalar_subquery()
        )
    )
    bind.execute(
        sa.update(notification_logs)
        .where(notification_logs.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.func.coalesce(
                sa.select(price_alerts.c.workspace_id)
                .where(price_alerts.c.id == notification_logs.c.alert_id)
                .scalar_subquery(),
                sa.select(users.c.default_workspace_id)
                .where(users.c.id == notification_logs.c.user_id)
                .scalar_subquery(),
            )
        )
    )
    bind.execute(
        sa.update(push_subscriptions)
        .where(push_subscriptions.c.workspace_id.is_(None))
        .values(
            workspace_id=sa.select(users.c.default_workspace_id)
            .where(users.c.id == push_subscriptions.c.user_id)
            .scalar_subquery()
        )
    )

    validation_targets = [
        ("users.default_workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(users).where(users.c.default_workspace_id.is_(None))
        ).scalar_one()),
        ("products_monitored.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(products).where(products.c.workspace_id.is_(None))
        ).scalar_one()),
        ("competitor_matches.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(matches).where(matches.c.workspace_id.is_(None))
        ).scalar_one()),
        ("price_history.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(price_history).where(price_history.c.workspace_id.is_(None))
        ).scalar_one()),
        ("review_snapshots.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(review_snapshots).where(review_snapshots.c.workspace_id.is_(None))
        ).scalar_one()),
        ("listing_quality_snapshots.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(listing_quality_snapshots).where(listing_quality_snapshots.c.workspace_id.is_(None))
        ).scalar_one()),
        ("keyword_ranks.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(keyword_ranks).where(keyword_ranks.c.workspace_id.is_(None))
        ).scalar_one()),
        ("competitor_promotions.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(competitor_promotions).where(competitor_promotions.c.workspace_id.is_(None))
        ).scalar_one()),
        ("my_price_history.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(my_price_history).where(my_price_history.c.workspace_id.is_(None))
        ).scalar_one()),
        ("price_alerts.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(price_alerts).where(price_alerts.c.workspace_id.is_(None))
        ).scalar_one()),
        ("saved_views.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(saved_views).where(saved_views.c.workspace_id.is_(None))
        ).scalar_one()),
        ("repricing_rules.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(repricing_rules).where(repricing_rules.c.workspace_id.is_(None))
        ).scalar_one()),
        ("api_keys.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(api_keys).where(api_keys.c.workspace_id.is_(None))
        ).scalar_one()),
        ("store_connections.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(store_connections).where(store_connections.c.workspace_id.is_(None))
        ).scalar_one()),
        ("activity_logs.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(activity_logs).where(activity_logs.c.workspace_id.is_(None))
        ).scalar_one()),
        ("notification_logs.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(notification_logs).where(notification_logs.c.workspace_id.is_(None))
        ).scalar_one()),
        ("push_subscriptions.workspace_id", bind.execute(
            sa.select(sa.func.count()).select_from(push_subscriptions).where(push_subscriptions.c.workspace_id.is_(None))
        ).scalar_one()),
    ]
    failures = [f"{label}={count}" for label, count in validation_targets if count]
    if failures:
        raise RuntimeError(
            "Workspace backfill left null ownership on enterprise-scoped rows: "
            + ", ".join(failures)
            + ". Resolve orphaned data before continuing to 0010."
        )


def downgrade() -> None:
    # This migration reassigns ownership data and may create personal workspaces.
    # Reversing it automatically would be destructive, so downgrade is intentionally a no-op.
    pass
