"""
Products API Routes

These endpoints handle all operations related to products:
- Adding new products to monitor
- Listing all products
- Getting product details
- Triggering scrapes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import ConfigDict, BaseModel
from datetime import datetime
import asyncio

# Import our database stuff
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, PriceHistory, CompetitorWebsite, User, MyPriceHistory
from scrapers.scraper_manager import scrape_url, search_products
from api.dependencies import ActiveWorkspace, get_current_user, get_current_workspace, check_usage_limit
from services.activity_service import log_activity
from services.enterprise_rollup_service import (
    refresh_product_rollups,
    refresh_workspace_rollups,
    refresh_workspace_seller_rollups,
)
from services.product_catalog_service import (
    fetch_latest_price_history_rows,
    get_home_catalog_summary,
    get_product_summaries,
)
from services.workspace_service import build_scope_predicate

# Create a router (a mini-app for product-related endpoints)
router = APIRouter()


# Pydantic models for request/response validation
class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    title: str
    sku: str | None = None
    brand: str | None = None
    image_url: str | None = None
    my_price: float | None = None
    description: str | None = None
    mpn: str | None = None
    upc_ean: str | None = None
    cost_price: float | None = None
    # Extended identifiers
    asin: str | None = None
    model_number: str | None = None
    keywords: str | None = None
    category: str | None = None
    # Group 1 — Pricing controls
    map_price: float | None = None
    rrp_msrp: float | None = None
    compare_at_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    target_margin_pct: float | None = None
    # Group 2 — Dimensions
    weight: float | None = None
    weight_unit: str | None = "kg"
    length: float | None = None
    width: float | None = None
    height: float | None = None
    dimension_unit: str | None = "cm"
    # Group 3 — Lifecycle / catalog
    status: str | None = "active"
    currency: str | None = "USD"
    product_url: str | None = None
    tags: list | None = None
    notes: str | None = None
    is_bundle: bool = False
    bundle_skus: list | None = None
    # Group 4 — Variants
    parent_sku: str | None = None
    variant_attributes: dict | None = None
    # Group 5 — Scraping control
    scrape_frequency: str | None = "daily"
    scrape_priority: str | None = "medium"
    track_all_variants: bool = False
    match_threshold: float | None = 60.0


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)."""
    title: str | None = None
    sku: str | None = None
    brand: str | None = None
    image_url: str | None = None
    my_price: float | None = None
    description: str | None = None
    mpn: str | None = None
    upc_ean: str | None = None
    cost_price: float | None = None
    asin: str | None = None
    model_number: str | None = None
    keywords: str | None = None
    category: str | None = None
    # Group 1 — Pricing controls
    map_price: float | None = None
    rrp_msrp: float | None = None
    compare_at_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    target_margin_pct: float | None = None
    # Group 2 — Dimensions
    weight: float | None = None
    weight_unit: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    dimension_unit: str | None = None
    # Group 3 — Lifecycle / catalog
    status: str | None = None
    currency: str | None = None
    product_url: str | None = None
    tags: list | None = None
    notes: str | None = None
    is_bundle: bool | None = None
    bundle_skus: list | None = None
    # Group 4 — Variants
    parent_sku: str | None = None
    variant_attributes: dict | None = None
    # Group 5 — Scraping control
    scrape_frequency: str | None = None
    scrape_priority: str | None = None
    track_all_variants: bool | None = None
    match_threshold: float | None = None


# Fields that can be set on both create and update — drives the DB write
_PRODUCT_WRITABLE_FIELDS = [
    "title", "sku", "brand", "image_url", "my_price", "description",
    "mpn", "upc_ean", "cost_price", "asin", "model_number", "keywords", "category",
    "map_price", "rrp_msrp", "compare_at_price", "min_price", "max_price", "target_margin_pct",
    "weight", "weight_unit", "length", "width", "height", "dimension_unit",
    "status", "currency", "product_url", "tags", "notes", "is_bundle", "bundle_skus",
    "parent_sku", "variant_attributes",
    "scrape_frequency", "scrape_priority", "track_all_variants", "match_threshold",
]


