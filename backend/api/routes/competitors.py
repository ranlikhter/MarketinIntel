"""
Competitor Websites API Routes

Manage custom competitor websites (any site, not just Amazon/eBay).

Security:
- All routes require authentication.
- Data is scoped to the active workspace (shop). If no workspace is selected
  the fallback is legacy user_id scoping via build_scope_predicate, ensuring
  existing single-user data keeps working during the migration period.
- Users in the same workspace share competitor website definitions, making
  it possible for a whole team to collaborate on the competitor list.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import ConfigDict, BaseModel
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import CompetitorWebsite, User
from api.dependencies import get_current_user, get_current_workspace, ActiveWorkspace, build_scope_predicate
from services.ssrf_validator import validate_external_url

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scope(aw: ActiveWorkspace, current_user: User):
    """Return (workspace_id, user_id) for scope predicate and new-row ownership."""
    return aw.workspace_id, current_user.id


def _find(db, competitor_id: int, aw: ActiveWorkspace, current_user: User):
    """Fetch a CompetitorWebsite row the caller is allowed to access, or 404."""
    row = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.id == competitor_id,
        build_scope_predicate(
            CompetitorWebsite,
            workspace_id=aw.workspace_id,
            user_id=current_user.id,
        ),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Competitor website not found")
    return row


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=CompetitorWebsiteResponse, status_code=201)
def create_competitor_website(
    competitor: CompetitorWebsiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Add a new competitor website scoped to the active workspace (shop)."""
    validate_external_url(competitor.base_url, field_name="base_url")

    workspace_id, user_id = _scope(aw, current_user)

    # Uniqueness check within this workspace / user scope
    existing = db.query(CompetitorWebsite).filter(
        CompetitorWebsite.base_url == competitor.base_url,
        build_scope_predicate(
            CompetitorWebsite,
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Competitor website with URL '{competitor.base_url}' already exists",
        )

    db_competitor = CompetitorWebsite(
        user_id=user_id,
        workspace_id=workspace_id,
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
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """List all competitor websites visible to the active workspace (shop)."""
    query = db.query(CompetitorWebsite).filter(
        build_scope_predicate(
            CompetitorWebsite,
            workspace_id=aw.workspace_id,
            user_id=current_user.id,
        )
    )
    if active_only:
        query = query.filter(CompetitorWebsite.is_active == True)
    return query.order_by(CompetitorWebsite.name).all()


@router.get("/{competitor_id}", response_model=CompetitorWebsiteResponse)
def get_competitor(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Get a specific competitor website (must belong to the active workspace)."""
    return _find(db, competitor_id, aw, current_user)


@router.put("/{competitor_id}", response_model=CompetitorWebsiteResponse)
def update_competitor(
    competitor_id: int,
    competitor_update: CompetitorWebsiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Update a competitor website (must belong to the active workspace)."""
    competitor = _find(db, competitor_id, aw, current_user)

    update_data = competitor_update.model_dump(exclude_unset=True)
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
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Delete a competitor website (must belong to the active workspace)."""
    competitor = _find(db, competitor_id, aw, current_user)
    db.delete(competitor)
    db.commit()
    return {"status": "deleted", "competitor_id": competitor_id}


@router.post("/{competitor_id}/toggle")
def toggle_competitor_status(
    competitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Enable or disable a competitor website without deleting it."""
    competitor = _find(db, competitor_id, aw, current_user)
    competitor.is_active = not competitor.is_active
    db.commit()
    db.refresh(competitor)
    return {
        "status": "active" if competitor.is_active else "inactive",
        "competitor_id": competitor_id,
        "name": competitor.name,
    }
