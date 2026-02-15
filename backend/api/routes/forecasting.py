"""
Forecasting & Historical Analysis API Routes
Time-series analysis and price predictions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.forecasting_service import get_forecasting_service

router = APIRouter(prefix="/forecasting", tags=["Forecasting & Analytics"])


# Pydantic Models
class PriceHistoryAnalysisResponse(BaseModel):
    product: Dict[str, Any]
    period_days: int
    statistics: Dict[str, Any]
    trend: Dict[str, Any]
    best_buying_times: List[Dict[str, Any]]
    competitor_histories: Dict[str, List[Dict[str, Any]]]
    total_data_points: int


class ForecastResponse(BaseModel):
    product: Dict[str, Any]
    forecast_days: int
    current_price: float
    predicted_price: float
    price_change: float
    price_change_pct: float
    trend_direction: str
    confidence: Dict[str, Any]
    forecast_points: List[Dict[str, Any]]
    methodology: str
    data_points_used: int


class SeasonalPatternsResponse(BaseModel):
    product: Dict[str, Any]
    analysis_period_months: int
    day_of_week_patterns: Dict[str, Dict[str, Any]]
    monthly_patterns: Dict[str, Dict[str, Any]]
    recommendations: Dict[str, Optional[str]]


# API Endpoints

@router.get("/products/{product_id}/history", response_model=PriceHistoryAnalysisResponse)
async def get_price_history_analysis(
    product_id: int,
    days: int = Query(90, ge=7, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze historical price data for a product

    Returns comprehensive analysis including:
    - Time series data for all competitors
    - Price statistics (min, max, avg, median, std dev)
    - Volatility analysis
    - Trend detection (increasing/decreasing/stable)
    - Best buying times (historically lowest periods)

    **Use Case:** "Show me price history for the last 90 days"

    **Example:** `/api/forecasting/products/123/history?days=90`
    """
    forecasting_service = get_forecasting_service(db, current_user)

    analysis = forecasting_service.get_price_history_analysis(product_id, days)

    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])

    return analysis


