"""
Products API Routes

These endpoints handle all operations related to products:
- Adding new products to monitor
- Listing all products
- Getting product details
- Triggering scrapes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

# Import our database stuff
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, PriceHistory

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
    created_at: datetime
    competitor_count: int = 0  # Number of competitor matches

    class Config:
        from_attributes = True  # Allows Pydantic to work with SQLAlchemy models


class CompetitorMatchResponse(BaseModel):
    """
    Schema for competitor match data.
    """
    id: int
    competitor_name: str
    competitor_url: str
    competitor_title: str
    competitor_image_url: str | None
    match_score: float
    last_crawled_at: datetime
    latest_price: float | None = None
    in_stock: bool | None = None

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """
    Schema for price history data (for charts).
    """
    timestamp: datetime
    price: float
    currency: str
    in_stock: bool
    competitor_name: str

    class Config:
        from_attributes = True


# API ENDPOINTS

@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    POST /products

    Add a new product to monitor.
    The frontend sends product details, we save it to database.

    Example request:
    {
        "title": "Sony WH-1000XM5 Headphones",
        "brand": "Sony"
    }
    """
    # Create a new ProductMonitored record
    db_product = ProductMonitored(
        title=product.title,
        sku=product.sku,
        brand=product.brand,
        image_url=product.image_url
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)  # Get the ID that was auto-generated

    # Return the product with competitor_count = 0 (no matches yet)
    return ProductResponse(
        id=db_product.id,
        title=db_product.title,
        sku=db_product.sku,
        brand=db_product.brand,
        image_url=db_product.image_url,
        created_at=db_product.created_at,
        competitor_count=0
    )


@router.get("/", response_model=List[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    """
    GET /products

    Get all monitored products.
    Returns a list of products with their competitor counts.
    """
    products = db.query(ProductMonitored).all()

    # Convert to response format with competitor counts
    response_products = []
    for product in products:
        response_products.append(ProductResponse(
            id=product.id,
            title=product.title,
            sku=product.sku,
            brand=product.brand,
            image_url=product.image_url,
            created_at=product.created_at,
            competitor_count=len(product.competitor_matches)
        ))

    return response_products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    GET /products/{id}

    Get a specific product by ID.
    """
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(
        id=product.id,
        title=product.title,
        sku=product.sku,
        brand=product.brand,
        image_url=product.image_url,
        created_at=product.created_at,
        competitor_count=len(product.competitor_matches)
    )


@router.get("/{product_id}/matches", response_model=List[CompetitorMatchResponse])
def get_product_matches(product_id: int, db: Session = Depends(get_db)):
    """
    GET /products/{id}/matches

    Get all competitor matches for a product.
    Includes the latest price for each match.
    """
    # Check if product exists
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all matches
    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    ).all()

    # Convert to response format with latest price
    response_matches = []
    for match in matches:
        # Get the most recent price
        latest_price_record = db.query(PriceHistory).filter(
            PriceHistory.match_id == match.id
        ).order_by(PriceHistory.timestamp.desc()).first()

        response_matches.append(CompetitorMatchResponse(
            id=match.id,
            competitor_name=match.competitor_name,
            competitor_url=match.competitor_url,
            competitor_title=match.competitor_title,
            competitor_image_url=match.competitor_image_url,
            match_score=match.match_score,
            last_crawled_at=match.last_crawled_at,
            latest_price=latest_price_record.price if latest_price_record else None,
            in_stock=latest_price_record.in_stock if latest_price_record else None
        ))

    return response_matches


@router.get("/{product_id}/price-history", response_model=List[PriceHistoryResponse])
def get_price_history(product_id: int, db: Session = Depends(get_db)):
    """
    GET /products/{id}/price-history

    Get price history for all competitors of a product.
    Used to display the price chart.
    """
    # Check if product exists
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()
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
                in_stock=price_record.in_stock,
                competitor_name=match.competitor_name
            ))

    # Sort by timestamp
    history_records.sort(key=lambda x: x.timestamp)

    return history_records


@router.post("/{product_id}/scrape")
def trigger_scrape(product_id: int, db: Session = Depends(get_db)):
    """
    POST /products/{id}/scrape

    Manually trigger a scrape for this product.
    This will search Amazon and update competitor matches.

    (We'll implement the actual scraping logic next!)
    """
    # Check if product exists
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # TODO: Call the scraper here
    # For now, just return a message
    return {
        "status": "scrape_triggered",
        "product_id": product_id,
        "message": "Scraping functionality will be implemented next!"
    }


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
