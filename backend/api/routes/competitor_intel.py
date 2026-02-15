"""
Competitor Intelligence API Routes
Advanced competitor analysis and profiling
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.competitor_intel_service import get_competitor_intel_service

router = APIRouter(prefix="/competitor-intel", tags=["Competitor Intelligence"])


# Pydantic Models
class CompetitorProfileResponse(BaseModel):
    competitor_name: str
    competitor_website: Optional[str]
    total_products_tracked: int
    pricing_profile: Dict[str, Any]
    availability: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    product_sample: List[Dict[str, Any]]


class CompetitorComparisonResponse(BaseModel):
    total_competitors: int
    market_leader: Dict[str, Any]
    competitors: List[Dict[str, Any]]
    summary: Dict[str, Any]


class CrossProductComparisonResponse(BaseModel):
    product: Dict[str, Any]
    total_competitors: int
    price_range: Dict[str, Any]
    best_deals: Dict[str, Any]
    all_competitors: List[Dict[str, Any]]


# API Endpoints

@router.get("/competitors/{competitor_name}", response_model=CompetitorProfileResponse)
async def get_competitor_profile(
    competitor_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive profile for a specific competitor

    Returns:
    - Total products tracked
    - Pricing profile (cheaper/similar/expensive vs market)
    - Average price change frequency
    - Stock availability rate
    - Detected pricing strategy
    - Recent activity (last 7 days)
    - Sample products

    **Example:** `/api/competitor-intel/competitors/Amazon`
    """
    intel_service = get_competitor_intel_service(db, current_user)

    profile = intel_service.get_competitor_profile(competitor_name)

    if "error" in profile:
        raise HTTPException(status_code=404, detail=profile["error"])

    return profile


@router.get("/compare", response_model=CompetitorComparisonResponse)
async def compare_competitors(
    competitors: Optional[List[str]] = Query(
        None,
        description="List of competitor names to compare (leave empty for all)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare multiple competitors side-by-side

    If no competitor names provided, compares all tracked competitors.

    Returns:
    - Individual competitor profiles
    - Market leader identification
    - Summary (most aggressive, most reliable, most dynamic)

    **Example:** `/api/competitor-intel/compare?competitors=Amazon&competitors=Walmart`
    """
    intel_service = get_competitor_intel_service(db, current_user)

    comparison = intel_service.compare_competitors(competitors)

    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])

    return comparison


@router.get("/products/{product_id}/comparison", response_model=CrossProductComparisonResponse)
async def get_cross_product_comparison(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare all competitors for a single product

    Shows:
    - All competitor prices and availability
    - Price range (lowest, highest, average)
    - Best deals (cheapest, most reliable stock)
    - Price trends for each competitor
    - Match confidence scores

    **Use Case:** "Show me all prices for iPhone 13"
    """
    intel_service = get_competitor_intel_service(db, current_user)

    comparison = intel_service.get_cross_product_comparison(product_id)

    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])

    return comparison


@router.get("/strategies")
async def get_pricing_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect and analyze pricing strategies across all competitors

    Categorizes competitors into:
    - **Price Leaders** - Always cheapest, aggressive pricing
    - **Premium Players** - Always expensive, brand positioning
    - **Dynamic Pricers** - Frequent price changes, algorithmic pricing
    - **Market Followers** - Match market average

    Returns insights about competitive landscape.
    """
    intel_service = get_competitor_intel_service(db, current_user)

    strategies = intel_service.get_pricing_strategies()

    return strategies


@router.get("/positioning")
async def get_market_positioning(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze your overall market positioning vs competitors

    Shows:
    - How many products you're cheapest on
    - How many products you're competitive on
    - How many products you're expensive on
    - Products with no competition (opportunities)
    - Market share estimates
    - Positioning recommendations

    **Use Case:** "Am I priced too high?"
    """
    intel_service = get_competitor_intel_service(db, current_user)

    positioning = intel_service.get_market_positioning()

    if "error" in positioning:
        raise HTTPException(status_code=404, detail=positioning["error"])

    return positioning


