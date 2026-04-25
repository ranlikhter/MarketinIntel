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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Optional
from pydantic import ConfigDict, BaseModel
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import get_db
from database.models import CompetitorWebsite, CompetitorMatch, ProductMonitored, User
from api.dependencies import get_current_user, get_current_workspace, ActiveWorkspace, build_scope_predicate
from services.ssrf_validator import validate_external_url
from services.cache_service import get_cached

_FACETS_TTL = 300  # 5 minutes

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


# ── Competitor Products faceted search ───────────────────────────────────────

class CompetitorProductResult(BaseModel):
    match_id: int
    my_product_id: int
    my_product_title: str
    competitor_name: str
    competitor_url: str
    competitor_product_title: str
    brand: Optional[str]
    category: Optional[str]
    latest_price: Optional[float]
    image_url: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    in_stock: Optional[bool]
    is_prime: Optional[bool]
    match_score: float
    badges: List[str]
    has_coupon: bool
    last_scraped_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CompetitorProductListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    results: List[CompetitorProductResult]


class FacetsPriceRange(BaseModel):
    min: Optional[float]
    max: Optional[float]


class CompetitorProductFacets(BaseModel):
    competitors: List[str]
    brands: List[str]
    categories: List[str]
    conditions: List[str]
    price_range: FacetsPriceRange


_SORT_MAP = {
    "price_asc": CompetitorMatch.latest_price.asc(),
    "price_desc": CompetitorMatch.latest_price.desc(),
    "rating_desc": CompetitorMatch.rating.desc(),
    "match_score_desc": CompetitorMatch.match_score.desc(),
    "last_scraped_desc": CompetitorMatch.last_scraped_at.desc(),
}


def _base_product_query(db: Session, aw: ActiveWorkspace, current_user: User):
    """Return a query joined to ProductMonitored, scoped to the active workspace."""
    return (
        db.query(CompetitorMatch, ProductMonitored)
        .join(ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id)
        .filter(
            build_scope_predicate(CompetitorMatch, workspace_id=aw.workspace_id, user_id=current_user.id)
        )
    )


def _apply_product_filters(query, params: dict):
    """Chain optional filter clauses onto a CompetitorMatch query."""
    q = params.get("q")
    if q:
        query = query.filter(CompetitorMatch.competitor_product_title.ilike(f"%{q}%"))

    competitors = params.get("competitor")
    if competitors:
        query = query.filter(CompetitorMatch.competitor_name.in_(competitors))

    brands = params.get("brand")
    if brands:
        query = query.filter(CompetitorMatch.brand.in_(brands))

    categories = params.get("category")
    if categories:
        query = query.filter(CompetitorMatch.category.in_(categories))

    min_price = params.get("min_price")
    max_price = params.get("max_price")
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price
    if min_price is not None:
        query = query.filter(CompetitorMatch.latest_price >= min_price)
    if max_price is not None:
        query = query.filter(CompetitorMatch.latest_price <= max_price)

    in_stock = params.get("in_stock")
    if in_stock is True:
        query = query.filter(CompetitorMatch.stock_status.ilike("%in stock%"))

    min_rating = params.get("min_rating")
    if min_rating is not None:
        query = query.filter(CompetitorMatch.rating >= min_rating)

    min_match_score = params.get("min_match_score", 60.0)
    query = query.filter(CompetitorMatch.match_score >= min_match_score)

    is_prime = params.get("is_prime")
    if is_prime is True:
        query = query.filter(CompetitorMatch.is_prime == True)

    has_coupon = params.get("has_coupon")
    if has_coupon is True:
        query = query.filter(
            (CompetitorMatch.coupon_value > 0) | (CompetitorMatch.coupon_pct > 0)
        )

    has_lightning_deal = params.get("has_lightning_deal")
    if has_lightning_deal is True:
        query = query.filter(CompetitorMatch.is_lightning_deal == True)

    is_sponsored = params.get("is_sponsored")
    if is_sponsored is True:
        query = query.filter(CompetitorMatch.is_sponsored == True)

    badge = params.get("badge")
    badge_col_map = {
        "amazons_choice": CompetitorMatch.badge_amazons_choice,
        "best_seller": CompetitorMatch.badge_best_seller,
        "new_release": CompetitorMatch.badge_new_release,
    }
    if badge and badge in badge_col_map:
        query = query.filter(badge_col_map[badge] == True)

    condition = params.get("condition")
    if condition:
        query = query.filter(CompetitorMatch.product_condition == condition)

    seller = params.get("seller")
    if seller:
        query = query.filter(CompetitorMatch.seller_name.ilike(f"%{seller}%"))

    scraped_within_days = params.get("scraped_within_days")
    if scraped_within_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=scraped_within_days)
        query = query.filter(CompetitorMatch.last_scraped_at >= cutoff)

    my_product_id = params.get("my_product_id")
    if my_product_id is not None:
        query = query.filter(CompetitorMatch.monitored_product_id == my_product_id)

    return query


def _build_badges(match: CompetitorMatch) -> List[str]:
    badges = []
    if match.badge_amazons_choice:
        badges.append("amazons_choice")
    if match.badge_best_seller:
        badges.append("best_seller")
    if match.badge_new_release:
        badges.append("new_release")
    return badges


