"""Baseline — marks all tables created by setup.py/create_all as applied.

This migration is intentionally a no-op.  All tables up to v10 were created
by the legacy database/setup.py script.  Stamping this revision with
`alembic stamp 0001` tells Alembic that the current database is already at
this point so it won't try to re-create existing tables.

To bring an existing database under Alembic control:
    alembic stamp 0001

New databases should just run:
    alembic upgrade head

Revision ID: 0001
Revises:
Create Date: 2026-03-04
"""

from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All pre-existing tables are managed by database/setup.py.
    # This revision is a no-op checkpoint.
    pass


def downgrade() -> None:
    pass
