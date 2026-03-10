"""
Competitor Promotions API

GET /api/promotions
  → Returns all active promotional offers detected on competitor product pages
    for the authenticated user's products.

Supports filters:
    ?product_id=<int>       — only promotions for a specific monitored product
    ?competitor=<str>       — filter by competitor name (partial, case-insensitive)
    ?promo_type=<str>       — "bogo"|"bundle"|"pct_off"|"free_item"|"other"
    ?days=<int>             — only promos seen within the last N days (default 30)
    ?active_only=true/false — default true

GET /api/promotions/stats
  → Summary counts by type and competitor
"""

from datetime import datetime, timedelta
from utils.time import utcnow
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from database.connection import get_db
from database.models import (
    CompetitorPromotion, CompetitorMatch, ProductMonitored, User
)

router = APIRouter(prefix="/promotions", tags=["Competitor Promotions"])


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("")
def list_promotions(
    product_id: Optional[int] = Query(None),
    competitor: Optional[str] = Query(None),
    promo_type: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List competitor promotions for all of the user's monitored products.
    """
    since = utcnow() - timedelta(days=days)

    q = (
        db.query(CompetitorPromotion, CompetitorMatch, ProductMonitored)
        .join(CompetitorMatch, CompetitorPromotion.match_id == CompetitorMatch.id)
        .join(ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id)
        .filter(
            ProductMonitored.user_id == current_user.id,
            CompetitorPromotion.last_seen_at >= since,
        )
    )

    if active_only:
        q = q.filter(CompetitorPromotion.is_active.is_(True))
    if product_id:
        q = q.filter(ProductMonitored.id == product_id)
    if promo_type:
        q = q.filter(CompetitorPromotion.promo_type == promo_type)
    if competitor:
        q = q.filter(CompetitorMatch.competitor_name.ilike(f"%{competitor}%"))

    rows = q.order_by(CompetitorPromotion.last_seen_at.desc()).limit(200).all()

    return [
        {
            "id": promo.id,
            "promo_type": promo.promo_type,
            "description": promo.description,
            "buy_qty": promo.buy_qty,
            "get_qty": promo.get_qty,
            "discount_pct": promo.discount_pct,
            "free_item_name": promo.free_item_name,
            "is_active": promo.is_active,
            "first_seen_at": promo.first_seen_at.isoformat() if promo.first_seen_at else None,
            "last_seen_at": promo.last_seen_at.isoformat() if promo.last_seen_at else None,
            # Competitor context
            "competitor_name": match.competitor_name,
            "competitor_url": match.competitor_url,
            "match_id": match.id,
            # Product context
            "product_id": product.id,
            "product_title": product.title,
        }
        for promo, match, product in rows
    ]


@router.get("/stats")
def promotion_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregate promotion counts broken down by type and competitor.
    """
    since = utcnow() - timedelta(days=days)

    rows = (
        db.query(CompetitorPromotion, CompetitorMatch)
        .join(CompetitorMatch, CompetitorPromotion.match_id == CompetitorMatch.id)
        .join(ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id)
        .filter(
            ProductMonitored.user_id == current_user.id,
            CompetitorPromotion.is_active.is_(True),
            CompetitorPromotion.last_seen_at >= since,
        )
        .all()
    )

    by_type: dict = {}
    by_competitor: dict = {}
    for promo, match in rows:
        by_type[promo.promo_type] = by_type.get(promo.promo_type, 0) + 1
        by_competitor[match.competitor_name] = by_competitor.get(match.competitor_name, 0) + 1

    return {
        "total_active": len(rows),
        "by_type": by_type,
        "by_competitor": by_competitor,
        "since": since.isoformat(),
    }
