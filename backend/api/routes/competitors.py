"""
Competitor Websites API Routes

These endpoints allow clients to add and manage their own custom competitor
websites (not just Amazon/eBay, but any private website they want to monitor).

Security: All routes require authentication. Each user can only see and modify
their own competitor entries (user_id scoping).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import ConfigDict, BaseModel, HttpUrl
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import CompetitorWebsite, User
from api.dependencies import get_current_user
from services.ssrf_validator import validate_external_url

router = APIRouter()


# Pydantic models

class CompetitorWebsiteCreate(BaseModel):
    name: str
    base_url: str
    website_type: str = "custom"
    price_selector: str | None = None
    title_selector: str | None = None
    stock_selector: str | None = None
    image_selector: str | None = None
    notes: str | None = None


class CompetitorWebsiteUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    price_selector: str | None = None
    title_selector: str | None = None
    stock_selector: str | None = None
    image_selector: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class CompetitorWebsiteResponse(BaseModel):
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
    """Add a new competitor website to monitor (scoped to the authenticated user)."""
    # SSRF protection — prevent crawling internal/private hosts
    validate_external_url(competitor.base_url, field_name="base_url")

    # Scope uniqueness check to this user
    existing = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.base_url == competitor.base_url,
        CompetitorWebsite.user_id == current_user.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Competitor website with URL '{competitor.base_url}' already exists",
        )

    db_competitor = CompetitorWebsite(
        user_id=current_user.id,
        name=competitor.name,
        base_url=competitor.base_url,
        website_type=competitor.website_type,
        price_selector=competitor.price_selector,
        title_selector=competitor.title_selector,
        stock_selector=competitor.stock_selector,
        image_selector=competitor.image_selector,
        notes=competitor.notes,
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
    """Get all competitor websites belonging to the authenticated user."""
    query = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.user_id == current_user.id
    )

    if active_only:
        query = query.filter(CompetitorWebsite.is_active == True)

    return query.order_by(CompetitorWebsite.name).all()


@router.get("/{competitor_id}", response_model=CompetitorWebsiteResponse)
def get_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific competitor website by ID (must belong to the current user)."""
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id,
        CompetitorWebsite.user_id == current_user.id,
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
    """Update a competitor website (must belong to the current user)."""
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id,
        CompetitorWebsite.user_id == current_user.id,
    ).first()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor website not found")

    update_data = competitor_update.model_dump(exclude_unset=True)

    # Validate new base_url against SSRF if it changed
    if "base_url" in update_data:
        validate_external_url(update_data["base_url"], field_name="base_url")

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
    """Delete a competitor website (must belong to the current user)."""
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id,
        CompetitorWebsite.user_id == current_user.id,
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
    """Enable or disable a competitor website without deleting it."""
    competitor = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id,
        CompetitorWebsite.user_id == current_user.id,
    ).first()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor website not found")

    competitor.is_active = not competitor.is_active
    db.commit()
    db.refresh(competitor)

    return {
        "status": "active" if competitor.is_active else "inactive",
        "competitor_id": competitor_id,
        "name": competitor.name,
    }
