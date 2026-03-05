"""
Keyword Rank Tracking API Routes
Portfolio keyword summaries, rank movement alerts, per-product dashboards,
keyword trend series, and keyword management
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.keyword_rank_service import get_keyword_rank_service

router = APIRouter(prefix="/keyword-ranks", tags=["Keyword Rank Tracking"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AddKeywordRequest(BaseModel):
    keyword: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_portfolio_keyword_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a keyword ranking summary across the entire product portfolio.

    Returns aggregate statistics including total keywords tracked, average
    rank position, number of keywords in the top 10 / top 20 / top 50, and
    the most and least improved keywords over the last 7 days.
    """
    svc = get_keyword_rank_service(db, current_user)
    try:
        return svc.get_portfolio_keyword_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movements")
def get_rank_movements(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyse"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get significant keyword rank movements across all tracked products.

    - **days**: Look-back window in days (default: 7, range: 1–90).

    Returns keywords that have gained or lost rank positions within the
    specified period, sorted by magnitude of movement. Useful for spotting
    algorithmic shifts or the impact of listing optimisations.
    """
    svc = get_keyword_rank_service(db, current_user)
    try:
        return svc.get_rank_movements(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}")
def get_keyword_dashboard(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the full keyword ranking dashboard for a specific product.

    - **product_id**: ID of the product to retrieve keyword data for.

    Returns all tracked keywords for the product along with their current
    rank, rank delta vs the previous period, search volume estimates, and
    a performance tier classification (top-10, top-20, top-50, beyond-50).

    Raises 404 if the product is not found or does not belong to the current user.
    """
    svc = get_keyword_rank_service(db, current_user)
    try:
        result = svc.get_keyword_dashboard(product_id)
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


@router.get("/trends/{product_id}")
def get_keyword_trend(
    product_id: int,
    keyword: str = Query(..., description="Keyword to retrieve trend data for"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyse"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the historical rank trend for a single keyword on a specific product.

    - **product_id**: ID of the product.
    - **keyword**: The exact keyword string to look up.
    - **days**: Look-back window in days (default: 30, range: 1–365).

    Returns a daily time-series of rank positions, allowing you to visualise
    rank trajectory and correlate movements with price changes, review velocity,
    or listing updates.

    Raises 404 if the product or keyword is not found.
    """
    svc = get_keyword_rank_service(db, current_user)
    try:
        result = svc.get_keyword_trend(product_id, keyword, days)
        if result is None or (isinstance(result, dict) and "error" in result):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Product or keyword not found") if isinstance(result, dict) else "Product or keyword not found",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products/{product_id}/keywords")
def add_keyword(
    product_id: int,
    body: AddKeywordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new keyword to track for a specific product.

    - **product_id**: ID of the product to associate the keyword with.
    - **body.keyword**: The keyword string to begin tracking.

    The keyword will be queued for its first rank check and will appear in
    the product's keyword dashboard once initial rank data has been collected.

    Raises 404 if the product is not found or does not belong to the current user.
    """
    svc = get_keyword_rank_service(db, current_user)
    try:
        result = svc.add_keyword(product_id, body.keyword)
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
