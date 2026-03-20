"""Add user SSO fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String(length=50), nullable=False, server_default="local"))
    op.add_column("users", sa.Column("auth_provider_subject", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("password_login_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("idx_users_auth_provider_subject", "users", ["auth_provider_subject"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_users_auth_provider_subject", table_name="users")
    op.drop_column("users", "password_login_enabled")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "auth_provider_subject")
    op.drop_column("users", "auth_provider")
