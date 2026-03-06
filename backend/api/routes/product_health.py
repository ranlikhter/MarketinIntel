"""
Product Health & Review Velocity API Routes
Portfolio health scoring, per-product summaries, and review velocity trends
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.product_health_service import get_product_health_service

router = APIRouter(prefix="/product-health", tags=["Product Health & Review Velocity"])


@router.get("/portfolio")
def get_portfolio_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get health scores and review metrics across the entire product portfolio.

    Returns an aggregated health summary for all products belonging to the
    current user, including review counts, average ratings, and flagged issues.
    """
    svc = get_product_health_service(db, current_user)
    try:
        return svc.get_portfolio_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}")
def get_product_health_summary(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a detailed health summary for a single product.

    - **product_id**: ID of the product to retrieve health data for.

    Returns review statistics, rating distribution, sentiment signals, and
    any active health alerts for the specified product.

    Raises 404 if the product is not found or does not belong to the current user.
    """
    svc = get_product_health_service(db, current_user)
    try:
        result = svc.get_product_health_summary(product_id)
        if result is None or (isinstance(result, dict) and "error" in result):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Product not found") if isinstance(result, dict) else "Product not found",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/velocity/{match_id}")
def get_review_velocity_trend(
    match_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyse"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the review velocity trend for a specific competitor match.

    - **match_id**: ID of the competitor match to analyse.
    - **days**: Look-back window in days (default: 30, range: 1–365).

    Returns a time-series of daily/weekly review counts so you can spot
    acceleration or deceleration in competitor review acquisition.

    Raises 404 if the match is not found or does not belong to the current user.
    """
    svc = get_product_health_service(db, current_user)
    try:
        result = svc.get_review_velocity_trend(match_id, days)
        if result is None or (isinstance(result, dict) and "error" in result):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Match not found") if isinstance(result, dict) else "Match not found",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
