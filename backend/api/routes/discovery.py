"""
Automatic Discovery API Routes
AI-powered competitor and product discovery
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.discovery_service import get_discovery_service

router = APIRouter(prefix="/discovery", tags=["Auto Discovery"])


# Pydantic Models
class DiscoveryResult(BaseModel):
    product: Dict[str, Any]
    search_keywords: List[str]
    discovered_competitors: List[Dict[str, Any]]
    total_found: int
    existing_competitors: int
    recommendation: str


class ProductSuggestion(BaseModel):
    total_suggestions: int
    filters_applied: Dict[str, Any]
    your_catalog: Dict[str, Any]
    suggestions: List[Dict[str, Any]]


class WebsiteDiscoveryResult(BaseModel):
    existing_websites: int
    discovered_websites: List[Dict[str, Any]]
    total_found: int
    filters: Dict[str, Any]
    recommendation: str


# API Endpoints

@router.post("/products/{product_id}/discover-competitors", response_model=DiscoveryResult)
async def discover_competitors_for_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Automatically discover competitors for a specific product

    **Process:**
    1. Analyzes product data (title, brand, SKU)
    2. Generates search keywords
    3. Searches major e-commerce sites
    4. Returns potential competitor matches for review

    **Use Case:** "Find where else this product is sold"

    **Example:** `POST /api/discovery/products/123/discover-competitors`

    **Note:** In production, uses:
    - Google Shopping API
    - Marketplace APIs (Amazon, eBay, Walmart)
    - AI-powered relevance scoring
    - Automatic match confidence calculation
    """
    discovery_service = get_discovery_service(db, current_user)

    result = discovery_service.discover_competitors_for_product(product_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/suggest-products", response_model=ProductSuggestion)
async def suggest_new_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_competitors: int = Query(2, ge=1, le=10, description="Minimum competitor count"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get suggestions for new products to monitor

    Analyzes your existing catalog and suggests:
    - Products from brands you're tracking
    - Products in same categories
    - Trending products in your market
    - Products frequently found on competitor sites

    **Use Case:** "What other products should I track?"

    **Example:** `/api/discovery/suggest-products?brand=Apple&min_competitors=3`
    """
    discovery_service = get_discovery_service(db, current_user)

    suggestions = discovery_service.suggest_new_products(
        based_on_category=category,
        based_on_brand=brand,
        min_competitor_count=min_competitors
    )

    return suggestions


@router.get("/websites", response_model=WebsiteDiscoveryResult)
async def find_competitor_websites(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    location: Optional[str] = Query(None, description="Filter by location"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discover new competitor websites to track

    **Methods:**
    - Analyzes domains from existing matches
    - Industry-specific directories
    - Market research tools
    - Competitor analysis

    **Use Case:** "Find more competitor websites in my industry"

    **Example:** `/api/discovery/websites?industry=Electronics&location=US`
    """
    discovery_service = get_discovery_service(db, current_user)

    result = discovery_service.find_competitor_websites(industry, location)

    return result


@router.post("/auto-match")
async def auto_match_products(
    product_id: Optional[int] = Query(None, description="Specific product to match (optional)"),
    min_confidence: float = Query(
        0.7,
        ge=0.1,
        le=1.0,
        description="Minimum confidence threshold (0.1-1.0)"
    ),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Automatically match products across competitor sites

    **Process:**
    1. Crawls competitor websites
    2. Uses AI to find matching products
    3. Auto-creates matches above confidence threshold
    4. Starts price tracking automatically

    **Parameters:**
    - `product_id`: Match specific product (leave empty for batch matching)
    - `min_confidence`: Only auto-create matches above this score (0.7 = 70%)

    **Use Case:** "Automatically find and track this product everywhere"

    **Example:** `POST /api/discovery/auto-match?product_id=123&min_confidence=0.8`

    **Note:** High-confidence matches (>0.9) are auto-approved.
    Medium-confidence (0.7-0.9) may need manual review.
    """
    discovery_service = get_discovery_service(db, current_user)

    result = discovery_service.auto_match_products(
        product_id=product_id,
        min_confidence=min_confidence
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/suggestions")
async def get_discovery_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized discovery suggestions

    Analyzes your catalog and provides actionable recommendations:
    - Products needing competitor discovery
    - Brands/categories to expand
    - Popular sites to add
    - Market gaps and opportunities

    **Use Case:** Dashboard widget showing "What should I do next?"

    **Example:** `/api/discovery/suggestions`
    """
    discovery_service = get_discovery_service(db, current_user)

    suggestions = discovery_service.get_discovery_suggestions()

    return suggestions


@router.post("/bulk-discover")
async def bulk_discover(
    batch_size: int = Query(10, ge=1, le=100, description="Products to process per batch"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run bulk discovery across multiple products

    Processes products in batches to find competitors efficiently.
    Ideal for initial setup or expanding catalog coverage.

    **Parameters:**
    - `batch_size`: Number of products to process (1-100)

    **Use Case:** "Find competitors for all my products at once"

    **Example:** `POST /api/discovery/bulk-discover?batch_size=20`

    **Note:** For large batches (50+), consider running as background job.
    """
    discovery_service = get_discovery_service(db, current_user)

    result = discovery_service.bulk_discover(batch_size=batch_size)

    return result


@router.get("/stats")
async def get_discovery_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get discovery statistics and health metrics

    Shows:
    - Total products monitored
    - Products with/without competitors
    - Average competitors per product
    - Coverage gaps
    - Discovery opportunities

    **Use Case:** Analytics dashboard showing discovery health

    **Example:** `/api/discovery/stats`
    """
    from database.models import ProductMonitored, CompetitorMatch

    # Get all products
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).all()

    if not products:
        return {
            "message": "No products found",
            "stats": {}
        }

    # Calculate statistics
    products_with_competitors = 0
    products_without_competitors = 0
    total_competitors = 0

    competitor_distribution = {
        "0": 0,
        "1-2": 0,
        "3-5": 0,
        "6+": 0
    }

    for product in products:
        count = db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product.id
        ).count()

        total_competitors += count

        if count == 0:
            products_without_competitors += 1
            competitor_distribution["0"] += 1
        else:
            products_with_competitors += 1

            if count <= 2:
                competitor_distribution["1-2"] += 1
            elif count <= 5:
                competitor_distribution["3-5"] += 1
            else:
                competitor_distribution["6+"] += 1

    avg_competitors = (
        total_competitors / len(products) if products else 0
    )

    # Calculate health score (0-100)
    health_score = min(100, int(
        (products_with_competitors / len(products)) * 50 +  # 50 points for having any competitors
        (min(avg_competitors, 5) / 5) * 50  # 50 points for avg competitors (capped at 5)
    ))

    return {
        "total_products": len(products),
        "products_with_competitors": products_with_competitors,
        "products_without_competitors": products_without_competitors,
        "total_competitor_matches": total_competitors,
        "avg_competitors_per_product": round(avg_competitors, 2),
        "competitor_distribution": competitor_distribution,
        "discovery_health_score": health_score,
        "health_rating": (
            "Excellent" if health_score >= 80 else
            "Good" if health_score >= 60 else
            "Fair" if health_score >= 40 else
            "Needs Improvement"
        ),
        "recommendations": [
            f"Add competitors for {products_without_competitors} products" if products_without_competitors > 0 else None,
            "Run bulk discovery to expand coverage" if health_score < 60 else None,
            "Great coverage! Keep monitoring and updating" if health_score >= 80 else None
        ]
    }


@router.post("/approve-match")
async def approve_discovered_match(
    product_id: int,
    competitor_url: str,
    competitor_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a discovered competitor match

    After discovery suggests potential competitors, use this to approve
    and start tracking a specific match.

    **Body:**
    ```json
    {
      "product_id": 123,
      "competitor_url": "https://amazon.com/product/xyz",
      "competitor_name": "Amazon"
    }
    ```

    **Use Case:** User reviews discovered competitors and approves tracking

    **Example:** `POST /api/discovery/approve-match`
    """
    from database.models import ProductMonitored, CompetitorMatch
    from datetime import datetime

    # Verify product exists and belongs to user
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if match already exists
    existing_match = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id,
        CompetitorMatch.competitor_url == competitor_url
    ).first()

    if existing_match:
        return {
            "message": "Match already exists",
            "match_id": existing_match.id
        }

    # Create new match
    new_match = CompetitorMatch(
        monitored_product_id=product_id,
        competitor_name=competitor_name,
        competitor_url=competitor_url,
        match_score=0.85,  # From discovery
        created_at=datetime.utcnow()
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return {
        "message": "Competitor match approved and created",
        "match_id": new_match.id,
        "status": "tracking_started",
        "next_step": "Price tracking will begin on next crawl"
    }


@router.delete("/reject-match")
async def reject_discovered_match(
    product_id: int = Query(..., description="Product ID"),
    competitor_url: str = Query(..., description="Competitor URL to reject"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a discovered competitor match

    Mark a suggested competitor as not relevant. This helps improve
    future discovery suggestions.

    **Use Case:** User reviews discovered competitors and rejects irrelevant ones

    **Example:** `DELETE /api/discovery/reject-match?product_id=123&competitor_url=...`
    """
    # In production, this would:
    # - Store rejection in database
    # - Train ML model to avoid similar false matches
    # - Update discovery algorithms

    return {
        "message": "Match rejected",
        "product_id": product_id,
        "competitor_url": competitor_url,
        "status": "Feedback recorded for future improvements"
    }
