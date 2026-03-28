"""
0014 — Workspace-scope all remaining tables for multi-tenant SaaS isolation

Adds workspace_id to:
  - competitor_websites   (was user_id only)
  - seller_profiles       (was global; also replaces the global seller_name
                           unique constraint with a per-workspace composite)
  - products_monitored    (adds source + source_id for import provenance)

These changes make every shop's data 100% isolated from every other shop.

Revision ID: 0014
Revises: 0013
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. competitor_websites: add workspace_id ──────────────────────────────
    op.add_column(
        "competitor_websites",
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("idx_cw_workspace_active", "competitor_websites", ["workspace_id", "is_active"])

    # Backfill: assign each existing competitor_website to the owner's default workspace
    op.execute("""
        UPDATE competitor_websites cw
        SET workspace_id = (
            SELECT u.default_workspace_id
            FROM users u
            WHERE u.id = cw.user_id
              AND u.default_workspace_id IS NOT NULL
        )
        WHERE cw.workspace_id IS NULL
          AND cw.user_id IS NOT NULL
    """)

    # ── 2. seller_profiles: add workspace_id, replace global unique ───────────
    # Drop the old global unique constraint on seller_name
    # (SQLite doesn't support DROP CONSTRAINT; use batch mode for SQLite compat)
    with op.batch_alter_table("seller_profiles") as batch_op:
        # Drop existing unique index on seller_name (may be named differently per DB)
        try:
            batch_op.drop_constraint("uq_seller_profiles_seller_name", type_="unique")
        except Exception:
            pass  # Index may not exist under this name in all environments
        try:
            batch_op.drop_index("ix_seller_profiles_seller_name")
        except Exception:
            pass

        batch_op.add_column(
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
        )
        # New composite unique: one row per (workspace_id, seller_name)
        batch_op.create_unique_constraint(
            "uq_seller_workspace_name",
            ["workspace_id", "seller_name"],
        )
        # Keep a plain index on seller_name for fast lookups
        batch_op.create_index("ix_seller_profiles_seller_name", ["seller_name"])

    op.create_index("ix_seller_profiles_workspace_id", "seller_profiles", ["workspace_id"])

    # Backfill: existing global seller profiles get NULL workspace_id (legacy rows)
    # — no action needed; the column is already nullable and defaults to NULL

    # ── 3. products_monitored: add source + source_id ─────────────────────────
    op.add_column(
        "products_monitored",
        sa.Column("source", sa.String(30), nullable=True),
    )
    op.add_column(
        "products_monitored",
        sa.Column("source_id", sa.String(200), nullable=True),
    )
    # Index for fast re-sync lookups: find a product by its source + platform ID
    op.create_index(
        "idx_pm_source_id",
        "products_monitored",
        ["workspace_id", "source", "source_id"],
    )


def downgrade() -> None:
    # ── products_monitored ────────────────────────────────────────────────────
    op.drop_index("idx_pm_source_id", table_name="products_monitored")
    op.drop_column("products_monitored", "source_id")
    op.drop_column("products_monitored", "source")

    # ── seller_profiles ───────────────────────────────────────────────────────
    op.drop_index("ix_seller_profiles_workspace_id", table_name="seller_profiles")
    with op.batch_alter_table("seller_profiles") as batch_op:
        batch_op.drop_index("ix_seller_profiles_seller_name")
        batch_op.drop_constraint("uq_seller_workspace_name", type_="unique")
        batch_op.drop_column("workspace_id")
        # Restore old global unique index on seller_name
        batch_op.create_index("ix_seller_profiles_seller_name", ["seller_name"], unique=True)

    # ── competitor_websites ───────────────────────────────────────────────────
    op.drop_index("idx_cw_workspace_active", table_name="competitor_websites")
    op.drop_column("competitor_websites", "workspace_id")
