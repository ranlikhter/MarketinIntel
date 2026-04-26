"""
Campaign Price Scheduler Routes

CRUD for price campaigns (Black Friday, flash sales, clearance).
The actual price application is handled by the Celery beat task in
tasks/campaign_tasks.py — these endpoints only manage campaign records.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.dependencies import ActiveWorkspace, get_current_user, get_current_workspace
from database.connection import get_db
from database.models import (
    CampaignProductSnapshot,
    PriceCampaign,
    ProductMonitored,
    User,
)
from services.activity_service import log_activity
from services.workspace_service import build_scope_predicate

router = APIRouter()

_TEMPLATES = {
    "black_friday": {"name": "Black Friday Sale", "rules": [{"type": "discount_pct", "value": 20}]},
    "flash_sale":   {"name": "Flash Sale",        "rules": [{"type": "discount_pct", "value": 15}]},
    "clearance":    {"name": "Clearance",          "rules": [{"type": "discount_pct", "value": 30}]},
}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    rules: list[dict[str, Any]]
    product_filter: Optional[dict[str, Any]] = None

    @field_validator("ends_at")
    @classmethod
    def ends_after_starts(cls, v, info):
        if "starts_at" in info.data and v <= info.data["starts_at"]:
            raise ValueError("ends_at must be after starts_at")
        return v


class CampaignResponse(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    template: Optional[str] = None
    status: str
    starts_at: datetime
    ends_at: datetime
    rules: list
    product_filter: Optional[dict] = None
    products_affected: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignPreviewProduct(BaseModel):
    product_id: int
    title: str
    sku: Optional[str] = None
    current_price: float
    new_price: float
    floor_clamped: bool = False


class CampaignPreviewResponse(BaseModel):
    products_matched: int
    sample: list[CampaignPreviewProduct]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_campaign_or_404(db, scope, campaign_id: int) -> PriceCampaign:
    campaign = db.query(PriceCampaign).filter(scope, PriceCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _compute_new_price(current_price: float, rules: list) -> Optional[float]:
    for rule in rules:
        rule_type = rule.get("type", "")
        value = rule.get("value")
        if value is None:
            continue
        if rule_type == "discount_pct":
            return round(current_price * (1 - float(value) / 100), 2)
        if rule_type == "discount_fixed":
            return round(max(current_price - float(value), 0.01), 2)
        if rule_type == "set_price":
            return round(float(value), 2)
    return None


def _floor_for_product(product: ProductMonitored) -> Optional[float]:
    cost = getattr(product, "cost_price", None)
    margin = getattr(product, "target_margin_pct", None)
    if cost and margin and 0 < margin < 100:
        return cost / (1 - margin / 100)
    candidates = [p for p in [product.min_price, product.map_price] if p]
    return max(candidates) if candidates else None


def _matches_filter(product: ProductMonitored, pf: Optional[dict]) -> bool:
    if not pf or pf.get("all"):
        return True
    if "category" in pf:
        if pf["category"].lower() not in (product.category or "").lower():
            return False
    if "tags" in pf:
        tags = [t.lower() for t in (product.tags or [])]
        if not any(t.lower() in tags for t in pf["tags"]):
            return False
    if "skus" in pf:
        if (product.sku or "").lower() not in [s.lower() for s in pf["skus"]]:
            return False
    return True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    scope = build_scope_predicate(PriceCampaign, aw.workspace_id, current_user.id)
    q = db.query(PriceCampaign).filter(scope)
    if status:
        q = q.filter(PriceCampaign.status == status)
    return q.order_by(PriceCampaign.starts_at.desc()).all()


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    if body.starts_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="starts_at must be in the future")
    if not body.rules:
        raise HTTPException(status_code=400, detail="At least one rule is required")

    # Apply template defaults if provided
    name = body.name
    rules = body.rules
    if body.template and body.template in _TEMPLATES:
        tmpl = _TEMPLATES[body.template]
        name = name or tmpl["name"]
        rules = rules or tmpl["rules"]

    campaign = PriceCampaign(
        workspace_id=aw.workspace_id,
        user_id=current_user.id,
        name=name,
        description=body.description,
        template=body.template,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        rules=rules,
        product_filter=body.product_filter,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    log_activity(db, current_user.id, "campaign.created", "campaign",
                 f"Campaign '{campaign.name}' scheduled for {campaign.starts_at.date()}",
                 metadata={"campaign_id": campaign.id})
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    scope = build_scope_predicate(PriceCampaign, aw.workspace_id, current_user.id)
    return _get_campaign_or_404(db, scope, campaign_id)


@router.post("/campaigns/{campaign_id}/preview", response_model=CampaignPreviewResponse)
def preview_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Dry-run: show which products would be affected and at what price. No DB writes."""
    scope = build_scope_predicate(PriceCampaign, aw.workspace_id, current_user.id)
    campaign = _get_campaign_or_404(db, scope, campaign_id)

    products = (
        db.query(ProductMonitored)
        .filter(
            ProductMonitored.workspace_id == aw.workspace_id,
            ProductMonitored.my_price.isnot(None),
            ProductMonitored.status == "active",
        )
        .limit(5_000)
        .all()
    )

    matched = []
    for product in products:
        if not _matches_filter(product, campaign.product_filter):
            continue
        new_price = _compute_new_price(product.my_price, campaign.rules or [])
        if new_price is None:
            continue
        floor = _floor_for_product(product)
        floor_clamped = False
        if floor and new_price < floor:
            new_price = round(floor, 2)
            floor_clamped = True
        matched.append(CampaignPreviewProduct(
            product_id=product.id,
            title=product.title or "",
            sku=product.sku,
            current_price=product.my_price,
            new_price=new_price,
            floor_clamped=floor_clamped,
        ))

    return CampaignPreviewResponse(
        products_matched=len(matched),
        sample=matched[:20],
    )


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignResponse)
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Pause a running campaign (prices stay; auto-revert is suspended)."""
    scope = build_scope_predicate(PriceCampaign, aw.workspace_id, current_user.id)
    campaign = _get_campaign_or_404(db, scope, campaign_id)
    if campaign.status not in ("running", "scheduled"):
        raise HTTPException(status_code=400, detail=f"Cannot pause a {campaign.status} campaign")
    campaign.status = "paused"
    db.commit()
    db.refresh(campaign)
    log_activity(db, current_user.id, "campaign.paused", "campaign",
                 f"Campaign '{campaign.name}' paused",
                 metadata={"campaign_id": campaign.id})
    return campaign


@router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignResponse)
def cancel_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Cancel a campaign. If running, prices are reverted immediately."""
    scope = build_scope_predicate(PriceCampaign, aw.workspace_id, current_user.id)
    campaign = _get_campaign_or_404(db, scope, campaign_id)
    if campaign.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign.status}")

    if campaign.status == "running":
        # Revert prices now using the snapshot data
        from tasks.campaign_tasks import _end_campaign
        campaign.ends_at = datetime.utcnow()
        db.commit()
        _end_campaign(db, campaign, datetime.utcnow())
    else:
        campaign.status = "cancelled"
        db.commit()

    db.refresh(campaign)
    log_activity(db, current_user.id, "campaign.cancelled", "campaign",
                 f"Campaign '{campaign.name}' cancelled",
                 metadata={"campaign_id": campaign.id})
    return campaign


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    scope = build_scope_predicate(PriceCampaign, aw.workspace_id, current_user.id)
    campaign = _get_campaign_or_404(db, scope, campaign_id)
    if campaign.status == "running":
        raise HTTPException(status_code=400, detail="Cancel the campaign before deleting it")
    db.delete(campaign)
    db.commit()
