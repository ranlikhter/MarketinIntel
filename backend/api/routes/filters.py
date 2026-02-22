"""
Filtering & Saved Views API Routes
Advanced product filtering and saved filter combinations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from sqlalchemy import or_
from database.connection import get_db
from database.models import User, SavedView, ProductMonitored, WorkspaceMember, SubscriptionTier
from api.dependencies import get_current_user
from services.filter_service import get_filter_service

router = APIRouter(prefix="/filters", tags=["Filtering & Search"])


# Pydantic Models
class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    limit: Optional[int] = 50
    offset: Optional[int] = 0


class SavedViewCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    filters: Dict[str, Any]
    is_default: bool = False
    is_shared: bool = False
    sort_by: Optional[str] = "created_at"
    sort_order: str = "desc"


class SavedViewUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_shared: Optional[bool] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None


class SavedViewResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    filters: Dict[str, Any]
    is_default: bool
    is_shared: bool
    sort_by: Optional[str]
    sort_order: str
    use_count: int
    last_used_at: Optional[Any]
    created_at: Any

    class Config:
        from_attributes = True


class FilterOptionsResponse(BaseModel):
    brands: List[str]
    total_products: int
    competition_levels: Dict[str, int]
    recent_activity: Dict[str, int]
    date_range: Dict[str, Any]


# Filtering Endpoints

@router.post("/apply")
async def apply_filters(
    request: FilterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply filters to products and return results

    Supported filters:
    - **price_position**: "cheapest", "most_expensive", "mid_range"
    - **competition_level**: "high", "medium", "low", "none"
    - **activity**: "price_dropped", "new_competitor", "out_of_stock", "trending"
    - **opportunity_score**: {"min": 0, "max": 100}
    - **price_range**: {"min": 0, "max": 1000}
    - **brand**: "string"
    - **sku**: "string"
    - **date_added**: {"from": "2024-01-01", "to": "2024-12-31"}
    - **has_alerts**: true/false
    - **search**: "fuzzy search term"
    """
    filter_service = get_filter_service(db, current_user)

    # Apply filters
    query = filter_service.apply_filters(request.filters)

    # Apply sorting
    if request.sort_by == "title":
        query = query.order_by(
            ProductMonitored.title.desc() if request.sort_order == "desc"
            else ProductMonitored.title.asc()
        )
    elif request.sort_by == "created_at":
        query = query.order_by(
            ProductMonitored.created_at.desc() if request.sort_order == "desc"
            else ProductMonitored.created_at.asc()
        )
    elif request.sort_by == "brand":
        query = query.order_by(
            ProductMonitored.brand.desc() if request.sort_order == "desc"
            else ProductMonitored.brand.asc()
        )

    # Apply pagination
    total = query.count()
    products = query.offset(request.offset).limit(request.limit).all()

    return {
        "products": [
            {
                "id": p.id,
                "title": p.title,
                "sku": p.sku,
                "brand": p.brand,
                "image_url": p.image_url,
                "competitor_count": len(p.competitor_matches),
                "alert_count": len([a for a in p.alerts if a.enabled]),
                "created_at": p.created_at
            }
            for p in products
        ],
        "total": total,
        "limit": request.limit,
        "offset": request.offset,
        "has_more": (request.offset + request.limit) < total
    }