class ProductResponse(BaseModel):
    """Schema for returning product data to the frontend."""
    id: int
    title: str
    sku: str | None = None
    brand: str | None = None
    image_url: str | None = None
    my_price: float | None = None
    description: str | None = None
    mpn: str | None = None
    upc_ean: str | None = None
    cost_price: float | None = None
    asin: str | None = None
    model_number: str | None = None
    keywords: str | None = None
    category: str | None = None
    # Group 1 — Pricing controls
    map_price: float | None = None
    rrp_msrp: float | None = None
    compare_at_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    target_margin_pct: float | None = None
    # Group 2 — Dimensions
    weight: float | None = None
    weight_unit: str | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    dimension_unit: str | None = None
    # Group 3 — Lifecycle / catalog
    status: str | None = None
    currency: str | None = None
    product_url: str | None = None
    tags: list | None = None
    notes: str | None = None
    is_bundle: bool = False
    bundle_skus: list | None = None
    # Group 4 — Variants
    parent_sku: str | None = None
    variant_attributes: dict | None = None
    # Group 5 — Scraping control
    scrape_frequency: str | None = None
    scrape_priority: str | None = None
    track_all_variants: bool = False
    match_threshold: float | None = None
    # Meta
    source: str | None = None
    created_at: datetime
    competitor_count: int = 0
    # Pricing summary (populated in list endpoint)
    lowest_price: float | None = None
    avg_price: float | None = None
    in_stock_count: int = 0
    price_position: str | None = None
    price_change_pct: float | None = None

    model_config = ConfigDict(from_attributes=True)


class CompetitorMatchResponse(BaseModel):
    """Schema for competitor match data — includes all rich intelligence fields."""
    id: int
    competitor_name: str
    competitor_url: str
    competitor_product_title: str
    image_url: str | None = None
    match_score: float
    last_checked: datetime
    latest_price: float | None = None
    stock_status: str | None = None
    # Rich intelligence fields
    external_id: str | None = None
    rating: float | None = None
    review_count: int | None = None
    is_prime: bool | None = None
    fulfillment_type: str | None = None
    product_condition: str | None = None
    seller_name: str | None = None
    category: str | None = None
    variant: str | None = None
    # Match-rate identifiers
    brand: str | None = None
    description: str | None = None
    mpn: str | None = None
    upc_ean: str | None = None
    # Latest price snapshot detail
    was_price: float | None = None
    discount_pct: float | None = None
    shipping_cost: float | None = None
    total_price: float | None = None
    promotion_label: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryResponse(BaseModel):
    """Schema for price history data (for charts and trend analysis)."""
    timestamp: datetime
    price: float
    currency: str
    in_stock: bool
    competitor_name: str
    # Rich snapshot fields
    was_price: float | None = None
    discount_pct: float | None = None
    shipping_cost: float | None = None
    total_price: float | None = None
    promotion_label: str | None = None
    seller_name: str | None = None
    seller_count: int | None = None
    is_buy_box_winner: bool | None = None
    scrape_quality: str | None = None

    model_config = ConfigDict(from_attributes=True)


class HomeSummaryProduct(BaseModel):
    id: int
    title: str
    brand: str | None = None
    competitor_count: int = 0
    created_at: datetime


class HomeCatalogSummaryResponse(BaseModel):
    total_products: int
    total_matches: int
    total_competitors: int
    recent_products: List[HomeSummaryProduct]


def _get_scoped_product_or_404(
    db: Session,
    product_id: int,
    current_user: User,
    current_workspace: ActiveWorkspace,
) -> ProductMonitored:
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        build_scope_predicate(
            ProductMonitored,
            workspace_id=current_workspace.workspace_id,
            user_id=current_user.id,
        ),
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# API ENDPOINTS

