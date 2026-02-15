"""
Insights API Routes
Provides actionable recommendations and business intelligence
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.insights_service import get_insights_service

router = APIRouter(prefix="/insights", tags=["Insights & Recommendations"])


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
    """
    insights_service = get_insights_service(db, current_user)

    try:
        insights = insights_service.get_dashboard_insights()
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.get("/priorities", response_model=List[PriorityAction])
async def get_priorities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get today's priority actions

    Returns list of actions ranked by urgency:
    - High severity: Immediate action needed
    - Medium severity: Review soon
    - Low severity: Can wait
    """
    insights_service = get_insights_service(db, current_user)

    try:
        priorities = insights_service.get_today_priorities()
        return priorities
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get priorities: {str(e)}"
        )


@router.get("/opportunities", response_model=List[Opportunity])
async def get_opportunities(
    current_user: User = Depends(get_current_user),
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
    insights_service = get_insights_service(db, current_user)

    try:
        opportunities = insights_service.get_opportunities()
        return opportunities
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get opportunities: {str(e)}"
        )


@router.get("/threats", response_model=List[Threat])
async def get_threats(
    current_user: User = Depends(get_current_user),
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
    insights_service = get_insights_service(db, current_user)

    try:
        threats = insights_service.get_threats()
        return threats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get threats: {str(e)}"
        )


@router.get("/metrics", response_model=KeyMetrics)
async def get_key_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get key performance metrics

    Returns:
    - Total products monitored
    - Total competitor matches
    - Competitive position breakdown
    - Active alerts
    - Recent price change activity
    """
    insights_service = get_insights_service(db, current_user)

    try:
        metrics = insights_service.get_key_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/trending", response_model=List[TrendingProduct])
async def get_trending_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get trending products with high activity

    Returns products with:
    - Frequent price changes
    - New competitor entries
    - High market volatility
    """
    insights_service = get_insights_service(db, current_user)

    try:
        trending = insights_service.get_trending_products()
        return trending
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending products: {str(e)}"
        )


@router.get("/opportunity-score/{product_id}", response_model=OpportunityScoreResponse)
async def get_opportunity_score(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate opportunity score for a specific product

    Score 0-100:
    - 80-100: High opportunity (take action now)
    - 50-79: Medium opportunity (monitor closely)
    - 0-49: Low opportunity (stable/competitive)

    Factors considered:
    - Price position vs competitors
    - Competition level
    - Recent price volatility
    - Competitor stock status
    """
    insights_service = get_insights_service(db, current_user)

    try:
        score = insights_service.calculate_opportunity_score(product_id)

        # Interpret score
        if score >= 80:
            interpretation = "High opportunity - Take action now!"
        elif score >= 50:
            interpretation = "Medium opportunity - Monitor closely"
        else:
            interpretation = "Low opportunity - Stable/competitive"

        return {
            "product_id": product_id,
            "score": score,
            "interpretation": interpretation
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate opportunity score: {str(e)}"
        )
