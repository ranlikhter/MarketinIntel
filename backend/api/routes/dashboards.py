"""
Dashboards API Routes

CRUD for dashboards + widgets, plus the widget-data endpoint that powers
all chart/KPI renders on the frontend.

Routes:
  GET    /api/dashboards                        list user's dashboards
  POST   /api/dashboards                        create dashboard
  GET    /api/dashboards/{id}                   get dashboard + widgets
  PUT    /api/dashboards/{id}                   rename / update dashboard
  DELETE /api/dashboards/{id}                   delete dashboard
  POST   /api/dashboards/{id}/widgets           add widget
  PUT    /api/dashboards/{id}/widgets/{wid}     update widget config/position/size
  DELETE /api/dashboards/{id}/widgets/{wid}     remove widget
  PUT    /api/dashboards/{id}/layout            bulk-save widget positions after drag
  GET    /api/dashboards/widget-data/{type}     fetch rendered data for a widget type
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from database.models import Dashboard, DashboardWidget, User
from services.dashboard_data_service import get_widget_data, WIDGET_DISPATCH

router = APIRouter()


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class DashboardWidgetCreate(BaseModel):
    widget_type: str
    title: Optional[str] = None
    size: str = "medium"           # small | medium | large | tall-medium | tall-large
    config: Dict[str, Any] = {}


class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = None
    size: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position: Optional[int] = None


class LayoutItem(BaseModel):
    widget_id: int
    position: int


class DashboardWidgetResponse(BaseModel):
    id: int
    dashboard_id: int
    widget_type: str
    title: Optional[str]
    size: str
    position: int
    config: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    widgets: List[DashboardWidgetResponse] = []
    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    widget_count: int
    model_config = ConfigDict(from_attributes=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_dashboard_or_404(dashboard_id: int, user_id: int, db: Session) -> Dashboard:
    d = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        Dashboard.user_id == user_id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return d


def _unset_defaults(user_id: int, db: Session):
    db.query(Dashboard).filter(
        Dashboard.user_id == user_id,
        Dashboard.is_default == True,
    ).update({"is_default": False})


# ── Dashboard CRUD ─────────────────────────────────────────────────────────────

@router.get("/dashboards", response_model=List[DashboardSummaryResponse])
async def list_dashboards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dashboards = (
        db.query(Dashboard)
        .filter(Dashboard.user_id == current_user.id)
        .order_by(Dashboard.is_default.desc(), Dashboard.created_at.asc())
        .all()
    )
    return [
        DashboardSummaryResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            is_default=d.is_default,
            widget_count=len(d.widgets),
        )
        for d in dashboards
    ]


@router.post("/dashboards", response_model=DashboardResponse, status_code=201)
async def create_dashboard(
    payload: DashboardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.is_default:
        _unset_defaults(current_user.id, db)

    # If this is the user's first dashboard, make it the default automatically
    existing_count = db.query(Dashboard).filter(
        Dashboard.user_id == current_user.id
    ).count()
    is_default = payload.is_default or existing_count == 0

    dashboard = Dashboard(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        is_default=is_default,
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_dashboard_or_404(dashboard_id, current_user.id, db)


@router.put("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    payload: DashboardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard_or_404(dashboard_id, current_user.id, db)
    if payload.name is not None:
        d.name = payload.name
    if payload.description is not None:
        d.description = payload.description
    if payload.is_default is True:
        _unset_defaults(current_user.id, db)
        d.is_default = True
    db.commit()
    db.refresh(d)
    return d


@router.delete("/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = _get_dashboard_or_404(dashboard_id, current_user.id, db)
    db.delete(d)
    db.commit()


# ── Widget CRUD ────────────────────────────────────────────────────────────────

@router.post("/dashboards/{dashboard_id}/widgets",
             response_model=DashboardWidgetResponse, status_code=201)
async def add_widget(
    dashboard_id: int,
    payload: DashboardWidgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_dashboard_or_404(dashboard_id, current_user.id, db)

    if payload.widget_type not in WIDGET_DISPATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown widget type '{payload.widget_type}'. "
                   f"Valid: {list(WIDGET_DISPATCH)}"
        )

    # Place the new widget after existing ones
    max_pos = db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dashboard_id
    ).count()

    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        widget_type=payload.widget_type,
        title=payload.title,
        size=payload.size,
        config=payload.config,
        position=max_pos,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.put("/dashboards/{dashboard_id}/widgets/{widget_id}",
            response_model=DashboardWidgetResponse)
async def update_widget(
    dashboard_id: int,
    widget_id: int,
    payload: DashboardWidgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_dashboard_or_404(dashboard_id, current_user.id, db)
    w = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.dashboard_id == dashboard_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")

    if payload.title is not None:
        w.title = payload.title
    if payload.size is not None:
        w.size = payload.size
    if payload.config is not None:
        w.config = {**w.config, **payload.config}
    if payload.position is not None:
        w.position = payload.position
    db.commit()
    db.refresh(w)
    return w


@router.delete("/dashboards/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def delete_widget(
    dashboard_id: int,
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_dashboard_or_404(dashboard_id, current_user.id, db)
    w = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.dashboard_id == dashboard_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    db.delete(w)
    db.commit()


@router.put("/dashboards/{dashboard_id}/layout", status_code=204)
async def save_layout(
    dashboard_id: int,
    layout: List[LayoutItem],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk-update widget positions after a drag-to-reorder."""
    _get_dashboard_or_404(dashboard_id, current_user.id, db)
    for item in layout:
        db.query(DashboardWidget).filter(
            DashboardWidget.id == item.widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        ).update({"position": item.position})
    db.commit()


# ── Widget data endpoint ───────────────────────────────────────────────────────

@router.get("/dashboards/widget-data/{widget_type}")
async def fetch_widget_data(
    widget_type: str,
    product_id: int = Query(..., description="Product to analyze"),
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    metric: str = Query("price", description="price | effective_price | bsr | rating"),
    competitors: Optional[str] = Query(None, description="Comma-separated competitor names to filter"),
    color_scheme: str = Query("rainbow", description="blue|green|purple|orange|rainbow"),
    pie_metric: str = Query("fulfillment_type", description="fulfillment_type|price_range|stock_status|badges"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if widget_type not in WIDGET_DISPATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown widget type '{widget_type}'. Valid: {list(WIDGET_DISPATCH)}"
        )

    config = {
        "days": days,
        "metric": metric,
        "color_scheme": color_scheme,
        "pie_metric": pie_metric,
        "competitors": [c.strip() for c in competitors.split(",")] if competitors else [],
    }

    data = get_widget_data(db, widget_type, product_id, config)
    if "error" in data:
        raise HTTPException(status_code=500, detail=data["error"])
    return data