@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    POST /products

    Add a new product to monitor.
    The frontend sends product details, we save it to database.
    Requires authentication. Enforces usage limits based on subscription tier.

    Example request:
    {
        "title": "Sony WH-1000XM5 Headphones",
        "brand": "Sony"
    }
    """
    # Check if user has reached their product limit
    check_usage_limit(
        current_user,
        "products",
        db,
        workspace_id=current_workspace.workspace_id,
    )

    # Build new product from all writable fields
    product_data = product.model_dump(exclude_unset=False)
    db_product = ProductMonitored(
        user_id=current_user.id,
        workspace_id=current_workspace.workspace_id,
        source="manual",
        **{f: product_data[f] for f in _PRODUCT_WRITABLE_FIELDS if f in product_data},
    )

    db.add(db_product)
    db.flush()

    # Record initial price in history if provided
    if db_product.my_price is not None:
        db.add(MyPriceHistory(
            product_id=db_product.id,
            workspace_id=current_workspace.workspace_id,
            old_price=None,
            new_price=db_product.my_price,
        ))

    refresh_product_rollups(
        db,
        product_id=db_product.id,
        workspace_id=current_workspace.workspace_id,
    )
    refresh_workspace_rollups(db, workspace_id=current_workspace.workspace_id)

    log_activity(db, current_user.id, "product.create", "product",
                 f"Added product '{db_product.title}' to monitoring",
                 entity_type="product", entity_id=db_product.id, entity_name=db_product.title,
                 metadata={"sku": db_product.sku, "brand": db_product.brand, "my_price": db_product.my_price},
                 workspace_id=current_workspace.workspace_id)
    db.commit()
    db.refresh(db_product)  # Get the ID that was auto-generated

    return ProductResponse.model_validate(db_product)


@router.get("/", response_model=List[ProductResponse])
def get_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
    limit: int = Query(50, ge=1, le=200, description="Max products to return"),
    offset: int = Query(0, ge=0, description="Number of products to skip"),
):
    """
    GET /products

    Get monitored products for the authenticated user (paginated).
    Use `limit` and `offset` for pages; default page size is 50, max is 200.
    Requires authentication.
    """
    summaries = get_product_summaries(
        db,
        user_id=current_user.id,
        workspace_id=current_workspace.workspace_id,
        limit=limit,
        offset=offset,
    )
    return [ProductResponse(**summary) for summary in summaries]


@router.get("/summary", response_model=HomeCatalogSummaryResponse)
def get_home_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/summary

    Lightweight homepage summary.
    Returns counts and a short recent-products list without loading the entire
    product catalog into the browser.
    """
    return get_home_catalog_summary(
        db,
        user_id=current_user.id,
        workspace_id=current_workspace.workspace_id,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/{id}

    Get a specific product by ID.
    Requires authentication. Only returns products owned by the current user.
    """
    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    PUT /products/{id}
    Update a product's fields (title, sku, brand, image_url, my_price).
    """
    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    # Auto-record my_price change before applying the update
    updates = product_update.model_dump(exclude_unset=True)
    old_price = product.my_price
    if 'my_price' in updates and updates['my_price'] != product.my_price:
        price_record = MyPriceHistory(
            product_id=product.id,
            workspace_id=current_workspace.workspace_id,
            old_price=product.my_price,
            new_price=updates['my_price'],
        )
        db.add(price_record)

    for field, value in updates.items():
        if field in _PRODUCT_WRITABLE_FIELDS:
            setattr(product, field, value)

    # Log price change separately if my_price was updated
    if 'my_price' in updates and updates['my_price'] != old_price:
        new_p = updates['my_price']
        pct = round((new_p - old_price) / old_price * 100, 1) if old_price else None
        direction = "raised" if new_p > (old_price or 0) else "lowered"
        desc = f"Price {direction} from ${old_price:.2f} to ${new_p:.2f}" if old_price else f"Price set to ${new_p:.2f}"
        if pct is not None:
            desc += f" ({'+' if pct > 0 else ''}{pct}%)"
        log_activity(db, current_user.id, "price.update", "price", desc,
                     entity_type="product", entity_id=product.id, entity_name=product.title,
                     metadata={"old_price": old_price, "new_price": new_p, "change_pct": pct},
                     workspace_id=current_workspace.workspace_id)
    elif updates:
        changed = [k for k in updates if k != 'my_price']
        if changed:
            log_activity(db, current_user.id, "product.update", "product",
                         f"Updated product '{product.title}'",
                         entity_type="product", entity_id=product.id, entity_name=product.title,
                         metadata={"fields_changed": changed},
                         workspace_id=current_workspace.workspace_id)

    refresh_product_rollups(
        db,
        product_id=product.id,
        workspace_id=current_workspace.workspace_id,
    )
    refresh_workspace_rollups(db, workspace_id=current_workspace.workspace_id)

    db.commit()
    db.refresh(product)

    return ProductResponse.model_validate(product)


@router.get("/{product_id}/matches", response_model=List[CompetitorMatchResponse])
def get_product_matches(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/{id}/matches

    Get all competitor matches for a product.
    Includes the latest price for each match.
    Requires authentication. Only returns matches for products owned by the current user.
    """
    _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    # Get all matches
    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    ).all()
    latest_rows = fetch_latest_price_history_rows(db, [match.id for match in matches])

    # Convert to response format with latest price snapshot
    response_matches = []
    for match in matches:
        latest = latest_rows.get(match.id)

        response_matches.append(CompetitorMatchResponse(
            id=match.id,
            competitor_name=match.competitor_name,
            competitor_url=match.competitor_url,
            competitor_product_title=match.competitor_product_title or '',
            image_url=match.image_url,
            match_score=match.match_score or 0.0,
            last_checked=match.last_scraped_at,
            latest_price=match.latest_price,
            stock_status=match.stock_status,
            external_id=match.external_id,
            rating=match.rating,
            review_count=match.review_count,
            is_prime=match.is_prime,
            fulfillment_type=match.fulfillment_type,
            product_condition=match.product_condition,
            seller_name=match.seller_name,
            category=match.category,
            variant=match.variant,
            brand=match.brand,
            description=match.description,
            mpn=match.mpn,
            upc_ean=match.upc_ean,
            was_price=latest.was_price if latest else None,
            discount_pct=latest.discount_pct if latest else None,
            shipping_cost=latest.shipping_cost if latest else None,
            total_price=latest.total_price if latest else None,
            promotion_label=latest.promotion_label if latest else None,
        ))

    return response_matches


@router.get("/{product_id}/price-history", response_model=List[PriceHistoryResponse])
def get_price_history(
    product_id: int,
    days: int = 90,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/{id}/price-history?days=90&limit=500

    Returns price history for a product's competitors, bounded by recency and row count.
    Default: last 90 days, max 500 rows (prevents unbounded response on long-tracked products).
    """
    from datetime import datetime, timedelta
    _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    since = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    history_rows = db.query(
        PriceHistory,
        CompetitorMatch.competitor_name,
    ).join(
        CompetitorMatch,
        PriceHistory.match_id == CompetitorMatch.id,
    ).filter(
        CompetitorMatch.monitored_product_id == product_id,
        PriceHistory.timestamp >= since,
    ).order_by(
        PriceHistory.timestamp.asc()
    ).limit(max(1, min(limit, 2000))).all()

    return [
        PriceHistoryResponse(
            timestamp=price_record.timestamp,
            price=price_record.price,
            currency=price_record.currency,
            in_stock=bool(price_record.in_stock),
            competitor_name=competitor_name,
            was_price=price_record.was_price,
            discount_pct=price_record.discount_pct,
            shipping_cost=price_record.shipping_cost,
            total_price=price_record.total_price,
            promotion_label=price_record.promotion_label,
            seller_name=price_record.seller_name,
            seller_count=price_record.seller_count,
            is_buy_box_winner=price_record.is_buy_box_winner,
            scrape_quality=price_record.scrape_quality,
        )
        for price_record, competitor_name in history_rows
    ]


@router.post("/{product_id}/scrape")
async def trigger_scrape(
    product_id: int,
    background_tasks: BackgroundTasks,
    website: str = "amazon.com",
    max_results: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    POST /products/{id}/scrape

    Manually trigger a scrape for this product.
    This will search for the product on specified competitors and update matches.
    Requires authentication. Only allows scraping products owned by the current user.

    Query params:
    - website: Which site to search (default: amazon.com)
    - max_results: Max products to find (default: 5)
    """
    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    # Search for the product on the specified website
    try:
        search_results = await search_products(product.title, website, max_results)

        if isinstance(search_results, dict) and search_results.get('error'):
            return {
                "status": "error",
                "product_id": product_id,
                "error": search_results['error']
            }

        # Save each result as a competitor match
        matches_created = 0
        for result in search_results:
            if not result.get('url'):
                continue

            # Check if match already exists
            existing = db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id,
                CompetitorMatch.competitor_url == result['url']
            ).first()

            new_price = result.get('price')
            stock = result.get('in_stock', True)
            stock_status = 'In Stock' if stock else 'Out of Stock'

            if existing:
                # Update existing match with latest data
                existing.competitor_product_title = result.get('title', '') or existing.competitor_product_title
                existing.image_url = result.get('image_url') or existing.image_url
                existing.last_scraped_at = datetime.utcnow()
                existing.latest_price = new_price if new_price is not None else existing.latest_price
                existing.stock_status = stock_status
                # Update rich fields if present
                if result.get('asin') or result.get('external_id'):
                    existing.external_id = result.get('asin') or result.get('external_id')
                if result.get('rating') is not None:
                    existing.rating = result['rating']
                if result.get('review_count') is not None:
                    existing.review_count = result['review_count']
                if result.get('is_prime') is not None:
                    existing.is_prime = result['is_prime']
                if result.get('fulfillment_type'):
                    existing.fulfillment_type = result['fulfillment_type']
                if result.get('product_condition'):
                    existing.product_condition = result['product_condition']
                if result.get('seller_name'):
                    existing.seller_name = result['seller_name']
                if result.get('category'):
                    existing.category = result['category']
                if result.get('variant'):
                    existing.variant = result['variant']
                if result.get('brand'):
                    existing.brand = result['brand']
                if result.get('description'):
                    existing.description = result['description']
                if result.get('mpn'):
                    existing.mpn = result['mpn']
                if result.get('upc_ean'):
                    existing.upc_ean = result['upc_ean']
                match_id = existing.id
            else:
                # Create new match
                new_match = CompetitorMatch(
                    monitored_product_id=product_id,
                    workspace_id=current_workspace.workspace_id,
                    competitor_name=website.split('.')[0].capitalize(),
                    competitor_url=result['url'],
                    competitor_product_title=result.get('title', ''),
                    image_url=result.get('image_url'),
                    match_score=85.0,
                    latest_price=new_price,
                    stock_status=stock_status,
                    last_scraped_at=datetime.utcnow(),
                    external_id=result.get('asin') or result.get('external_id'),
                    rating=result.get('rating'),
                    review_count=result.get('review_count'),
                    is_prime=result.get('is_prime'),
                    fulfillment_type=result.get('fulfillment_type'),
                    product_condition=result.get('product_condition', 'New'),
                    seller_name=result.get('seller_name'),
                    category=result.get('category'),
                    variant=result.get('variant'),
                    brand=result.get('brand'),
                    description=result.get('description'),
                    mpn=result.get('mpn'),
                    upc_ean=result.get('upc_ean'),
                )
                db.add(new_match)
                db.flush()
                match_id = new_match.id
                matches_created += 1

            # Save rich price history snapshot
            if new_price is not None:
                price_record = PriceHistory(
                    match_id=match_id,
                    workspace_id=current_workspace.workspace_id,
                    price=new_price,
                    currency=result.get('currency', 'USD'),
                    in_stock=stock,
                    was_price=result.get('was_price'),
                    discount_pct=result.get('discount_pct'),
                    shipping_cost=result.get('shipping_cost'),
                    total_price=result.get('total_price'),
                    promotion_label=result.get('promotion_label'),
                    seller_name=result.get('seller_name'),
                    seller_count=result.get('seller_count'),
                    is_buy_box_winner=result.get('is_buy_box_winner'),
                    scrape_quality=result.get('scrape_quality', 'clean'),
                )
                db.add(price_record)

        log_activity(db, current_user.id, "product.scrape", "competitor",
                     f"Scraped {website} for '{product.title}' — {matches_created} new match{'es' if matches_created != 1 else ''} found",
                     entity_type="product", entity_id=product_id, entity_name=product.title,
                     metadata={"website": website, "matches_found": len(search_results), "matches_created": matches_created},
                     workspace_id=current_workspace.workspace_id)
        refresh_product_rollups(
            db,
            product_id=product.id,
            workspace_id=current_workspace.workspace_id,
        )
        refresh_workspace_seller_rollups(db, workspace_id=current_workspace.workspace_id)
        refresh_workspace_rollups(db, workspace_id=current_workspace.workspace_id)
        db.commit()

        return {
            "status": "success",
            "product_id": product_id,
            "website": website,
            "matches_found": len(search_results),
            "matches_created": matches_created,
            "results": search_results
        }

    except Exception as e:
        return {
            "status": "error",
            "product_id": product_id,
            "error": str(e)
        }


class ScrapeUrlBody(BaseModel):
    competitor_url: str
    competitor_name: str | None = None
    competitor_website_id: int | None = None


@router.post("/{product_id}/scrape-url")
async def scrape_competitor_url(
    product_id: int,
    body: ScrapeUrlBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    POST /products/{id}/scrape-url

    Scrape a specific competitor URL and link it to this product.
    User-pinned matches are always assigned match_score=100.

    Body:
    {
        "competitor_url": "https://competitor.com/product/123",
        "competitor_name": "My Competitor",   // optional
        "competitor_website_id": 1            // optional: use stored CSS selectors
    }
    """
    competitor_url = body.competitor_url.strip()
    if not competitor_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="competitor_url must be a full URL starting with http:// or https://")

    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    # Derive competitor name from URL hostname as a fallback
    from urllib.parse import urlparse
    parsed_host = urlparse(competitor_url).hostname or "competitor"
    parsed_host = parsed_host.replace("www.", "")

    # Get CSS selectors if competitor website is registered
    price_selector = None
    title_selector = None
    stock_selector = None
    image_selector = None
    competitor_name = body.competitor_name.strip() if body.competitor_name and body.competitor_name.strip() else parsed_host.split(".")[0].capitalize()

    if body.competitor_website_id:
        comp_website = db.query(CompetitorWebsite).filter(
            CompetitorWebsite.id == body.competitor_website_id
        ).first()

        if comp_website:
            price_selector = comp_website.price_selector
            title_selector = comp_website.title_selector
            stock_selector = comp_website.stock_selector
            image_selector = comp_website.image_selector
            if not (body.competitor_name and body.competitor_name.strip()):
                competitor_name = comp_website.name

    # Scrape the URL
    try:
        result = await scrape_url(
            competitor_url,
            price_selector,
            title_selector,
            stock_selector,
            image_selector
        )

        if result.get('error'):
            return {
                "status": "error",
                "error": result['error'],
                "result": result
            }

        # Check if this URL is already matched to this product
        existing = db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id,
            CompetitorMatch.competitor_url == competitor_url
        ).first()

        scrape_price = result.get('price')
        scrape_stock = result.get('in_stock', True)

        if existing:
            existing.competitor_product_title = result.get('title', '') or existing.competitor_product_title
            existing.image_url = result.get('image_url') or existing.image_url
            existing.last_scraped_at = datetime.utcnow()
            existing.latest_price = scrape_price if scrape_price is not None else existing.latest_price
            existing.stock_status = 'In Stock' if scrape_stock else 'Out of Stock'
            if result.get('asin') or result.get('external_id'):
                existing.external_id = result.get('asin') or result.get('external_id')
            if result.get('rating') is not None: existing.rating = result['rating']
            if result.get('review_count') is not None: existing.review_count = result['review_count']
            if result.get('is_prime') is not None: existing.is_prime = result['is_prime']
            if result.get('fulfillment_type'): existing.fulfillment_type = result['fulfillment_type']
            if result.get('product_condition'): existing.product_condition = result['product_condition']
            if result.get('seller_name'): existing.seller_name = result['seller_name']
            if result.get('category'): existing.category = result['category']
            if result.get('variant'): existing.variant = result['variant']
            if result.get('brand'): existing.brand = result['brand']
            if result.get('description'): existing.description = result['description']
            if result.get('mpn'): existing.mpn = result['mpn']
            if result.get('upc_ean'): existing.upc_ean = result['upc_ean']
            match_id = existing.id
        else:
            new_match = CompetitorMatch(
                monitored_product_id=product_id,
                workspace_id=current_workspace.workspace_id,
                competitor_name=competitor_name,
                competitor_url=competitor_url,
                competitor_product_title=result.get('title', ''),
                image_url=result.get('image_url'),
                match_score=100.0,
                latest_price=scrape_price,
                stock_status='In Stock' if scrape_stock else 'Out of Stock',
                last_scraped_at=datetime.utcnow(),
                external_id=result.get('asin') or result.get('external_id'),
                rating=result.get('rating'),
                review_count=result.get('review_count'),
                is_prime=result.get('is_prime'),
                fulfillment_type=result.get('fulfillment_type'),
                product_condition=result.get('product_condition', 'New'),
                seller_name=result.get('seller_name'),
                category=result.get('category'),
                variant=result.get('variant'),
                brand=result.get('brand'),
                description=result.get('description'),
                mpn=result.get('mpn'),
                upc_ean=result.get('upc_ean'),
            )
            db.add(new_match)
            db.flush()
            match_id = new_match.id

        if scrape_price is not None:
            price_record = PriceHistory(
                match_id=match_id,
                workspace_id=current_workspace.workspace_id,
                price=scrape_price,
                currency=result.get('currency', 'USD'),
                in_stock=scrape_stock,
                was_price=result.get('was_price'),
                discount_pct=result.get('discount_pct'),
                shipping_cost=result.get('shipping_cost'),
                total_price=result.get('total_price'),
                promotion_label=result.get('promotion_label'),
                seller_name=result.get('seller_name'),
                seller_count=result.get('seller_count'),
                is_buy_box_winner=result.get('is_buy_box_winner'),
                scrape_quality=result.get('scrape_quality', 'clean'),
            )
            db.add(price_record)

        action_label = "competitor.update" if existing else "competitor.add"
        action_desc = f"{'Updated' if existing else 'Added'} competitor '{competitor_name}' for '{product.title}'"
        if scrape_price:
            action_desc += f" (${scrape_price:.2f})"
        refresh_product_rollups(
            db,
            product_id=product.id,
            workspace_id=current_workspace.workspace_id,
        )
        refresh_workspace_seller_rollups(db, workspace_id=current_workspace.workspace_id)
        refresh_workspace_rollups(db, workspace_id=current_workspace.workspace_id)
        log_activity(db, current_user.id, action_label, "competitor", action_desc,
                     entity_type="product", entity_id=product_id, entity_name=product.title,
                     metadata={"competitor_name": competitor_name, "url": competitor_url, "price": scrape_price},
                     workspace_id=current_workspace.workspace_id)
        db.commit()
        db.refresh(existing if existing else new_match)
        match_obj = existing if existing else new_match

        return {
            "status": "success",
            "product_id": product_id,
            "match_id": match_id,
            "is_update": existing is not None,
            "match": {
                "id": match_obj.id,
                "competitor_name": match_obj.competitor_name,
                "competitor_url": match_obj.competitor_url,
                "competitor_product_title": match_obj.competitor_product_title,
                "image_url": match_obj.image_url,
                "match_score": match_obj.match_score,
                "latest_price": match_obj.latest_price,
                "stock_status": match_obj.stock_status,
                "last_checked": match_obj.last_scraped_at.isoformat() if match_obj.last_scraped_at else None,
                "rating": match_obj.rating,
                "review_count": match_obj.review_count,
                "is_prime": match_obj.is_prime,
                "fulfillment_type": match_obj.fulfillment_type,
                "product_condition": match_obj.product_condition,
                "seller_name": match_obj.seller_name,
                "category": match_obj.category,
                "variant": match_obj.variant,
                "brand": match_obj.brand,
                "was_price": result.get("was_price"),
                "discount_pct": result.get("discount_pct"),
                "shipping_cost": result.get("shipping_cost"),
                "total_price": result.get("total_price"),
                "promotion_label": result.get("promotion_label"),
                "scrape_quality": result.get("scrape_quality"),
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/{product_id}/my-price-history")
def get_my_price_history(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/{id}/my-price-history

    Returns the log of MY OWN price changes for this product.
    Recorded automatically every time my_price is updated.
    """
    _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    records = (
        db.query(MyPriceHistory)
        .filter(MyPriceHistory.product_id == product_id)
        .order_by(MyPriceHistory.changed_at.asc())
        .all()
    )

    return [
        {
            "id": r.id,
            "old_price": r.old_price,
            "new_price": r.new_price,
            "change": round(r.new_price - r.old_price, 2) if r.old_price else None,
            "change_pct": round((r.new_price - r.old_price) / r.old_price * 100, 1) if r.old_price else None,
            "note": r.note,
            "changed_at": r.changed_at.isoformat(),
        }
        for r in records
    ]


@router.get("/{product_id}/export.csv")
def export_product_csv(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/{id}/export.csv

    Download all competitor data for a product as a CSV file.
    Includes latest snapshot (price, shipping, discount, stock, seller, ratings).
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    ).all()
    latest_rows = fetch_latest_price_history_rows(db, [match.id for match in matches])

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Competitor", "Product Title", "URL",
        "Match Score (%)", "Price", "Was Price", "Discount (%)",
        "Shipping", "Total Price", "In Stock", "Stock Status",
        "Fulfillment", "Seller", "Rating", "Reviews",
        "Prime", "Condition", "Category", "Variant",
        "Brand", "MPN", "UPC/EAN",
        "Promotion", "Last Checked",
        # My product fields for context
        "My Price", "Cost Price",
        "Margin at My Price (%)", "Margin if Matched (%)"
    ])

    for match in matches:
        latest = latest_rows.get(match.id)

        price = match.latest_price
        shipping = latest.shipping_cost if latest else None
        total = latest.total_price if latest else price
        was_price = latest.was_price if latest else None
        discount_pct = latest.discount_pct if latest else None
        promotion = latest.promotion_label if latest else None

        # Margin calculations
        margin_at_my_price = None
        margin_if_matched = None
        if product.cost_price:
            if product.my_price and product.my_price > 0:
                margin_at_my_price = round((product.my_price - product.cost_price) / product.my_price * 100, 1)
            if price and price > 0:
                margin_if_matched = round((price - product.cost_price) / price * 100, 1)

        writer.writerow([
            match.competitor_name,
            match.competitor_product_title or '',
            match.competitor_url,
            f"{match.match_score:.0f}" if match.match_score else '',
            f"{price:.2f}" if price else '',
            f"{was_price:.2f}" if was_price else '',
            f"{discount_pct:.1f}" if discount_pct else '',
            f"{shipping:.2f}" if shipping is not None else '',
            f"{total:.2f}" if total else '',
            'Yes' if (latest and latest.in_stock) else 'No',
            match.stock_status or '',
            match.fulfillment_type or '',
            match.seller_name or '',
            f"{match.rating:.1f}" if match.rating else '',
            match.review_count or '',
            'Yes' if match.is_prime else ('No' if match.is_prime is False else ''),
            match.product_condition or '',
            match.category or '',
            match.variant or '',
            match.brand or '',
            match.mpn or '',
            match.upc_ean or '',
            promotion or '',
            match.last_scraped_at.strftime('%Y-%m-%d %H:%M') if match.last_scraped_at else '',
            f"{product.my_price:.2f}" if product.my_price else '',
            f"{product.cost_price:.2f}" if product.cost_price else '',
            f"{margin_at_my_price}" if margin_at_my_price is not None else '',
            f"{margin_if_matched}" if margin_if_matched is not None else '',
        ])

    output.seek(0)
    filename = f"marketintel_{product.title[:30].replace(' ', '_')}_{product_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{product_id}/export.xlsx")
def export_product_xlsx(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    GET /products/{id}/export.xlsx

    Download all competitor data for a product as an Excel (.xlsx) file.
    Uses a stdlib-only XLSX writer — no openpyxl required.
    """
    from fastapi.responses import Response
    from services.xlsx_writer import write_xlsx

    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    ).all()
    latest_rows = fetch_latest_price_history_rows(db, [match.id for match in matches])

    headers = [
        "Competitor", "Product Title", "URL",
        "Match Score (%)", "Price", "Was Price", "Discount (%)",
        "Shipping", "Total Price", "In Stock", "Stock Status",
        "Fulfillment", "Seller", "Rating", "Reviews",
        "Prime", "Condition", "Category", "Variant",
        "Brand", "MPN", "UPC/EAN",
        "Promotion", "Last Checked",
        "My Price", "Cost Price",
        "Margin at My Price (%)", "Margin if Matched (%)",
    ]

    rows = []
    for match in matches:
        latest = latest_rows.get(match.id)

        price = match.latest_price
        shipping = latest.shipping_cost if latest else None
        total = latest.total_price if latest else price
        was_price = latest.was_price if latest else None
        discount_pct = latest.discount_pct if latest else None
        promotion = latest.promotion_label if latest else None

        margin_at_my_price = None
        margin_if_matched = None
        if product.cost_price:
            if product.my_price and product.my_price > 0:
                margin_at_my_price = round((product.my_price - product.cost_price) / product.my_price * 100, 1)
            if price and price > 0:
                margin_if_matched = round((price - product.cost_price) / price * 100, 1)

        rows.append([
            match.competitor_name,
            match.competitor_product_title or '',
            match.competitor_url,
            round(match.match_score) if match.match_score else '',
            round(price, 2) if price else '',
            round(was_price, 2) if was_price else '',
            round(discount_pct, 1) if discount_pct else '',
            round(shipping, 2) if shipping is not None else '',
            round(total, 2) if total else '',
            'Yes' if (latest and latest.in_stock) else 'No',
            match.stock_status or '',
            match.fulfillment_type or '',
            match.seller_name or '',
            round(match.rating, 1) if match.rating else '',
            match.review_count or '',
            'Yes' if match.is_prime else ('No' if match.is_prime is False else ''),
            match.product_condition or '',
            match.category or '',
            match.variant or '',
            match.brand or '',
            match.mpn or '',
            match.upc_ean or '',
            promotion or '',
            match.last_scraped_at.strftime('%Y-%m-%d %H:%M') if match.last_scraped_at else '',
            round(product.my_price, 2) if product.my_price else '',
            round(product.cost_price, 2) if product.cost_price else '',
            margin_at_my_price if margin_at_my_price is not None else '',
            margin_if_matched if margin_if_matched is not None else '',
        ])

    xlsx_bytes = write_xlsx(product.title[:31], headers, rows)
    safe_title = product.title[:30].replace(' ', '_')
    filename = f"marketintel_{safe_title}_{product_id}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: ActiveWorkspace = Depends(get_current_workspace),
):
    """
    DELETE /products/{id}

    Delete a product and all its competitor matches.
    """
    product = _get_scoped_product_or_404(db, product_id, current_user, current_workspace)

    title = product.title
    match_count = len(product.competitor_matches)
    db.delete(product)
    db.flush()
    refresh_workspace_seller_rollups(db, workspace_id=current_workspace.workspace_id)
    refresh_workspace_rollups(db, workspace_id=current_workspace.workspace_id)
    log_activity(db, current_user.id, "product.delete", "product",
                 f"Deleted product '{title}' and {match_count} competitor match{'es' if match_count != 1 else ''}",
                 entity_type="product", entity_id=product_id, entity_name=title,
                 metadata={"matches_removed": match_count},
                 workspace_id=current_workspace.workspace_id)
    db.commit()

    return {"status": "deleted", "product_id": product_id}
