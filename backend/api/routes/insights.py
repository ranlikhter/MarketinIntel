"""
Insights API Routes
Provides actionable recommendations and business intelligence
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import User, ProductMonitored, CompetitorMatch, PriceHistory, RepricingRule
from api.dependencies import ActiveWorkspace, get_current_user, get_current_workspace
from services.insights_service import get_insights_service
from services.cache_service import get_cached
from services.workspace_service import build_scope_predicate

router = APIRouter(prefix="/insights", tags=["Insights & Recommendations"])

# Cache TTLs
_DASHBOARD_TTL = 300   # 5 minutes — users expect near-real-time
_INSIGHTS_TTL  = 600   # 10 minutes for sub-endpoints


# Pydantic response models
class PriorityAction(BaseModel):
    type: str
    severity: str
    title: str
    description: str
    action: str
    products: List[Dict[str, Any]]
    count: int

class Opportunity(BaseModel):
    type: str
    title: str
    description: str
    products: List[Dict[str, Any]]
    potential_revenue: Optional[float] = None

class Threat(BaseModel):
    type: str
    severity: str
    title: str
    description: str
    products: Optional[List[Dict[str, Any]]] = None
    competitors: Optional[List[Dict[str, Any]]] = None

class KeyMetrics(BaseModel):
    total_products: int
    total_competitors: int
    competitive_position: Dict[str, Any]
    active_alerts: int
    price_changes_last_week: int
    avg_competitors_per_product: float

class TrendingProduct(BaseModel):
    product_id: int
    product_title: str
    change_count: int
    reason: str

class DashboardInsightsResponse(BaseModel):
    priorities: List[PriorityAction]
    opportunities: List[Opportunity]
    threats: List[Threat]
    key_metrics: KeyMetrics
    trending: List[TrendingProduct]

class OpportunityScoreResponse(BaseModel):
    product_id: int
    score: int
    interpretation: str


@router.get("/dashboard", response_model=DashboardInsightsResponse)
async def get_dashboard_insights(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard insights

    Returns:
    - **priorities**: Top actions user should take today
    - **opportunities**: Revenue opportunities and market gaps
    - **threats**: Competitive threats and risks
    - **key_metrics**: KPIs and performance metrics
    - **trending**: Products with interesting activity

    Cached per user for 5 minutes.
    """
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    scope_key = current_workspace.workspace_id or current_user.id
    cache_key = f"insights:dashboard:{scope_key}"

    try:
        return get_cached(cache_key, _DASHBOARD_TTL,
                          insights_service.get_dashboard_insights)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