@router.get("/search")
async def search_products(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fuzzy search across products

    Searches in: title, brand, SKU
    Returns ranked results (exact matches first, then partial)
    """
    filter_service = get_filter_service(db, current_user)

    products = filter_service.search_products(q, limit)

    return {
        "query": q,
        "results": [
            {
                "id": p.id,
                "title": p.title,
                "sku": p.sku,
                "brand": p.brand,
                "image_url": p.image_url,
                "competitor_count": len(p.competitor_matches),
                "created_at": p.created_at
            }
            for p in products
        ],
        "total": len(products)
    }


@router.get("/options", response_model=FilterOptionsResponse)
async def get_filter_options(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available filter options based on user's data

    Returns:
    - Available brands
    - Total products
    - Competition level counts
    - Recent activity counts
    - Date range
    """
    filter_service = get_filter_service(db, current_user)

    options = filter_service.get_filter_options()

    return options


# Saved Views Endpoints

@router.post("/views", response_model=SavedViewResponse)
async def create_saved_view(
    view: SavedViewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a saved view (filter combination)

    Examples:
    - "Problem Products" - Most expensive + high competition
    - "Black Friday Prep" - High opportunity + trending
    - "Quick Wins" - Competitor out of stock
    """
    # If setting as default, unset other defaults
    if view.is_default:
        db.query(SavedView).filter(
            SavedView.user_id == current_user.id,
            SavedView.is_default == True
        ).update({"is_default": False})

    new_view = SavedView(
        user_id=current_user.id,
        name=view.name,
        description=view.description,
        icon=view.icon,
        filters=view.filters,
        is_default=view.is_default,
        is_shared=view.is_shared,
        sort_by=view.sort_by,
        sort_order=view.sort_order
    )

    db.add(new_view)
    db.commit()
    db.refresh(new_view)

    return new_view


@router.get("/views", response_model=List[SavedViewResponse])
async def get_saved_views(
    include_shared: bool = Query(True, description="Include workspace-shared views"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all saved views for current user

    Includes:
    - User's own views
    - Workspace-shared views (if include_shared=true)
    """
    # Start with the user's own views
    conditions = [SavedView.user_id == current_user.id]

    # Business/Enterprise users also see views shared by workspace members
    if include_shared and current_user.subscription_tier in (
        SubscriptionTier.BUSINESS, SubscriptionTier.ENTERPRISE
    ):
        # Collect workspace IDs the user belongs to
        workspace_ids = [
            m.workspace_id
            for m in db.query(WorkspaceMember).filter(
                WorkspaceMember.user_id == current_user.id,
                WorkspaceMember.is_active == True,
            ).all()
        ]
        if workspace_ids:
            conditions.append(
                and_(
                    SavedView.is_shared == True,
                    SavedView.workspace_id.in_(workspace_ids),
                )
            )

    from sqlalchemy import and_
    query = db.query(SavedView).filter(or_(*conditions))

    views = query.order_by(SavedView.is_default.desc(), SavedView.use_count.desc()).all()

    return views


@router.get("/views/{view_id}", response_model=SavedViewResponse)
async def get_saved_view(
    view_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific saved view by ID"""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current_user.id
    ).first()

    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found")

    # Update usage stats
    from datetime import datetime
    view.use_count += 1
    view.last_used_at = datetime.utcnow()
    db.commit()

    return view


@router.put("/views/{view_id}", response_model=SavedViewResponse)
async def update_saved_view(
    view_id: int,
    update: SavedViewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a saved view"""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current_user.id
    ).first()

    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found")

    # If setting as default, unset other defaults
    if update.is_default:
        db.query(SavedView).filter(
            SavedView.user_id == current_user.id,
            SavedView.id != view_id,
            SavedView.is_default == True
        ).update({"is_default": False})

    # Update fields
    if update.name is not None:
        view.name = update.name
    if update.description is not None:
        view.description = update.description
    if update.icon is not None:
        view.icon = update.icon
    if update.filters is not None:
        view.filters = update.filters
    if update.is_default is not None:
        view.is_default = update.is_default
    if update.is_shared is not None:
        view.is_shared = update.is_shared
    if update.sort_by is not None:
        view.sort_by = update.sort_by
    if update.sort_order is not None:
        view.sort_order = update.sort_order

    from datetime import datetime
    view.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(view)

    return view


@router.delete("/views/{view_id}")
async def delete_saved_view(
    view_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved view"""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current_user.id
    ).first()

    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found")

    db.delete(view)
    db.commit()

    return {"success": True, "message": "Saved view deleted"}


@router.post("/views/{view_id}/duplicate")
async def duplicate_saved_view(
    view_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate a saved view"""
    original = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current_user.id
    ).first()

    if not original:
        raise HTTPException(status_code=404, detail="Saved view not found")

    # Create duplicate
    duplicate = SavedView(
        user_id=current_user.id,
        name=f"{original.name} (Copy)",
        description=original.description,
        icon=original.icon,
        filters=original.filters,
        is_default=False,  # Don't duplicate default setting
        is_shared=False,  # Don't duplicate shared setting
        sort_by=original.sort_by,
        sort_order=original.sort_order
    )

    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)

    return duplicate
