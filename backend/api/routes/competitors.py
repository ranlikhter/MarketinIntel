"""
Competitor Websites API Routes

These endpoints allow clients to add and manage their own custom competitor websites
(not just Amazon/eBay, but any private website they want to monitor).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import ConfigDict, BaseModel, HttpUrl
from datetime import datetime

# Import our database stuff
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import CompetitorWebsite, User
from api.dependencies import get_current_user

# Create a router
router = APIRouter()


# Pydantic models for request/response validation
class CompetitorWebsiteCreate(BaseModel):
    """
    Schema for adding a new competitor website.
    """
    name: str                           # e.g., "Acme Electronics"
    base_url: str                       # e.g., "https://www.acme-electronics.com"
    website_type: str = "custom"        # "custom", "amazon", "walmart", etc.

    # Optional: CSS selectors for scraping (advanced users can configure)
    price_selector: str | None = None   # e.g., ".price", "#product-price"
    title_selector: str | None = None   # e.g., "h1.title"
    stock_selector: str | None = None   # e.g., ".stock-status"
    image_selector: str | None = None   # e.g., "img.main-image"

    notes: str | None = None            # Any notes about this competitor


class CompetitorWebsiteUpdate(BaseModel):
    """
    Schema for updating an existing competitor website.
    All fields are optional.
    """
    name: str | None = None
    base_url: str | None = None
    price_selector: str | None = None
    title_selector: str | None = None
    stock_selector: str | None = None
    image_selector: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class CompetitorWebsiteResponse(BaseModel):
    """
    Schema for returning competitor website data.
    """
    id: int
    name: str
    base_url: str
    website_type: str
    price_selector: str | None
    title_selector: str | None
    stock_selector: str | None
    image_selector: str | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# API ENDPOINTS

@router.post("/", response_model=CompetitorWebsiteResponse, status_code=201)
def create_competitor_website(
    competitor: CompetitorWebsiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /competitors

    Add a new competitor website to monitor.

    Example request:
    {
        "name": "Acme Electronics",
        "base_url": "https://www.acme-electronics.com",
        "price_selector": ".product-price",
        "title_selector": "h1.product-name",
        "notes": "Our main competitor in the electronics space"
    }
    """
    # Check if website already exists
    existing = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.base_url == competitor.base_url
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Competitor website with URL '{competitor.base_url}' already exists"
        )

    # Create new competitor website
    db_competitor = CompetitorWebsite(
        name=competitor.name,
        base_url=competitor.base_url,
        website_type=competitor.website_type,
        price_selector=competitor.price_selector,
        title_selector=competitor.title_selector,
        stock_selector=competitor.stock_selector,
        image_selector=competitor.image_selector,
        notes=competitor.notes
    )

    db.add(db_competitor)
    db.commit()
    db.refresh(db_competitor)

    return db_competitor


@router.get("/", response_model=List[CompetitorWebsiteResponse])
def get_all_competitors(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /competitors

    Get all competitor websites.
    Use ?active_only=true to only show active competitors.
    """
    query = db.query(CompetitorWebsite)

    if active_only:
        query = query.filter(CompetitorWebsite.is_active == True)

    competitors = query.order_by(CompetitorWebsite.name).all()
    return competitors


@router.get("/{competitor_id}", response_model=CompetitorWebsiteResponse)
def get_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /competitors/{id}

    Get a specific competitor website by ID.
    """
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id
    ).first()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor website not found")

    return competitor


@router.put("/{competitor_id}", response_model=CompetitorWebsiteResponse)
def update_competitor(
    competitor_id: int,
    competitor_update: CompetitorWebsiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    PUT /competitors/{id}

    Update a competitor website's details.

    Example request (update CSS selectors):
    {
        "price_selector": ".new-price-class",
        "notes": "They redesigned their website, updated selectors"
    }
    """
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id
    ).first()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor website not found")

    # Update only fields that were provided
    update_data = competitor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(competitor, field, value)

    db.commit()
    db.refresh(competitor)

    return competitor


@router.delete("/{competitor_id}")
def delete_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    DELETE /competitors/{id}

    Delete a competitor website.
    Warning: This will also remove all product matches from this competitor.
    """
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id
    ).first()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor website not found")

    db.delete(competitor)
    db.commit()

    return {"status": "deleted", "competitor_id": competitor_id}


@router.post("/{competitor_id}/toggle")
def toggle_competitor_status(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /competitors/{id}/toggle

    Enable or disable a competitor website without deleting it.
    Useful for temporarily stopping scraping without losing configuration.
    """
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id
    ).first()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor website not found")

    # Toggle the status
    competitor.is_active = not competitor.is_active
    db.commit()
    db.refresh(competitor)

    return {
        "status": "active" if competitor.is_active else "inactive",
        "competitor_id": competitor_id,
        "name": competitor.name
    }