@router.get("/insights")
async def get_competitive_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get high-level competitive intelligence insights

    Combines data from:
    - Pricing strategies
    - Market positioning
    - Competitor comparison

    Returns actionable insights and recommendations.
    """
    intel_service = get_competitor_intel_service(db, current_user)

    # Get all analysis types
    strategies = intel_service.get_pricing_strategies()
    positioning = intel_service.get_market_positioning()
    comparison = intel_service.compare_competitors()

    # Generate combined insights
    insights = {
        "executive_summary": {
            "total_competitors_tracked": comparison.get("total_competitors", 0),
            "market_leader": comparison.get("market_leader", {}),
            "your_competitive_position": positioning.get("market_share_estimate", {}),
            "key_threats": [],
            "key_opportunities": []
        },
        "detailed_analysis": {
            "pricing_strategies": strategies,
            "your_positioning": positioning,
            "competitor_comparison": comparison
        },
        "recommendations": []
    }

    # Identify threats
    if strategies.get("strategies", {}).get("price_leaders"):
        price_leaders = strategies["strategies"]["price_leaders"]
        if len(price_leaders) > 2:
            insights["executive_summary"]["key_threats"].append({
                "type": "price_competition",
                "description": f"{len(price_leaders)} competitors using aggressive pricing",
                "severity": "high"
            })

    # Identify opportunities
    if positioning.get("positioning_summary", {}).get("no_competition", 0) > 0:
        no_comp = positioning["positioning_summary"]["no_competition"]
        insights["executive_summary"]["key_opportunities"].append({
            "type": "market_gap",
            "description": f"{no_comp} products with no competition",
            "potential": "high"
        })

    # Generate recommendations
    insights["recommendations"] = positioning.get("recommendations", [])

    if strategies.get("strategies", {}).get("dynamic_pricers"):
        insights["recommendations"].append(
            "💡 Consider implementing dynamic pricing to compete with algorithmic pricers"
        )

    return insights


@router.get("/competitors")
async def list_all_competitors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a simple list of all tracked competitors

    Returns basic info about each competitor:
    - Name
    - Total products tracked
    - Last crawled timestamp

    **Use Case:** Populate a competitor dropdown selector
    """
    from database.models import CompetitorMatch, ProductMonitored
    from sqlalchemy import func

    # Get all unique competitors with product counts
    competitors = db.query(
        CompetitorMatch.competitor_name,
        func.count(CompetitorMatch.id).label('product_count'),
        func.max(CompetitorMatch.last_crawled_at).label('last_crawled')
    ).join(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).group_by(
        CompetitorMatch.competitor_name
    ).order_by(
        func.count(CompetitorMatch.id).desc()
    ).all()

    return {
        "total_competitors": len(competitors),
        "competitors": [
            {
                "name": comp[0],
                "products_tracked": comp[1],
                "last_crawled": comp[2].isoformat() if comp[2] else None
            }
            for comp in competitors
        ]
    }


@router.get("/trending")
async def get_trending_competitors(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get competitors with most activity in recent days

    Activity includes:
    - New products added
    - Price changes
    - Stock changes

    **Use Case:** "Which competitors are most active this week?"
    """
    from database.models import CompetitorMatch, ProductMonitored, PriceHistory
    from datetime import datetime, timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    intel_service = get_competitor_intel_service(db, current_user)

    # Get all competitors
    all_matches = db.query(
        CompetitorMatch.competitor_name
    ).join(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).distinct().all()

    competitor_names = [match[0] for match in all_matches]

    # Calculate activity score for each
    competitor_activity = []

    for name in competitor_names:
        activity = intel_service._get_recent_activity(name, cutoff_date)

        activity_score = len(activity)
        price_changes = len([a for a in activity if a["type"] == "price_change"])
        new_products = len([a for a in activity if a["type"] == "new_product"])

        if activity_score > 0:
            competitor_activity.append({
                "competitor_name": name,
                "total_activity": activity_score,
                "price_changes": price_changes,
                "new_products": new_products,
                "recent_activity": activity[:5]  # Top 5 activities
            })

    # Sort by activity score
    competitor_activity.sort(
        key=lambda x: x["total_activity"],
        reverse=True
    )

    return {
        "period_days": days,
        "total_competitors": len(competitor_activity),
        "trending_competitors": competitor_activity[:10]  # Top 10 most active
    }
