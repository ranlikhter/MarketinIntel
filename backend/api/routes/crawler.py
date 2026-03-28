"""
Site Crawler API Endpoints
Automatically discover and scrape competitor websites.

Security:
- All endpoints require authentication.
- URLs are validated against SSRF to prevent crawling internal infrastructure.
- Rate-limited to 10 crawl starts per hour (expensive operation).

Async job system:
- POST /crawler/start  returns a job_id immediately; the crawl runs in the
  background and writes progress to Redis so it works across multiple workers.
- GET  /crawler/status/{job_id} polls Redis for live status.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

import redis as _redis_lib
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from api.limiter import limiter
from database.connection import get_db
from database.models import CompetitorMatch, CompetitorWebsite, ProductMonitored, User
from scrapers.site_crawler import SiteCrawler
from services.ssrf_validator import validate_external_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawler", tags=["crawler"])

# ── Redis job store ───────────────────────────────────────────────────────────

def _get_redis():
    """Return a Redis client using the same connection settings as Celery."""
    return _redis_lib.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )


_JOB_TTL = 86_400   # keep job state for 24 hours


def _set_job(r, job_id: str, data: dict):
    r.set(f"crawl_jobs:{job_id}", json.dumps(data), ex=_JOB_TTL)


def _get_job(r, job_id: str) -> Optional[dict]:
    raw = r.get(f"crawl_jobs:{job_id}")
    return json.loads(raw) if raw else None


# ── Pydantic models ───────────────────────────────────────────────────────────

class CrawlRequest(BaseModel):
    base_url: HttpUrl
    max_products: Optional[int] = 50
    max_depth: Optional[int] = 3
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


# ── Background crawl task ─────────────────────────────────────────────────────

async def _run_crawl_job(
    job_id: str,
    base_url: str,
    max_products: int,
    max_depth: int,
    auto_import: bool,
    competitor_id: Optional[int],
    user_id: int,
):
    """Background task: runs the crawl and updates Redis progress."""
    r = _get_redis()

    async def _progress(info: dict):
        current = _get_job(r, job_id) or {}
        current.update({
            "pages_visited": info.get("pages_visited", 0),
            "products_found": info.get("products_found", 0),
            "categories_found": info.get("categories_found", 0),
        })
        _set_job(r, job_id, current)

    try:
        crawler = SiteCrawler()
        result = await crawler.crawl_site(
            base_url=base_url,
            max_products=max_products,
            max_depth=max_depth,
            progress_callback=_progress,
        )

        if not result["success"]:
            _set_job(r, job_id, {
                **(_get_job(r, job_id) or {}),
                "status": "failed",
                "error": result.get("error", "Crawl failed"),
            })
            return

        # Auto-import discovered products
        products_imported = 0
        if auto_import and result.get("products"):
            from database.connection import SessionLocal
            db: Session = SessionLocal()
            try:
                competitor = None
                if competitor_id:
                    competitor = db.query(CompetitorWebsite).filter(
                        CompetitorWebsite.id == competitor_id
                    ).first()

                for product_data in result["products"]:
                    try:
                        existing = db.query(ProductMonitored).filter(
                            ProductMonitored.title == product_data["title"],
                            ProductMonitored.user_id == user_id,
                        ).first()
                        if not existing:
                            new_product = ProductMonitored(
                                user_id=user_id,
                                title=product_data["title"],
                                image_url=product_data.get("image_url"),
                            )
                            db.add(new_product)
                            db.commit()
                            db.refresh(new_product)
                            if competitor:
                                match = CompetitorMatch(
                                    monitored_product_id=new_product.id,
                                    competitor_website_id=competitor.id,
                                    competitor_name=competitor.name,
                                    competitor_url=product_data["url"],
                                    competitor_product_title=product_data["title"],
                                    latest_price=product_data.get("price"),
                                    stock_status=product_data.get("stock_status"),
                                    image_url=product_data.get("image_url"),
                                    last_scraped_at=datetime.utcnow(),
                                )
                                db.add(match)
                            products_imported += 1
                    except Exception as e:
                        logger.error("Error importing crawled product: %s", e)
                db.commit()
            finally:
                db.close()

        _set_job(r, job_id, {
            **(_get_job(r, job_id) or {}),
            "status": "completed",
            "products_found": result["products_found"],
            "categories_found": result["categories_found"],
            "products_imported": products_imported,
            "progress_pct": 100.0,
        })

    except Exception as e:
        logger.error("Crawl job %s failed: %s", job_id, e)
        _set_job(r, job_id, {
            **(_get_job(r, job_id) or {}),
            "status": "failed",
            "error": str(e),
        })


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
    Start an async site crawl to discover all products.

    Returns a **job_id** immediately. Poll `GET /crawler/status/{job_id}` for
    progress.  Results are written to the database as the crawl progresses.

    - **base_url**: Competitor website URL (must be a public, external host)
    - **max_products**: Maximum products to discover (default: 50)
    - **max_depth**: Crawl depth (default: 3)
    - **auto_import**: Automatically import discovered products (default: true)
    - **competitor_name**: Name for the competitor website entry
    """
    base_url_str = str(crawl_request.base_url)
    validate_external_url(base_url_str, field_name="base_url")

    # Look up or create competitor entry
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
    r = _get_redis()
    _set_job(r, job_id, {
        "job_id": job_id,
        "status": "running",
        "progress_pct": 0.0,
        "pages_visited": 0,
        "products_found": 0,
        "categories_found": 0,
        "products_imported": 0,
        "base_url": base_url_str,
        "error": None,
    })

    background_tasks.add_task(
        _run_crawl_job,
        job_id=job_id,
        base_url=base_url_str,
        max_products=crawl_request.max_products or 50,
        max_depth=crawl_request.max_depth or 3,
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
    r = _get_redis()
    job = _get_job(r, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found")

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

    Much faster than a full crawl — loads the homepage and sitemap.xml, then
    returns a flat list of discovered URLs.  Useful for planning what to scrape.

    - **base_url**: Website to map (must be a public, external host)
    - **max_urls**: Maximum URLs to return (default: 500)
    """
    base_url_str = str(map_request.base_url)
    validate_external_url(base_url_str, field_name="base_url")

    try:
        crawler = SiteCrawler()
        result = await crawler.map_site(
            base_url=base_url_str,
            max_urls=map_request.max_urls or 500,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover-categories")
@limiter.limit("20/hour")
async def discover_categories(
    request: Request,
    crawl_request: CrawlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Quickly discover category pages without scraping products.

    - **base_url**: Competitor website URL (must be a public, external host)
    """
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
