"""
Price Analytics API Endpoints
Trendlines, comparisons, and insights
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database.connection import get_db
from database.models import ProductMonitored, User, PriceWar, ActivityLog, PendingPriceChange, MyPriceHistory, StockOpportunity
from api.dependencies import get_current_user, get_current_workspace, ActiveWorkspace
from services.price_analytics import PriceAnalytics
from services.cache_service import get_cached
from services.workspace_service import build_scope_predicate
from sqlalchemy import func, case

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Cache TTLs
_TRENDLINE_TTL = 3600   # 1 hour  — changes only on new scrape
_COMPARE_TTL   = 3600   # 1 hour
_ALERTS_TTL    = 300    # 5 min   — alert status is more time-sensitive


def _ensure_product_owned_by_user(product_id: int, current_user: User, db: Session) -> None:
    """
    Ensure the requested product belongs to the authenticated user.
    We return 404 to avoid leaking whether another user's product exists.
    """
    product = db.query(ProductMonitored.id).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/products/{product_id}/trendline")
async def get_product_trendline(
    product_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get daily price trendline for a product

    - **product_id**: Product to analyze
    - **days**: Number of days to look back (default: 30, max: 365)
    - **start_date**: Optional custom start date (YYYY-MM-DD)
    - **end_date**: Optional custom end date (YYYY-MM-DD)

    Returns daily price trends, insights, and recommendations.
    Results are cached for 1 hour and invalidated on new scrape data.
    """
    _ensure_product_owned_by_user(product_id, current_user, db)

    # If custom dates provided, calculate days between them
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            days = (end - start).days
        except ValueError:
            return {
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }

    cache_key = f"analytics:trendline:{current_user.id}:{product_id}:{days}"
    analytics = PriceAnalytics(db)
    return get_cached(cache_key, _TRENDLINE_TTL,
                      lambda: analytics.get_product_trendline(product_id=product_id, days=days))


