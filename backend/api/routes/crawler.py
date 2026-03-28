"""
Site Crawler API Endpoints
Automatically discover and scrape competitor websites.

Security:
- All endpoints require authentication.
- URLs are validated against SSRF to prevent crawling internal infrastructure.
- Rate-limited to 10 crawl starts per hour (expensive operation).
- Job state includes owner_id; status endpoints reject mismatched users.

Async job system:
- POST /crawler/start  enqueues a Celery task and returns job_id immediately.
- GET  /crawler/status/{job_id} reads progress from Redis (async client).
"""

import json
import logging
import os
import uuid
from typing import Optional

import redis.asyncio as _redis_async
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from api.limiter import limiter
from database.connection import get_db
from database.models import CompetitorWebsite, User
from scrapers.site_crawler import SiteCrawler
from services.ssrf_validator import validate_external_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawler", tags=["crawler"])

# ── Async Redis helpers (used in FastAPI route handlers) ─────────────────────

def _get_async_redis():
    return _redis_async.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )


_JOB_TTL = 86_400


async def _set_job(r, job_id: str, data: dict) -> None:
    await r.set(f"crawl_jobs:{job_id}", json.dumps(data), ex=_JOB_TTL)


async def _get_job(r, job_id: str) -> Optional[dict]:
    raw = await r.get(f"crawl_jobs:{job_id}")
    return json.loads(raw) if raw else None


# ── Pydantic models ───────────────────────────────────────────────────────────

class CrawlRequest(BaseModel):
    base_url: HttpUrl
    max_products: Optional[int] = 50
    max_depth: Optional[int] = 3
    max_pages: Optional[int] = 500
    auto_import: Optional[bool] = True
    competitor_name: Optional[str] = None


class MapRequest(BaseModel):
    base_url: HttpUrl
    max_urls: Optional[int] = 500


class CrawlJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class CrawlStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: float = 0.0
    pages_visited: int = 0
    products_found: int = 0
    categories_found: int = 0
    products_imported: int = 0
    error: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start", response_model=CrawlJobResponse)
@limiter.limit("10/hour")
async def start_site_crawl(
    request: Request,
    crawl_request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enqueue an async site crawl. Returns **job_id** immediately.
    Poll `GET /crawler/status/{job_id}` for live progress.
    """
    base_url_str = str(crawl_request.base_url)
    validate_external_url(base_url_str, field_name="base_url")

    competitor_id = None
    if crawl_request.competitor_name:
        competitor = db.query(CompetitorWebsite).filter(
            CompetitorWebsite.name == crawl_request.competitor_name,
            CompetitorWebsite.user_id == current_user.id,
        ).first()
        if not competitor:
            competitor = CompetitorWebsite(
                user_id=current_user.id,
                name=crawl_request.competitor_name,
                base_url=base_url_str,
                website_type="auto_discovered",
            )
            db.add(competitor)
            db.commit()
            db.refresh(competitor)
        competitor_id = competitor.id

    job_id = str(uuid.uuid4())
    r = _get_async_redis()
    try:
        await _set_job(r, job_id, {
            "job_id": job_id,
            "user_id": current_user.id,
            "status": "running",
            "progress_pct": 0.0,
            "pages_visited": 0,
            "products_found": 0,
            "categories_found": 0,
            "products_imported": 0,
            "base_url": base_url_str,
            "error": None,
        })
    finally:
        await r.aclose()

    # Dispatch to Celery — survives process restarts
    from tasks.crawl_tasks import crawl_site_task
    crawl_site_task.delay(
        job_id=job_id,
        base_url=base_url_str,
        max_products=crawl_request.max_products or 50,
        max_depth=crawl_request.max_depth or 3,
        max_pages=crawl_request.max_pages or 500,
        auto_import=crawl_request.auto_import if crawl_request.auto_import is not None else True,
        competitor_id=competitor_id,
        user_id=current_user.id,
    )

    return CrawlJobResponse(
        job_id=job_id,
        status="running",
        message=f"Crawl started for {base_url_str}. Poll /crawler/status/{job_id} for progress.",
    )


@router.get("/status/{job_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get live status of a crawl job from Redis."""
    r = _get_async_redis()
    try:
        job = await _get_job(r, job_id)
    finally:
        await r.aclose()

    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    if job.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised to view this job")

    return CrawlStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress_pct=float(job.get("progress_pct", 0)),
        pages_visited=int(job.get("pages_visited", 0)),
        products_found=int(job.get("products_found", 0)),
        categories_found=int(job.get("categories_found", 0)),
        products_imported=int(job.get("products_imported", 0)),
        error=job.get("error"),
    )


@router.post("/map")
@limiter.limit("30/hour")
async def map_site(
    request: Request,
    map_request: MapRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Instantly discover all URLs on a website without scraping content.
    Checks sitemap.xml first, then scrapes homepage links.
    """
    base_url_str = str(map_request.base_url)
    validate_external_url(base_url_str, field_name="base_url")

    try:
        crawler = SiteCrawler()
        return await crawler.map_site(base_url_str, max_urls=map_request.max_urls or 500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover-categories")
@limiter.limit("20/hour")
async def discover_categories(
    request: Request,
    crawl_request: CrawlRequest,
    current_user: User = Depends(get_current_user),
):
    """Quickly discover category pages without scraping products."""
    base_url_str = str(crawl_request.base_url)
    validate_external_url(base_url_str, field_name="base_url")

    try:
        crawler = SiteCrawler()
        categories = await crawler.discover_categories(base_url_str)
        return {
            "success": True,
            "base_url": base_url_str,
            "categories_found": len(categories),
            "categories": categories,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
