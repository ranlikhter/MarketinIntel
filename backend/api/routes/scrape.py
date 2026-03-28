"""
Unified Scrape API — Firecrawl-compatible surface

  POST /scrape            – Single URL extraction (JSON, markdown, or screenshot)
  POST /scrape/crawl      – Async full-site crawl via Celery, returns job_id
  POST /scrape/map        – Fast URL map (no content scraping)
  POST /scrape/agent      – Natural-language AI extraction via Claude
  GET  /scrape/jobs/{id}  – Poll async crawl job status

Security:
  - All endpoints require authentication.
  - URLs validated against SSRF.
  - Rate limited per endpoint cost.
  - Crawl job status checks ownership.
"""

import logging
import uuid
from typing import Any, Dict, Literal, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from api.dependencies import get_current_user
from api.limiter import limiter
from api.routes.crawler import (
    CrawlStatusResponse,
    _get_async_redis,
    _get_job,
    _set_job,
)
from database.models import User
from scrapers.ai_extractor import AIExtractor
from scrapers.browser_pool import BrowserPool
from scrapers.generic_scraper import GenericWebScraper
from scrapers.site_crawler import SiteCrawler
from services.ssrf_validator import validate_external_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["scrape"])


# ── Request / Response models ─────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: HttpUrl
    price_selector: Optional[str] = None
    title_selector: Optional[str] = None
    stock_selector: Optional[str] = None
    image_selector: Optional[str] = None
    use_javascript: Optional[bool] = None
    output_format: Literal["json", "markdown"] = "json"
    capture_screenshot: bool = False


class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = 50
    max_depth: Optional[int] = 3
    auto_import: Optional[bool] = False


class MapRequest(BaseModel):
    url: HttpUrl
    max_urls: Optional[int] = 500


class AgentRequest(BaseModel):
    url: HttpUrl
    prompt: str
    schema: Optional[Dict[str, Any]] = None
    include_markdown: bool = False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("")
@limiter.limit("100/hour")
async def scrape(
    request: Request,
    body: ScrapeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Scrape a single URL — returns structured JSON, LLM-ready markdown, or
    a base64 screenshot.  Equivalent to Firecrawl's `/scrape`.
    """
    url_str = str(body.url)
    validate_external_url(url_str, field_name="url")

    pool = BrowserPool(pool_size=1)
    try:
        scraper = GenericWebScraper(browser_pool=pool)
        result = await scraper.scrape_product(
            url=url_str,
            price_selector=body.price_selector,
            title_selector=body.title_selector,
            stock_selector=body.stock_selector,
            image_selector=body.image_selector,
            use_javascript=body.use_javascript,
            output_format=body.output_format,
            capture_screenshot=body.capture_screenshot,
        )
    finally:
        await pool.close()

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.post("/crawl")
@limiter.limit("10/hour")
async def crawl(
    request: Request,
    body: CrawlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Enqueue an async full-site crawl via Celery. Returns **job_id** immediately.
    Poll `GET /scrape/jobs/{job_id}` for live progress.
    Equivalent to Firecrawl's `/crawl`.
    """
    url_str = str(body.url)
    validate_external_url(url_str, field_name="url")

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
            "base_url": url_str,
            "error": None,
        })
    finally:
        await r.aclose()

    from tasks.crawl_tasks import crawl_site_task
    crawl_site_task.delay(
        job_id=job_id,
        base_url=url_str,
        max_products=body.max_pages or 50,
        max_depth=body.max_depth or 3,
        max_pages=body.max_pages or 50,
        auto_import=body.auto_import if body.auto_import is not None else False,
        competitor_id=None,
        user_id=current_user.id,
    )

    return {
        "job_id": job_id,
        "status": "running",
        "message": f"Crawl started. Poll /scrape/jobs/{job_id} for progress.",
    }


@router.get("/jobs/{job_id}", response_model=CrawlStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll the status of an async crawl job (ownership enforced)."""
    r = _get_async_redis()
    try:
        job = await _get_job(r, job_id)
    finally:
        await r.aclose()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
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
    body: MapRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Instantly discover all URLs on a website without scraping content.
    Equivalent to Firecrawl's `/map`.
    """
    url_str = str(body.url)
    validate_external_url(url_str, field_name="url")

    try:
        crawler = SiteCrawler()
        return await crawler.map_site(url_str, max_urls=body.max_urls or 500)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/agent")
@limiter.limit("20/hour")
async def agent_extract(
    request: Request,
    body: AgentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    AI-powered extraction using natural language.
    Equivalent to Firecrawl's `/agent`.
    """
    url_str = str(body.url)
    validate_external_url(url_str, field_name="url")

    async with AIExtractor() as extractor:
        result = await extractor.extract(
            url=url_str,
            prompt=body.prompt,
            schema=body.schema,
            include_markdown=body.include_markdown,
        )

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])
    return result