@router.get("/products/facets", response_model=CompetitorProductFacets)
def get_competitor_product_facets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Return distinct filter values for the competitor products sidebar. Cached 5 min."""
    cache_key = f"competitor_facets:{current_user.id}:{aw.workspace_id}"

    def compute():
        scope = build_scope_predicate(CompetitorMatch, workspace_id=aw.workspace_id, user_id=current_user.id)

        competitors = [
            r[0] for r in
            db.query(distinct(CompetitorMatch.competitor_name))
            .filter(scope, CompetitorMatch.competitor_name.isnot(None))
            .order_by(CompetitorMatch.competitor_name)
            .all()
        ]

        brands = [
            r[0] for r in
            db.query(CompetitorMatch.brand, func.count(CompetitorMatch.id).label("cnt"))
            .filter(scope, CompetitorMatch.brand.isnot(None))
            .group_by(CompetitorMatch.brand)
            .order_by(func.count(CompetitorMatch.id).desc())
            .limit(200)
            .all()
        ]

        categories = [
            r[0] for r in
            db.query(distinct(CompetitorMatch.category))
            .filter(scope, CompetitorMatch.category.isnot(None))
            .order_by(CompetitorMatch.category)
            .all()
        ]

        conditions = [
            r[0] for r in
            db.query(distinct(CompetitorMatch.product_condition))
            .filter(scope, CompetitorMatch.product_condition.isnot(None))
            .order_by(CompetitorMatch.product_condition)
            .all()
        ]

        price_agg = (
            db.query(
                func.min(CompetitorMatch.latest_price),
                func.max(CompetitorMatch.latest_price),
            )
            .filter(scope, CompetitorMatch.latest_price.isnot(None))
            .first()
        )

        return {
            "competitors": competitors,
            "brands": brands,
            "categories": categories,
            "conditions": conditions,
            "price_range": {
                "min": price_agg[0] if price_agg else None,
                "max": price_agg[1] if price_agg else None,
            },
        }

    return get_cached(cache_key, _FACETS_TTL, compute)


@router.get("/products", response_model=CompetitorProductListResponse)
def get_competitor_products(
    q: Optional[str] = Query(None),
    competitor: Optional[str] = Query(None, description="Comma-separated competitor names"),
    brand: Optional[str] = Query(None, description="Comma-separated brands"),
    category: Optional[str] = Query(None, description="Comma-separated categories"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    in_stock: Optional[bool] = Query(None),
    min_rating: Optional[float] = Query(None),
    min_match_score: float = Query(60.0),
    is_prime: Optional[bool] = Query(None),
    has_coupon: Optional[bool] = Query(None),
    has_lightning_deal: Optional[bool] = Query(None),
    is_sponsored: Optional[bool] = Query(None),
    badge: Optional[str] = Query(None, description="amazons_choice | best_seller | new_release"),
    condition: Optional[str] = Query(None),
    seller: Optional[str] = Query(None),
    scraped_within_days: Optional[int] = Query(None),
    my_product_id: Optional[int] = Query(None),
    sort: str = Query("match_score_desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    aw: ActiveWorkspace = Depends(get_current_workspace),
):
    """Faceted search over all competitor product matches for the active workspace."""
    params = {
        "q": q,
        "competitor": [c.strip() for c in competitor.split(",")] if competitor else None,
        "brand": [b.strip() for b in brand.split(",")] if brand else None,
        "category": [c.strip() for c in category.split(",")] if category else None,
        "min_price": min_price,
        "max_price": max_price,
        "in_stock": in_stock,
        "min_rating": min_rating,
        "min_match_score": min_match_score,
        "is_prime": is_prime,
        "has_coupon": has_coupon,
        "has_lightning_deal": has_lightning_deal,
        "is_sponsored": is_sponsored,
        "badge": badge,
        "condition": condition,
        "seller": seller,
        "scraped_within_days": scraped_within_days,
        "my_product_id": my_product_id,
    }

    base_q = _base_product_query(db, aw, current_user)
    filtered_q = _apply_product_filters(base_q, params)

    total = filtered_q.with_entities(func.count(CompetitorMatch.id)).scalar()

    sort_clause = _SORT_MAP.get(sort, CompetitorMatch.match_score.desc())
    rows = (
        filtered_q
        .order_by(sort_clause)
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for match, product in rows:
        results.append(
            CompetitorProductResult(
                match_id=match.id,
                my_product_id=product.id,
                my_product_title=product.title or "",
                competitor_name=match.competitor_name,
                competitor_url=match.competitor_url,
                competitor_product_title=match.competitor_product_title,
                brand=match.brand,
                category=match.category,
                latest_price=match.latest_price,
                image_url=match.image_url,
                rating=match.rating,
                review_count=match.review_count,
                in_stock=(match.stock_status or "").lower().find("in stock") >= 0 if match.stock_status else None,
                is_prime=match.is_prime,
                match_score=match.match_score or 0.0,
                badges=_build_badges(match),
                has_coupon=bool(
                    (match.coupon_value and match.coupon_value > 0) or
                    (match.coupon_pct and match.coupon_pct > 0)
                ),
                last_scraped_at=match.last_scraped_at,
            )
        )

    return CompetitorProductListResponse(total=total or 0, limit=limit, offset=offset, results=results)
