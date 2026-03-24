"""
Price Analytics API Endpoints
Trendlines, comparisons, and insights
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database.connection import get_db
from database.models import ProductMonitored, User
from api.dependencies import get_current_user
from services.price_analytics import PriceAnalytics
from services.cache_service import get_cached
from api.dependencies import get_current_user

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

    cache_key = f"analytics:trendline:{product_id}:{days}"
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

    cache_key = f"analytics:compare:{product_id}:{days}"
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

    cache_key = f"analytics:alerts:{product_id}:{threshold}"
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
