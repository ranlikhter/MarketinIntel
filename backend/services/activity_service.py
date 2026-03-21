"""
Activity Logging Service

Provides a single log_activity() helper that any route can call to record
a user action into the activity_logs table.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from database.models import ActivityLog


def log_activity(
    db: Session,
    user_id: int,
    action: str,
    category: str,
    description: str,
    entity_type: str = None,
    entity_id: int = None,
    entity_name: str = None,
    metadata: dict = None,
    status: str = "success",
    workspace_id: int | None = None,
):
    """
    Record one user action.

    action    — dot-notation verb, e.g. "product.create", "price.update"
    category  — top-level bucket: product | price | alert | rule |
                 competitor | integration | account | team
    description — plain-English sentence shown in the activity feed
    """
    entry = ActivityLog(
        user_id=user_id,
        workspace_id=workspace_id,
        action=action,
        category=category,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        metadata_=metadata or {},
        status=status,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    # Flush so the entry is persisted with the surrounding transaction.
    # Callers commit themselves after their own logic succeeds.
    db.flush()
