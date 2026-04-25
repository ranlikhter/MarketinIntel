"""
Stock Opportunity Routes

Surfaces and manages Out-of-Stock opportunities: when competitors go OOS,
users can raise prices to capture demand. Endpoints support listing, applying,
and dismissing individual opportunities.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from api.dependencies import ActiveWorkspace, get_current_user, get_current_workspace
from database.connection import get_db
from database.models import MyPriceHistory, ProductMonitored, StockOpportunity, User
from services.workspace_service import build_scope_predicate

router = APIRouter()


class StockOpportunityResponse(BaseModel):
    id: int
    product_id: int
    workspace_id: Optional[int] = None
    product_title: Optional[str] = None
    product_sku: Optional[str] = None

    oos_match_ids: Optional[list] = None
    oos_competitor_count: int = 0

    detected_at: datetime
    closed_at: Optional[datetime] = None
    status: str

    price_before: Optional[float] = None
    price_suggested: Optional[float] = None
    price_applied: Optional[float] = None
    raise_pct: Optional[float] = None
    revenue_captured_estimate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class StockOpportunitySummary(BaseModel):
    open_count: int = 0
    applied_today: int = 0
    dismissed_today: int = 0
    total_revenue_estimate: float = 0.0


@router.get("/opportunities/stock", response_model=list[StockOpportunityResponse])
def list_stock_opportunities(
    status: Optional[str] = None,  # "open" | "applied" | "dismissed" | "closed"
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """List stock opportunities for the current workspace."""
    scope = build_scope_predicate(StockOpportunity, aw.workspace_id, current_user.id)
    q = db.query(StockOpportunity).filter(scope)
    if status:
        q = q.filter(StockOpportunity.status == status)
    opps = q.order_by(StockOpportunity.detected_at.desc()).offset(offset).limit(limit).all()

    # Attach product title/sku without N+1
    product_ids = list({o.product_id for o in opps})
    products = {
        p.id: p
        for p in db.query(ProductMonitored).filter(ProductMonitored.id.in_(product_ids)).all()
    }

    results = []
    for opp in opps:
        data = StockOpportunityResponse.model_validate(opp)
        prod = products.get(opp.product_id)
        if prod:
            data.product_title = prod.title
            data.product_sku = prod.sku
        results.append(data)
    return results


@router.get("/opportunities/stock/summary", response_model=StockOpportunitySummary)
def stock_opportunity_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Summary counts for the dashboard panel."""
    from datetime import timedelta
    from sqlalchemy import func

    scope = build_scope_predicate(StockOpportunity, aw.workspace_id, current_user.id)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    open_count = (
        db.query(func.count(StockOpportunity.id))
        .filter(scope, StockOpportunity.status == "open")
        .scalar() or 0
    )
    applied_today = (
        db.query(func.count(StockOpportunity.id))
        .filter(scope, StockOpportunity.status == "applied", StockOpportunity.detected_at >= today_start)
        .scalar() or 0
    )
    dismissed_today = (
        db.query(func.count(StockOpportunity.id))
        .filter(scope, StockOpportunity.status == "dismissed", StockOpportunity.detected_at >= today_start)
        .scalar() or 0
    )
    revenue_est = (
        db.query(func.sum(StockOpportunity.revenue_captured_estimate))
        .filter(scope, StockOpportunity.status.in_(["applied", "open"]))
        .scalar() or 0.0
    )

    return StockOpportunitySummary(
        open_count=open_count,
        applied_today=applied_today,
        dismissed_today=dismissed_today,
        total_revenue_estimate=round(float(revenue_est), 2),
    )


@router.post("/opportunities/stock/{opportunity_id}/apply", response_model=StockOpportunityResponse)
def apply_stock_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Manually apply a price raise for a stock opportunity."""
    scope = build_scope_predicate(StockOpportunity, aw.workspace_id, current_user.id)
    opp = db.query(StockOpportunity).filter(scope, StockOpportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status != "open":
        raise HTTPException(status_code=400, detail=f"Opportunity is already {opp.status}")
    if not opp.price_suggested:
        raise HTTPException(status_code=400, detail="No suggested price available")

    product = db.query(ProductMonitored).filter(ProductMonitored.id == opp.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old_price = product.my_price
    product.my_price = opp.price_suggested
    db.add(MyPriceHistory(
        product_id=product.id,
        workspace_id=product.workspace_id,
        old_price=old_price,
        new_price=opp.price_suggested,
        note="OOS opportunity: manual apply",
    ))

    opp.status = "applied"
    opp.price_applied = opp.price_suggested
    db.commit()
    db.refresh(opp)

    result = StockOpportunityResponse.model_validate(opp)
    result.product_title = product.title
    result.product_sku = product.sku
    return result


@router.post("/opportunities/stock/{opportunity_id}/dismiss", response_model=StockOpportunityResponse)
def dismiss_stock_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Dismiss a stock opportunity without applying the price change."""
    scope = build_scope_predicate(StockOpportunity, aw.workspace_id, current_user.id)
    opp = db.query(StockOpportunity).filter(scope, StockOpportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status not in ("open",):
        raise HTTPException(status_code=400, detail=f"Opportunity is already {opp.status}")

    opp.status = "dismissed"
    opp.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(opp)

    product = db.query(ProductMonitored).filter(ProductMonitored.id == opp.product_id).first()
    result = StockOpportunityResponse.model_validate(opp)
    if product:
        result.product_title = product.title
        result.product_sku = product.sku
    return result
