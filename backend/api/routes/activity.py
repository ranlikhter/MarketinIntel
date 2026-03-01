"""
Activity Log API

GET /api/activity   — paginated, filterable audit trail for the current user
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import ActivityLog, User
from api.dependencies import get_current_user

router = APIRouter()


@router.get("/activity")
def get_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="Comma-separated list of categories"),
    action: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    days: Optional[int] = Query(None, description="Limit to last N days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the current user's activity log, newest-first, with optional filters.
    """
    q = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id)

    if category:
        cats = [c.strip() for c in category.split(",") if c.strip()]
        if cats:
            q = q.filter(ActivityLog.category.in_(cats))

    if action:
        q = q.filter(ActivityLog.action == action)

    if entity_id is not None:
        q = q.filter(ActivityLog.entity_id == entity_id)

    if days:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(ActivityLog.created_at >= cutoff)

    total = q.count()
    entries = (
        q.order_by(desc(ActivityLog.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, -(-total // limit)),  # ceiling division
        "items": [
            {
                "id": e.id,
                "action": e.action,
                "category": e.category,
                "description": e.description,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "entity_name": e.entity_name,
                "metadata": e.metadata_ or {},
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }
