"""
Seller Intelligence API Routes
Third-party seller analysis, Amazon 1P threat detection, and Buy Box volatility
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.seller_intel_service import get_seller_intel_service

router = APIRouter(prefix="/seller-intel", tags=["Seller Intelligence"])


@router.get("/overview")
def get_seller_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a high-level overview of all sellers tracked across the portfolio.

    Returns aggregate seller metrics including total unique sellers, Buy Box
    win rates, Amazon 1P presence, and the top sellers by product coverage.
    """
    svc = get_seller_intel_service(db, current_user)
    try:
        return svc.get_seller_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/amazon-threats")
def get_amazon_1p_threats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Identify products where Amazon is selling as a first-party (1P) retailer.

    Returns a list of product matches where Amazon itself holds or contests
    the Buy Box, ranked by threat severity. Use this to prioritise defensive
    pricing or MAP-enforcement actions.
    """
    svc = get_seller_intel_service(db, current_user)
    try:
        return svc.get_amazon_1p_threats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sellers/{seller_name}")
def get_seller_profile(
    seller_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a detailed intelligence profile for a specific seller.

    - **seller_name**: Name of the third-party seller to profile.

    Returns the seller's product count, Buy Box win rate, pricing behaviour,
    fulfilment type (FBA/FBM), feedback rating, and recent activity.

    Raises 404 if the seller is not found in the current user's tracked data.
    """
    svc = get_seller_intel_service(db, current_user)
    try:
        result = svc.get_seller_profile(seller_name)
        if result is None or (isinstance(result, dict) and "error" in result):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Seller not found") if isinstance(result, dict) else "Seller not found",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buybox-volatility/{product_id}")
def get_buybox_volatility(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyse Buy Box ownership volatility for a specific product.

    - **product_id**: ID of the product to analyse.

    Returns the Buy Box change history, current owner, number of competing
    sellers, and a volatility score indicating how frequently ownership flips.

    Raises 404 if the product is not found or does not belong to the current user.
    """
    svc = get_seller_intel_service(db, current_user)
    try:
        result = svc.get_buybox_volatility(product_id)
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
