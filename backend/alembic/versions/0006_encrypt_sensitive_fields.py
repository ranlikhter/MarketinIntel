"""Encrypt legacy sensitive fields in place

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op

from database.secure_types import encrypt_existing_sensitive_values


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    encrypt_existing_sensitive_values(op.get_bind())


def downgrade() -> None:
    # Encryption is intentionally one-way at the migration level.
    pass
