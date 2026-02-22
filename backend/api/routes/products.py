"""
Products API Routes

These endpoints handle all operations related to products:
- Adding new products to monitor
- Listing all products
- Getting product details
- Triggering scrapes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
import asyncio

# Import our database stuff
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, PriceHistory, CompetitorWebsite, User
from scrapers.scraper_manager import scrape_url, search_products
from api.dependencies import get_current_user, check_usage_limit

# Create a router (a mini-app for product-related endpoints)
router = APIRouter()


# Pydantic models for request/response validation
class ProductCreate(BaseModel):
    """
    Schema for creating a new product.
    This defines what data the frontend must send.
    """
    title: str
    sku: str | None = None
    brand: str | None = None
    image_url: str | None = None
    my_price: float | None = None
    description: str | None = None
    mpn: str | None = None       # Manufacturer Part Number — used for exact matching
    upc_ean: str | None = None   # UPC-12 or EAN-13 barcode — gold-standard exact match
    cost_price: float | None = None  # COGS / landed cost — enables margin calculations


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


class ProductResponse(BaseModel):
    """
    Schema for returning product data.
    This defines what data the backend sends to frontend.
    """
    id: int
    title: str
    sku: str | None
    brand: str | None
    image_url: str | None
    my_price: float | None = None
    description: str | None = None
    mpn: str | None = None
    upc_ean: str | None = None
    cost_price: float | None = None
    created_at: datetime
    competitor_count: int = 0
    # Pricing summary (populated in list endpoint)
    lowest_price: float | None = None
    avg_price: float | None = None
    in_stock_count: int = 0
    price_position: str | None = None  # 'cheapest' | 'expensive' | 'mid'
    price_change_pct: float | None = None  # % change vs 7 days ago

    class Config:
        from_attributes = True  # Allows Pydantic to work with SQLAlchemy models


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# API ENDPOINTS

@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    check_usage_limit(current_user, "products", db)

    # Create a new ProductMonitored record
    db_product = ProductMonitored(
        title=product.title,
        sku=product.sku,
        brand=product.brand,
        image_url=product.image_url,
        my_price=product.my_price,
        description=product.description,
        mpn=product.mpn,
        upc_ean=product.upc_ean,
        cost_price=product.cost_price,
        user_id=current_user.id  # Associate product with user
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)  # Get the ID that was auto-generated

    return ProductResponse(
        id=db_product.id,
        title=db_product.title,
        sku=db_product.sku,
        brand=db_product.brand,
        image_url=db_product.image_url,
        my_price=db_product.my_price,
        description=db_product.description,
        mpn=db_product.mpn,
        upc_ean=db_product.upc_ean,
        cost_price=db_product.cost_price,
        created_at=db_product.created_at,
        competitor_count=0
    )


@router.get("/", response_model=List[ProductResponse])
def get_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GET /products

    Get all monitored products for the authenticated user.
    Returns a list of products with their competitor counts.
    Requires authentication.
    """
    # Only return products that belong to the current user
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).all()

    from datetime import timedelta

    response_products = []
    for product in products:
        # Collect latest prices from all competitor matches
        latest_prices = []
        stock_statuses = []
        week_ago_prices = []

        for match in product.competitor_matches:
            latest = (
                db.query(PriceHistory)
                .filter(PriceHistory.match_id == match.id)
                .order_by(PriceHistory.timestamp.desc())
                .first()
            )
            if latest:
                if latest.price:
                    latest_prices.append(latest.price)
                stock_statuses.append(bool(latest.in_stock))

            # 7-day-old price for trend
            week_ago = (
                db.query(PriceHistory)
                .filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp <= datetime.utcnow() - timedelta(days=7),
                )
                .order_by(PriceHistory.timestamp.desc())
                .first()
            )
            if week_ago and week_ago.price:
                week_ago_prices.append(week_ago.price)

        lowest_price = min(latest_prices) if latest_prices else None
        avg_price = (sum(latest_prices) / len(latest_prices)) if latest_prices else None
        in_stock_count = sum(1 for s in stock_statuses if s)

        # Price position relative to my_price
        price_position = None
        if product.my_price and lowest_price is not None:
            if product.my_price <= lowest_price:
                price_position = "cheapest"
            elif avg_price and product.my_price > avg_price * 1.1:
                price_position = "expensive"
            else:
                price_position = "mid"

        # 7-day price change %
        price_change_pct = None
        if latest_prices and week_ago_prices:
            current_avg = sum(latest_prices) / len(latest_prices)
            old_avg = sum(week_ago_prices) / len(week_ago_prices)
            if old_avg:
                price_change_pct = round(((current_avg - old_avg) / old_avg) * 100, 1)

        response_products.append(ProductResponse(
            id=product.id,
            title=product.title,
            sku=product.sku,
            brand=product.brand,
            image_url=product.image_url,
            my_price=product.my_price,
            description=product.description,
            mpn=product.mpn,
            upc_ean=product.upc_ean,
            cost_price=product.cost_price,
            created_at=product.created_at,
            competitor_count=len(product.competitor_matches),
            lowest_price=round(lowest_price, 2) if lowest_price else None,
            avg_price=round(avg_price, 2) if avg_price else None,
            in_stock_count=in_stock_count,
            price_position=price_position,
            price_change_pct=price_change_pct,
        ))

    return response_products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GET /products/{id}

    Get a specific product by ID.
    Requires authentication. Only returns products owned by the current user.
    """
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id  # Security: only show user's own products
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(
        id=product.id,
        title=product.title,
        sku=product.sku,
        brand=product.brand,
        image_url=product.image_url,
        my_price=product.my_price,
        description=product.description,
        mpn=product.mpn,
        upc_ean=product.upc_ean,
        cost_price=product.cost_price,
        created_at=product.created_at,
        competitor_count=len(product.competitor_matches)
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PUT /products/{id}
    Update a product's fields (title, sku, brand, image_url, my_price).
    """
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in product_update.dict(exclude_none=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return ProductResponse(
        id=product.id,
        title=product.title,
        sku=product.sku,
        brand=product.brand,
        image_url=product.image_url,
        my_price=product.my_price,
        description=product.description,
        mpn=product.mpn,
        upc_ean=product.upc_ean,
        cost_price=product.cost_price,
        created_at=product.created_at,
        competitor_count=len(product.competitor_matches)
    )


@router.get("/{product_id}/matches", response_model=List[CompetitorMatchResponse])
def get_product_matches(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GET /products/{id}/matches

    Get all competitor matches for a product.
    Includes the latest price for each match.
    Requires authentication. Only returns matches for products owned by the current user.
    """
    # Check if product exists and belongs to current user
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all matches
    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    ).all()

    # Convert to response format with latest price snapshot
    response_matches = []
    for match in matches:
        latest = db.query(PriceHistory).filter(
            PriceHistory.match_id == match.id
        ).order_by(PriceHistory.timestamp.desc()).first()

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GET /products/{id}/price-history

    Get price history for all competitors of a product.
    Used to display the price chart.
    Requires authentication. Only returns data for products owned by the current user.
    """
    # Check if product exists and belongs to current user
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all price history records for this product's matches
    history_records = []
    for match in product.competitor_matches:
        for price_record in match.price_history:
            history_records.append(PriceHistoryResponse(
                timestamp=price_record.timestamp,
                price=price_record.price,
                currency=price_record.currency,
                in_stock=bool(price_record.in_stock),
                competitor_name=match.competitor_name,
                was_price=price_record.was_price,
                discount_pct=price_record.discount_pct,
                shipping_cost=price_record.shipping_cost,
                total_price=price_record.total_price,
                promotion_label=price_record.promotion_label,
                seller_name=price_record.seller_name,
                seller_count=price_record.seller_count,
                is_buy_box_winner=price_record.is_buy_box_winner,
                scrape_quality=price_record.scrape_quality,
            ))

    # Sort by timestamp
    history_records.sort(key=lambda x: x.timestamp)

    return history_records


@router.post("/{product_id}/scrape")
async def trigger_scrape(
    product_id: int,
    background_tasks: BackgroundTasks,
    website: str = "amazon.com",
    max_results: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    # Check if product exists and belongs to current user
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

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


@router.post("/{product_id}/scrape-url")
async def scrape_competitor_url(
    product_id: int,
    competitor_url: str,
    competitor_website_id: int | None = None,
    db: Session = Depends(get_db)
):
    """
    POST /products/{id}/scrape-url

    Scrape a specific competitor URL and link it to this product.

    Body:
    {
        "competitor_url": "https://competitor.com/product/123",
        "competitor_website_id": 1  # Optional: Use CSS selectors from registered competitor
    }
    """
    # Check if product exists
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get CSS selectors if competitor website is registered
    price_selector = None
    title_selector = None
    stock_selector = None
    image_selector = None
    competitor_name = "Custom Competitor"

    if competitor_website_id:
        comp_website = db.query(CompetitorWebsite).filter(
            CompetitorWebsite.id == competitor_website_id
        ).first()

        if comp_website:
            price_selector = comp_website.price_selector
            title_selector = comp_website.title_selector
            stock_selector = comp_website.stock_selector
            image_selector = comp_website.image_selector
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

        # Check if match already exists
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

        db.commit()

        return {
            "status": "success",
            "product_id": product_id,
            "match_id": match_id,
            "scraped_data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/{product_id}/export.csv")
def export_product_csv(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GET /products/{id}/export.csv

    Download all competitor data for a product as a CSV file.
    Includes latest snapshot (price, shipping, discount, stock, seller, ratings).
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    ).all()

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
        latest = db.query(PriceHistory).filter(
            PriceHistory.match_id == match.id
        ).order_by(PriceHistory.timestamp.desc()).first()

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


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    DELETE /products/{id}

    Delete a product and all its competitor matches.
    """
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"status": "deleted", "product_id": product_id}