@router.get("/products/{product_id}/forecast", response_model=ForecastResponse)
async def forecast_price(
    product_id: int,
    days_ahead: int = Query(
        30,
        ge=1,
        le=90,
        description="Number of days to forecast"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Forecast future prices using historical data

    Uses simple linear regression for MVP (can be upgraded to ARIMA, Prophet, LSTM).

    Returns:
    - Predicted price
    - Expected price change (amount and percentage)
    - Trend direction
    - Confidence intervals
    - Forecast points for charting

    **Use Case:** "Will the price go up or down next month?"

    **Example:** `/api/forecasting/products/123/forecast?days_ahead=30`

    **Note:** Requires at least 10 historical data points for accurate forecasting.
    """
    forecasting_service = get_forecasting_service(db, current_user)

    forecast = forecasting_service.forecast_price(product_id, days_ahead)

    if "error" in forecast:
        raise HTTPException(status_code=404, detail=forecast["error"])

    return forecast


@router.get("/products/{product_id}/seasonal", response_model=SeasonalPatternsResponse)
async def get_seasonal_patterns(
    product_id: int,
    months: int = Query(
        12,
        ge=3,
        le=24,
        description="Number of months to analyze"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect seasonal pricing patterns

    Analyzes:
    - Day of week patterns (weekday vs weekend pricing)
    - Monthly patterns (seasonal trends)
    - Best day/month to buy recommendations

    **Use Case:** "When is the best time to buy this product?"

    **Example:** `/api/forecasting/products/123/seasonal?months=12`

    **Insights:**
    - Electronics often drop on Black Friday (November)
    - Retail may have weekend discounts
    - Back-to-school items cheaper in July
    """
    forecasting_service = get_forecasting_service(db, current_user)

    patterns = forecasting_service.get_seasonal_patterns(product_id, months)

    if "error" in patterns:
        raise HTTPException(status_code=404, detail=patterns["error"])

    return patterns


@router.get("/competitors/{competitor_name}/performance")
async def compare_historical_performance(
    competitor_name: str,
    days: int = Query(90, ge=7, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze a competitor's historical pricing performance

    Returns:
    - Win rate (how often they had lowest price)
    - Average price volatility
    - Price change frequency
    - Product-by-product performance breakdown

    **Use Case:** "How often does Amazon have the lowest price?"

    **Example:** `/api/forecasting/competitors/Amazon/performance?days=90`
    """
    forecasting_service = get_forecasting_service(db, current_user)

    performance = forecasting_service.compare_historical_performance(
        competitor_name,
        days
    )

    if "error" in performance:
        raise HTTPException(status_code=404, detail=performance["error"])

    return performance


@router.get("/price-drops")
async def get_price_drop_alerts(
    days: int = Query(30, ge=1, le=90, description="Look back period"),
    min_drop_pct: float = Query(
        10.0,
        ge=1.0,
        le=100.0,
        description="Minimum drop percentage to report"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Find significant price drops across all products

    Useful for:
    - Identifying buying opportunities
    - Detecting competitor sales/promotions
    - Triggering automated price matching

    Returns products where price dropped by at least min_drop_pct.

    **Use Case:** "Show me all products with 20%+ price drops this month"

    **Example:** `/api/forecasting/price-drops?days=30&min_drop_pct=20`
    """
    forecasting_service = get_forecasting_service(db, current_user)

    drops = forecasting_service.get_price_drop_alerts(days, min_drop_pct)

    return drops


@router.get("/trends/summary")
async def get_trends_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get high-level trends summary across all products

    Aggregates:
    - Overall market trend (prices going up or down)
    - Most volatile products
    - Products with best forecasts (predicted drops)
    - Recent significant price changes

    **Use Case:** Executive dashboard showing market trends

    **Example:** `/api/forecasting/trends/summary`
    """
    from database.models import ProductMonitored

    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).limit(100).all()  # Limit to first 100 for performance

    forecasting_service = get_forecasting_service(db, current_user)

    trends = {
        "increasing": 0,
        "decreasing": 0,
        "stable": 0
    }

    high_volatility_products = []
    predicted_drops = []

    for product in products:
        # Get trend
        analysis = forecasting_service.get_price_history_analysis(product.id, 30)

        if "trend" in analysis:
            direction = analysis["trend"]["direction"]
            trends[direction] = trends.get(direction, 0) + 1

            # Track high volatility
            if "statistics" in analysis and analysis["statistics"].get("volatility") == "High":
                high_volatility_products.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "volatility": analysis["statistics"]["volatility"]
                })

        # Get forecast
        forecast = forecasting_service.forecast_price(product.id, 30)

        if "price_change_pct" in forecast and forecast["price_change_pct"] < -5:
            predicted_drops.append({
                "product_id": product.id,
                "product_title": product.title,
                "predicted_drop_pct": forecast["price_change_pct"]
            })

    # Sort predicted drops by magnitude
    predicted_drops.sort(key=lambda x: x["predicted_drop_pct"])

    return {
        "total_products_analyzed": len(products),
        "trend_distribution": trends,
        "high_volatility_products": high_volatility_products[:10],
        "predicted_price_drops": predicted_drops[:10],
        "summary": {
            "market_trend": max(trends, key=trends.get),
            "volatile_products_count": len(high_volatility_products),
            "predicted_drops_count": len(predicted_drops)
        }
    }


@router.get("/insights/best-time-to-buy")
async def get_best_time_to_buy_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated insights on best times to buy across all products

    Analyzes seasonal patterns across entire catalog to answer:
    - What day of the week has lowest prices on average?
    - What month has lowest prices on average?
    - Are there any consistent patterns?

    **Use Case:** "When should I generally expect the best deals?"

    **Example:** `/api/forecasting/insights/best-time-to-buy`
    """
    from database.models import ProductMonitored
    from collections import defaultdict

    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).limit(50).all()  # Sample first 50 products

    forecasting_service = get_forecasting_service(db, current_user)

    # Aggregate day of week recommendations
    day_recommendations = defaultdict(int)
    month_recommendations = defaultdict(int)

    for product in products:
        patterns = forecasting_service.get_seasonal_patterns(product.id, 12)

        if "recommendations" in patterns:
            best_day = patterns["recommendations"].get("best_day_to_buy")
            best_month = patterns["recommendations"].get("best_month_to_buy")

            if best_day:
                day_recommendations[best_day] += 1

            if best_month:
                month_recommendations[best_month] += 1

    # Find most common recommendations
    best_day = max(
        day_recommendations.items(),
        key=lambda x: x[1]
    )[0] if day_recommendations else None

    best_month = max(
        month_recommendations.items(),
        key=lambda x: x[1]
    )[0] if month_recommendations else None

    return {
        "products_analyzed": len(products),
        "overall_recommendations": {
            "best_day_to_buy": best_day,
            "best_month_to_buy": best_month
        },
        "day_distribution": dict(day_recommendations),
        "month_distribution": dict(month_recommendations),
        "insights": [
            f"Most products have lowest prices on {best_day}" if best_day else None,
            f"Prices tend to be lowest in {best_month}" if best_month else None,
            "Patterns detected across your catalog"
        ]
    }