@router.get("/priorities", response_model=List[PriorityAction])
async def get_priorities(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Get today's priority actions

    Returns list of actions ranked by urgency:
    - High severity: Immediate action needed
    - Medium severity: Review soon
    - Low severity: Can wait
    """
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    scope_key = current_workspace.workspace_id or current_user.id
    cache_key = f"insights:priorities:{scope_key}"

    try:
        return get_cached(cache_key, _INSIGHTS_TTL,
                          insights_service.get_today_priorities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get priorities: {str(e)}")


@router.get("/opportunities", response_model=List[Opportunity])
async def get_opportunities(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Get revenue opportunities and market insights

    Identifies:
    - Products where you can raise prices
    - Low competition products (pricing power)
    - Bundling opportunities
    - Market gaps
    """
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    scope_key = current_workspace.workspace_id or current_user.id
    cache_key = f"insights:opportunities:{scope_key}"

    try:
        return get_cached(cache_key, _INSIGHTS_TTL,
                          insights_service.get_opportunities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get opportunities: {str(e)}")


@router.get("/threats", response_model=List[Threat])
async def get_threats(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Get competitive threats and market risks

    Identifies:
    - Aggressive competitors consistently undercutting
    - Declining market prices
    - Lost competitive position
    - Market share threats
    """
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    scope_key = current_workspace.workspace_id or current_user.id
    cache_key = f"insights:threats:{scope_key}"

    try:
        return get_cached(cache_key, _INSIGHTS_TTL,
                          insights_service.get_threats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get threats: {str(e)}")


@router.get("/metrics", response_model=KeyMetrics)
async def get_key_metrics(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Get key performance metrics"""
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    scope_key = current_workspace.workspace_id or current_user.id
    cache_key = f"insights:metrics:{scope_key}"

    try:
        return get_cached(cache_key, _INSIGHTS_TTL,
                          insights_service.get_key_metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/trending", response_model=List[TrendingProduct])
async def get_trending_products(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Get trending products with high activity"""
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    scope_key = current_workspace.workspace_id or current_user.id
    cache_key = f"insights:trending:{scope_key}"

    try:
        return get_cached(cache_key, _INSIGHTS_TTL,
                          insights_service.get_trending_products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trending products: {str(e)}")


@router.get("/opportunity-score/{product_id}", response_model=OpportunityScoreResponse)
async def get_opportunity_score(
    product_id: int,
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Calculate opportunity score for a specific product

    Score 0-100:
    - 80-100: High opportunity (take action now)
    - 50-79: Medium opportunity (monitor closely)
    - 0-49: Low opportunity (stable/competitive)
    """
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )

    try:
        score = insights_service.calculate_opportunity_score(product_id)

        if score >= 80:
            interpretation = "High opportunity - Take action now!"
        elif score >= 50:
            interpretation = "Medium opportunity - Monitor closely"
        else:
            interpretation = "Low opportunity - Stable/competitive"

        return {"product_id": product_id, "score": score, "interpretation": interpretation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate opportunity score: {str(e)}")


# ============================================================
# Price War Dashboard
# ============================================================

@router.get("/price-wars")
async def get_price_wars(
    hours: int = Query(72, ge=6, le=168, description="Look-back window in hours"),
    min_competitors: int = Query(3, ge=2, le=10, description="Min competitors needed to flag a price war"),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Detect active price wars across your product catalog.

    A price war is flagged when **min_competitors** or more competing listings
    for the same product each dropped their price within the look-back window.

    Returns products sorted by the number of competitors that dropped prices,
    with recommended response actions.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Fetch user's products
    products = db.query(ProductMonitored).filter(
        build_scope_predicate(
            ProductMonitored,
            workspace_id=current_workspace.workspace_id,
            user_id=current_user.id,
        )
    ).all()

    price_wars = []

    for product in products:
        matches = db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product.id
        ).all()

        competitors_with_drops = []

        for match in matches:
            # Get the two most-recent price history rows in the window
            recent = (
                db.query(PriceHistory)
                .filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= cutoff
                )
                .order_by(PriceHistory.timestamp.desc())
                .limit(2)
                .all()
            )

            if len(recent) < 2:
                continue

            latest_price = recent[0].price
            earlier_price = recent[1].price

            if earlier_price and latest_price < earlier_price:
                drop_pct = round((earlier_price - latest_price) / earlier_price * 100, 2)
                competitors_with_drops.append({
                    "competitor": match.competitor_name,
                    "url": match.competitor_url,
                    "previous_price": earlier_price,
                    "current_price": latest_price,
                    "drop_pct": drop_pct,
                    "dropped_at": recent[0].timestamp.isoformat(),
                })

        if len(competitors_with_drops) >= min_competitors:
            avg_drop = round(
                sum(c["drop_pct"] for c in competitors_with_drops) / len(competitors_with_drops), 2
            )
            lowest_competitor_price = min(c["current_price"] for c in competitors_with_drops)

            # Recommended action
            if product.my_price and product.my_price > lowest_competitor_price:
                action = f"Consider matching ${lowest_competitor_price:.2f} — you're currently priced above all dropping competitors."
            elif product.my_price and product.my_price <= lowest_competitor_price:
                action = "You're already at or below the lowest competitor. Hold or wait for the war to stabilise."
            else:
                action = f"Set your price — lowest competitor is at ${lowest_competitor_price:.2f}."

            price_wars.append({
                "product_id": product.id,
                "product_title": product.title,
                "my_price": product.my_price,
                "competitors_dropped": len(competitors_with_drops),
                "avg_drop_pct": avg_drop,
                "lowest_competitor_price": lowest_competitor_price,
                "competitors": competitors_with_drops,
                "recommended_action": action,
                "severity": "high" if avg_drop >= 10 else "medium" if avg_drop >= 5 else "low",
            })

    # Sort: most competitors dropped first, then largest avg drop
    price_wars.sort(key=lambda x: (-x["competitors_dropped"], -x["avg_drop_pct"]))

    return {
        "success": True,
        "look_back_hours": hours,
        "min_competitors_threshold": min_competitors,
        "total_price_wars": len(price_wars),
        "price_wars": price_wars,
    }


# ============================================================
# Competitor Out-of-Stock Tracker
# ============================================================

_OOS_KEYWORDS = {"out of stock", "out_of_stock", "unavailable", "sold out",
                 "currently unavailable", "not available", "no stock"}

@router.get("/competitor-oos")
async def get_competitor_oos(
    min_hours: int = Query(24, ge=1, le=720, description="Minimum hours OOS to include"),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Find competitors that are currently out of stock — your opportunity window.

    Returns competitor listings that have been OOS for at least **min_hours**,
    sorted by how long they've been unavailable. Longer OOS = bigger opportunity
    to capture demand or raise your own price.
    """
    now = datetime.utcnow()
    oos_cutoff = now - timedelta(hours=min_hours)

    products = db.query(ProductMonitored).filter(
        build_scope_predicate(
            ProductMonitored,
            workspace_id=current_workspace.workspace_id,
            user_id=current_user.id,
        )
    ).all()

    opportunities = []

    for product in products:
        matches = db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product.id
        ).all()

        for match in matches:
            # Check current stock status via string field
            stock_str = (match.stock_status or "").lower().strip()
            is_oos_by_status = stock_str in _OOS_KEYWORDS

            # Cross-check with most recent PriceHistory.in_stock flag
            latest_ph = (
                db.query(PriceHistory)
                .filter(PriceHistory.match_id == match.id)
                .order_by(PriceHistory.timestamp.desc())
                .first()
            )
            is_oos_by_history = (latest_ph is not None and latest_ph.in_stock is False)

            if not (is_oos_by_status or is_oos_by_history):
                continue

            # Find when they went OOS (earliest consecutive OOS record)
            oos_since = latest_ph.timestamp if latest_ph else now

            # Walk back through history to find onset
            history = (
                db.query(PriceHistory)
                .filter(PriceHistory.match_id == match.id)
                .order_by(PriceHistory.timestamp.desc())
                .limit(50)
                .all()
            )
            for ph in history:
                if ph.in_stock is True:
                    break
                oos_since = ph.timestamp

            hours_oos = round((now - oos_since).total_seconds() / 3600, 1)

            if hours_oos < min_hours:
                continue

            # Opportunity score: longer OOS = higher score
            opp_score = min(100, int(hours_oos / 24 * 20))  # +20 per day, max 100

            opportunities.append({
                "product_id": product.id,
                "product_title": product.title,
                "my_price": product.my_price,
                "competitor": match.competitor_name,
                "competitor_url": match.competitor_url,
                "last_known_price": match.latest_price,
                "oos_since": oos_since.isoformat(),
                "hours_oos": hours_oos,
                "days_oos": round(hours_oos / 24, 1),
                "opportunity_score": opp_score,
                "recommendation": (
                    f"{match.competitor_name} has been OOS for {round(hours_oos/24, 1)} day(s). "
                    "Consider raising your price to capture displaced demand."
                    if product.my_price else
                    f"{match.competitor_name} has been OOS for {round(hours_oos/24, 1)} day(s) — pricing opportunity."
                ),
            })

    # Sort by longest OOS first
    opportunities.sort(key=lambda x: -x["hours_oos"])

    return {
        "success": True,
        "min_hours_oos": min_hours,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities,
    }


# ============================================================
# Existing extra endpoints (positioning, price-drops, etc.)
# ============================================================

@router.get("/positioning")
async def get_competitive_positioning(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Get competitive positioning analysis"""
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    try:
        return insights_service.get_competitive_positioning()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-drops")
async def get_price_drop_opportunities(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Get price drop opportunities — competitors who recently lowered price"""
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    try:
        return insights_service.get_price_drop_opportunities()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/best-time-to-buy")
async def get_best_time_to_buy(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Get seasonal buying recommendations based on historical price patterns"""
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    try:
        return insights_service.get_best_time_to_buy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_ai_suggestions(
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Get AI-powered pricing suggestions"""
    insights_service = get_insights_service(
        db,
        current_user,
        workspace_id=current_workspace.workspace_id,
    )
    try:
        return insights_service.get_ai_suggestions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
