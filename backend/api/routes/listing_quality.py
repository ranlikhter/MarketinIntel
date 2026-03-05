"""
Listing Quality Intelligence API Routes
Portfolio-wide listing gap analysis, per-product comparisons, and quality trends
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.listing_quality_service import get_listing_quality_service

router = APIRouter(prefix="/listing-quality", tags=["Listing Quality Intelligence"])


@router.get("/portfolio")
def get_portfolio_listing_gaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Identify listing quality gaps across the entire product portfolio.

    Compares your product listings against competitor listings and surfaces
    missing or under-optimised content elements such as bullet points, images,
    A+ content, and keyword coverage. Results are sorted by impact severity.
    """
    svc = get_listing_quality_service(db, current_user)
    try:
        return svc.get_portfolio_listing_gaps()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}")
def get_listing_comparison(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compare your listing quality against competitors for a specific product.

    - **product_id**: ID of the product to compare.

    Returns a side-by-side quality scorecard covering title length, bullet
    count, image count, description richness, and keyword density relative
    to the top-ranked competitor listings.

    Raises 404 if the product is not found or does not belong to the current user.
    """
    svc = get_listing_quality_service(db, current_user)
    try:
        result = svc.get_listing_comparison(product_id)
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


@router.get("/trends/{match_id}")
def get_listing_trends(
    match_id: int,
    days: int = Query(60, ge=1, le=365, description="Number of days to analyse"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get historical listing quality trend data for a specific competitor match.

    - **match_id**: ID of the competitor match to analyse.
    - **days**: Look-back window in days (default: 60, range: 1–365).

    Returns a time-series showing how listing quality scores have evolved,
    making it easy to detect when competitors improved or degraded their
    content and correlate changes with rank or sales performance.

    Raises 404 if the match is not found or does not belong to the current user.
    """
    svc = get_listing_quality_service(db, current_user)
    try:
        result = svc.get_listing_trends(match_id, days)
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