@router.get("/products/{product_id}/compare")
async def compare_competitors(
    product_id: int,
    days: int = Query(7, ge=1, le=90, description="Days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compare prices across all competitors for a product

    - **product_id**: Product to analyze
    - **days**: Number of days to look back (default: 7)

    Returns ranked comparison by average price. Cached for 1 hour.
    """
    _ensure_product_owned_by_user(product_id, current_user, db)

    cache_key = f"analytics:compare:{current_user.id}:{product_id}:{days}"
    analytics = PriceAnalytics(db)
    return get_cached(cache_key, _COMPARE_TTL,
                      lambda: analytics.get_competitor_comparison(product_id=product_id, days=days))


@router.get("/products/{product_id}/alerts")
async def get_price_alerts(
    product_id: int,
    threshold: float = Query(5.0, ge=1.0, le=50.0, description="Change threshold %"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get price change alerts for a product

    - **product_id**: Product to check
    - **threshold**: Percentage change to trigger alert (default: 5%)

    Returns alerts for significant price changes in last 24h. Cached for 5 minutes.
    """
    _ensure_product_owned_by_user(product_id, current_user, db)

    cache_key = f"analytics:alerts:{current_user.id}:{product_id}:{threshold}"
    analytics = PriceAnalytics(db)
    return get_cached(cache_key, _ALERTS_TTL,
                      lambda: analytics.get_price_alerts(product_id=product_id, threshold_pct=threshold))


@router.get("/products/{product_id}/date-range")
async def get_date_range_comparison(
    product_id: int,
    start_date_1: str = Query(..., description="First period start (YYYY-MM-DD)"),
    end_date_1: str = Query(..., description="First period end (YYYY-MM-DD)"),
    start_date_2: str = Query(..., description="Second period start (YYYY-MM-DD)"),
    end_date_2: str = Query(..., description="Second period end (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compare two custom date ranges for a product

    Returns price comparison between two time periods
    """
    _ensure_product_owned_by_user(product_id, current_user, db)

    analytics = PriceAnalytics(db)

    try:
        # Parse dates
        start1 = datetime.strptime(start_date_1, '%Y-%m-%d')
        end1 = datetime.strptime(end_date_1, '%Y-%m-%d')
        start2 = datetime.strptime(start_date_2, '%Y-%m-%d')
        end2 = datetime.strptime(end_date_2, '%Y-%m-%d')

        # Calculate days for each period
        days1 = (end1 - start1).days
        days2 = (end2 - start2).days

        # Get trendline for each period
        period1 = analytics.get_product_trendline(product_id, days1)
        period2 = analytics.get_product_trendline(product_id, days2)

        if not period1['success'] or not period2['success']:
            return {
                'success': False,
                'error': 'Failed to fetch data for one or both periods'
            }

        # Compare insights
        insights1 = period1['insights']
        insights2 = period2['insights']

        comparison = {
            'avg_price_change': round(
                insights2['avg_price_period'] - insights1['avg_price_period'], 2
            ),
            'avg_price_change_pct': round(
                (insights2['avg_price_period'] - insights1['avg_price_period']) /
                insights1['avg_price_period'] * 100, 2
            ) if insights1['avg_price_period'] > 0 else 0,
            'volatility_change': round(
                insights2['volatility_pct'] - insights1['volatility_pct'], 2
            ),
            'trend_shift': f"{insights1['trend_direction']} → {insights2['trend_direction']}"
        }

        return {
            'success': True,
            'product_id': product_id,
            'period_1': {
                'start_date': start_date_1,
                'end_date': end_date_1,
                'days': days1,
                'insights': insights1
            },
            'period_2': {
                'start_date': start_date_2,
                'end_date': end_date_2,
                'days': days2,
                'insights': insights2
            },
            'comparison': comparison
        }

    except ValueError as e:
        return {
            'success': False,
            'error': f'Invalid date format: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/snapshots")
async def calculate_daily_snapshots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate daily price snapshots (async background task)"""
    from tasks.analytics_tasks import calculate_daily_snapshots as task
    t = task.delay()
    return {"success": True, "task_id": t.id, "message": "Snapshot calculation queued"}


@router.post("/update")
async def update_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recalculate all analytics (async background task)"""
    from tasks.analytics_tasks import update_all_analytics as task
    t = task.delay()
    return {"success": True, "task_id": t.id, "message": "Analytics update queued"}


@router.get("/quick-wins")
async def get_quick_wins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /analytics/quick-wins

    Returns up to 4 actionable insights for the dashboard "Quick Wins" panel.
    Each insight has a type, message, count, and link so the frontend can
    render a direct CTA button.  Results are computed in 2 batch queries.
    """
    from database.models import CompetitorMatch, PriceAlert
    from sqlalchemy import func as sqlfunc
    from datetime import timedelta
    from collections import defaultdict

    user_id = current_user.id

    # ── 1. Load all products + their my_price ───────────────────────────────
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == user_id,
        ProductMonitored.my_price.isnot(None),
    ).all()

    if not products:
        return {"wins": [], "all_competitive": False}

    product_ids = [p.id for p in products]
    my_price_by_id = {p.id: p.my_price for p in products}
    title_by_id = {p.id: p.title for p in products}

    # ── 2. Load lowest competitor prices per product in one query ───────────
    rows = (
        db.query(
            CompetitorMatch.monitored_product_id,
            sqlfunc.min(CompetitorMatch.latest_price).label("lowest"),
            sqlfunc.max(CompetitorMatch.latest_price).label("highest"),
            sqlfunc.count(CompetitorMatch.id).label("count"),
        )
        .filter(
            CompetitorMatch.monitored_product_id.in_(product_ids),
            CompetitorMatch.latest_price.isnot(None),
        )
        .group_by(CompetitorMatch.monitored_product_id)
        .all()
    )

    lowest_by_id = {r.monitored_product_id: r.lowest for r in rows}
    count_by_id  = {r.monitored_product_id: r.count  for r in rows}

    # ── 3. Compute insights ─────────────────────────────────────────────────
    overpriced = []      # my_price > lowest competitor by > 5%
    underpriced = []     # my_price < lowest competitor by > 10% (opportunity)
    no_data = []         # products with no competitor matches

    for p in products:
        pid = p.id
        lowest = lowest_by_id.get(pid)
        if lowest is None:
            no_data.append(pid)
            continue
        gap_pct = (p.my_price - lowest) / lowest * 100
        if gap_pct > 5:
            overpriced.append({"id": pid, "title": title_by_id[pid], "gap_pct": round(gap_pct, 1)})
        elif gap_pct < -10:
            underpriced.append({"id": pid, "title": title_by_id[pid], "gap_pct": round(gap_pct, 1)})

    # ── 4. Recent alerts (last 24 h) ────────────────────────────────────────
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_alerts = (
        db.query(sqlfunc.count(PriceAlert.id))
        .filter(
            PriceAlert.user_id == user_id,
            PriceAlert.last_triggered_at >= cutoff,
        )
        .scalar() or 0
    )

    wins = []

    if overpriced:
        overpriced.sort(key=lambda x: -x["gap_pct"])
        top = overpriced[0]
        wins.append({
            "type": "overpriced",
            "severity": "high",
            "count": len(overpriced),
            "message": f"You're overpriced vs competitors on {len(overpriced)} product{'s' if len(overpriced) != 1 else ''}",
            "detail": f"{top['title'][:40]} is +{top['gap_pct']}% above lowest competitor",
            "link": "/repricing",
            "cta": "Create Rule",
        })

    if recent_alerts:
        wins.append({
            "type": "alerts",
            "severity": "medium",
            "count": recent_alerts,
            "message": f"{recent_alerts} price alert{'s' if recent_alerts != 1 else ''} triggered in the last 24 h",
            "detail": "Competitor prices changed — review and reprice",
            "link": "/alerts",
            "cta": "View Alerts",
        })

    if no_data:
        wins.append({
            "type": "no_data",
            "severity": "low",
            "count": len(no_data),
            "message": f"{len(no_data)} product{'s have' if len(no_data) != 1 else ' has'} no competitor data yet",
            "detail": "Trigger a scrape to start tracking competitor prices",
            "link": "/products",
            "cta": "Go to Products",
        })

    if underpriced:
        top = underpriced[0]
        wins.append({
            "type": "underpriced",
            "severity": "low",
            "count": len(underpriced),
            "message": f"{len(underpriced)} product{'s are' if len(underpriced) != 1 else ' is'} priced well below competitors",
            "detail": f"Consider raising {top['title'][:40]} — you're {abs(top['gap_pct'])}% below market",
            "link": "/repricing",
            "cta": "Review Pricing",
        })

    all_competitive = not wins
    return {"wins": wins[:4], "all_competitive": all_competitive}


@router.get("/price-wars")
async def get_price_wars(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GET /analytics/price-wars

    Returns recent price war events detected for the current workspace.
    Each event includes the product, number of competitors involved,
    average/max drop percentages, and which competitor moved first.
    """
    from datetime import timedelta
    from sqlalchemy.orm import selectinload

    since = datetime.utcnow() - timedelta(days=days)
    workspace_id = getattr(current_user, "workspace_id", None)

    query = db.query(PriceWar).filter(PriceWar.detected_at >= since)
    if workspace_id:
        query = query.filter(PriceWar.workspace_id == workspace_id)
    else:
        # Fallback: wars for products owned by this user
        owned_ids = [
            p.id for p in db.query(ProductMonitored.id)
            .filter(ProductMonitored.user_id == current_user.id).all()
        ]
        if owned_ids:
            query = query.filter(PriceWar.product_id.in_(owned_ids))
        else:
            return {"price_wars": [], "total": 0}

    wars = (
        query.options(selectinload(PriceWar.product))
        .order_by(PriceWar.detected_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for w in wars:
        product = w.product
        results.append({
            "id": w.id,
            "detected_at": w.detected_at.isoformat() if w.detected_at else None,
            "product_id": w.product_id,
            "product_title": product.title if product else None,
            "product_sku": product.sku if product else None,
            "competitor_count": w.competitor_count,
            "avg_drop_pct": w.avg_drop_pct,
            "max_drop_pct": w.max_drop_pct,
            "price_leader": w.price_leader,
            "window_hours": w.window_hours,
            "status": w.status,
        })

    return {"price_wars": results, "total": len(results), "days": days}


class SimulateRequest(BaseModel):
    product_id: int
    proposed_price: float = Field(gt=0)


@router.post("/simulate")
def simulate_price(
    body: SimulateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    POST /analytics/simulate

    Run the price elasticity simulator for a product.
    Returns projected demand, revenue, and margin changes if the user
    changed to the proposed price.

    The model is computed on-demand and cached for 7 days per product.
    """
    from services.elasticity_service import simulate_price_change

    # Verify product belongs to this user / workspace
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == body.product_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    workspace_id = getattr(current_user, "workspace_id", None)
    if workspace_id and getattr(product, "workspace_id", None) != workspace_id:
        if product.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    result = simulate_price_change(body.product_id, body.proposed_price, db)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


_MARGIN_HEALTH_TTL = 600  # 10 minutes


@router.get("/margin-health")
def get_margin_health(
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Workspace-scoped margin health summary for the dashboard and repricing P&L banner."""
    cache_key = f"analytics:margin_health:{current_user.id}:{aw.workspace_id}"

    def compute():
        from datetime import date
        scope = build_scope_predicate(
            ProductMonitored, workspace_id=aw.workspace_id, user_id=current_user.id
        )
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Average margin % across products with cost data
        avg_row = db.query(
            func.avg(
                (ProductMonitored.my_price - ProductMonitored.cost_price)
                / ProductMonitored.my_price * 100
            )
        ).filter(
            scope,
            ProductMonitored.my_price.isnot(None),
            ProductMonitored.cost_price.isnot(None),
            ProductMonitored.my_price > 0,
        ).scalar()
        avg_margin = round(float(avg_row), 1) if avg_row else None

        # Products currently priced below their own floor
        products_with_cost = db.query(ProductMonitored).filter(
            scope,
            ProductMonitored.my_price.isnot(None),
            ProductMonitored.cost_price.isnot(None),
            ProductMonitored.cost_price > 0,
            ProductMonitored.target_margin_pct.isnot(None),
        ).all()
        below_floor = sum(
            1 for p in products_with_cost
            if p.my_price < (p.cost_price / (1 - p.target_margin_pct / 100))
            and 0 < p.target_margin_pct < 100
        )

        products_no_cost = db.query(func.count(ProductMonitored.id)).filter(
            scope,
            ProductMonitored.cost_price.is_(None),
        ).scalar() or 0

        floor_enforcements_today = db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.workspace_id == aw.workspace_id,
            ActivityLog.action == "repricing.floor_enforced",
            ActivityLog.created_at >= today_start,
        ).scalar() or 0

        autopilot_changes_today = db.query(func.count(MyPriceHistory.id)).filter(
            MyPriceHistory.workspace_id == aw.workspace_id,
            MyPriceHistory.changed_at >= today_start,
            MyPriceHistory.change_reason.ilike("%autopilot%"),
        ).scalar() or 0

        pending_floor_breaches = db.query(func.count(PendingPriceChange.id)).filter(
            PendingPriceChange.workspace_id == aw.workspace_id,
            PendingPriceChange.status == "pending",
            PendingPriceChange.reason == "margin_floor_breach",
        ).scalar() or 0

        return {
            "avg_margin_pct": avg_margin,
            "products_below_floor": below_floor,
            "products_no_cost": int(products_no_cost),
            "floor_enforcements_today": int(floor_enforcements_today),
            "autopilot_changes_today": int(autopilot_changes_today),
            "pending_floor_breaches": int(pending_floor_breaches),
        }

    return get_cached(cache_key, _MARGIN_HEALTH_TTL, compute)


# ── Revenue Recovery Scorecard ────────────────────────────────────────────────

_IMPACT_TTL = 600  # 10 minutes


@router.get("/impact-summary")
def impact_summary(
    period_days: int = 30,
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """
    Revenue recovered/saved by MarketIntel over the given period.
    Reads ActivityLog, StockOpportunity, PendingPriceChange, MyPriceHistory.
    No new models required.
    """
    cache_key = f"analytics:impact:{current_user.id}:{aw.workspace_id}:{period_days}"

    def compute():
        from datetime import timedelta
        period_start = datetime.utcnow() - timedelta(days=period_days)
        prev_start = datetime.utcnow() - timedelta(days=period_days * 2)

        ws_id = aw.workspace_id

        # ── OOS captures ──────────────────────────────────────────────────────
        oos_q = (
            db.query(
                func.sum(StockOpportunity.price_applied - StockOpportunity.price_before),
                func.count(StockOpportunity.id),
            )
            .filter(
                StockOpportunity.workspace_id == ws_id,
                StockOpportunity.status.in_(["applied", "closed"]),
                StockOpportunity.detected_at >= period_start,
                StockOpportunity.price_applied.isnot(None),
                StockOpportunity.price_before.isnot(None),
            )
            .one()
        )
        oos_revenue = round(float(oos_q[0] or 0), 2)
        oos_count = int(oos_q[1] or 0)

        # Best OOS win
        best_oos = (
            db.query(StockOpportunity, ProductMonitored)
            .join(ProductMonitored, StockOpportunity.product_id == ProductMonitored.id)
            .filter(
                StockOpportunity.workspace_id == ws_id,
                StockOpportunity.status.in_(["applied", "closed"]),
                StockOpportunity.detected_at >= period_start,
                StockOpportunity.price_applied.isnot(None),
            )
            .order_by((StockOpportunity.price_applied - StockOpportunity.price_before).desc())
            .first()
        )

        # ── Margin floor saves ────────────────────────────────────────────────
        floor_saves_count = int(
            db.query(func.count(ActivityLog.id))
            .filter(
                ActivityLog.workspace_id == ws_id,
                ActivityLog.action == "repricing.floor_enforced",
                ActivityLog.created_at >= period_start,
            )
            .scalar() or 0
        )

        # ── Repricing wins (applied PendingPriceChanges) ───────────────────────
        repricing_q = (
            db.query(
                func.count(PendingPriceChange.id),
                func.avg(PendingPriceChange.suggested_price - PendingPriceChange.current_price),
            )
            .filter(
                PendingPriceChange.workspace_id == ws_id,
                PendingPriceChange.status == "applied",
                PendingPriceChange.applied_at >= period_start,
            )
            .one()
        )
        repricing_count = int(repricing_q[0] or 0)
        repricing_avg_delta = round(float(repricing_q[1] or 0), 2)

        # ── Autopilot price changes ───────────────────────────────────────────
        autopilot_count = int(
            db.query(func.count(MyPriceHistory.id))
            .filter(
                MyPriceHistory.workspace_id == ws_id,
                MyPriceHistory.changed_at >= period_start,
                MyPriceHistory.note.ilike("%autopilot%"),
            )
            .scalar() or 0
        )

        # ── Previous period OOS (for MoM) ─────────────────────────────────────
        prev_oos = db.query(
            func.sum(StockOpportunity.price_applied - StockOpportunity.price_before)
        ).filter(
            StockOpportunity.workspace_id == ws_id,
            StockOpportunity.status.in_(["applied", "closed"]),
            StockOpportunity.detected_at >= prev_start,
            StockOpportunity.detected_at < period_start,
            StockOpportunity.price_applied.isnot(None),
        ).scalar() or 0

        prev_repricing = db.query(
            func.count(PendingPriceChange.id),
        ).filter(
            PendingPriceChange.workspace_id == ws_id,
            PendingPriceChange.status == "applied",
            PendingPriceChange.applied_at >= prev_start,
            PendingPriceChange.applied_at < period_start,
        ).scalar() or 0

        total_impact = round(
            oos_revenue
            + (floor_saves_count * 5.0)    # conservative $5 estimate per floor save
            + (repricing_count * max(repricing_avg_delta, 0)),
            2,
        )
        prev_impact = round(
            float(prev_oos)
            + (float(prev_repricing) * max(repricing_avg_delta, 0)),
            2,
        )

        biggest_win = None
        if best_oos:
            opp, prod = best_oos
            biggest_win = {
                "product_title": prod.title,
                "delta": round((opp.price_applied or 0) - (opp.price_before or 0), 2),
                "type": "oos",
            }

        return {
            "period_days": period_days,
            "oos_revenue_captured": oos_revenue,
            "oos_count": oos_count,
            "floor_saves_count": floor_saves_count,
            "floor_saves_est": round(floor_saves_count * 5.0, 2),
            "repricing_wins_count": repricing_count,
            "repricing_delta_avg": repricing_avg_delta,
            "autopilot_changes": autopilot_count,
            "total_impact_est": total_impact,
            "prev_period_impact": prev_impact,
            "biggest_win": biggest_win,
        }

    return get_cached(cache_key, _IMPACT_TTL, compute)
