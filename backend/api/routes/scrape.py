"""
Unified Scrape API — Firecrawl-compatible surface

Provides a clean, Firecrawl-equivalent API:

  POST /scrape            – Single URL extraction (JSON, markdown, or screenshot)
  POST /scrape/crawl      – Async full-site crawl, returns job_id immediately
  POST /scrape/map        – Fast URL map (no content scraping)
  POST /scrape/agent      – Natural-language AI extraction via Claude
  GET  /scrape/jobs/{id}  – Poll async crawl job status

Security:
  - All endpoints require authentication.
  - URLs validated against SSRF.
  - Rate limited per endpoint cost.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from api.dependencies import get_current_user
from api.limiter import limiter
from database.models import User
from scrapers.ai_extractor import AIExtractor
from scrapers.generic_scraper import GenericWebScraper
from scrapers.site_crawler import SiteCrawler
from scrapers.browser_pool import BrowserPool
from api.routes.crawler import (
    _get_redis,
    _get_job,
    _set_job,
    _run_crawl_job,
    CrawlStatusResponse,
)
from services.ssrf_validator import validate_external_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["scrape"])


# ── Request / Response models ─────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: HttpUrl
    # Selectors (optional — auto-detect if omitted)
    price_selector: Optional[str] = None
    title_selector: Optional[str] = None
    stock_selector: Optional[str] = None
    image_selector: Optional[str] = None
    # Render mode
    use_javascript: Optional[bool] = None   # None = auto
    # Output options
    output_format: str = "json"             # "json" | "markdown"
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
    Scrape a single URL and return structured product data, markdown, or a
    base64 screenshot — equivalent to Firecrawl's `/scrape` endpoint.

    **output_format**:
    - `json` (default) – returns structured product fields (price, title, …)
    - `markdown` – returns clean LLM-ready markdown of the page content

    **capture_screenshot**: include a base64 full-page PNG in the response.
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Start an async full-site crawl. Returns a **job_id** immediately.

    Poll `GET /scrape/jobs/{job_id}` for live progress.
    Equivalent to Firecrawl's `/crawl` endpoint.
    """
    url_str = str(body.url)
    validate_external_url(url_str, field_name="url")

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
        "base_url": url_str,
        "error": None,
    })

    background_tasks.add_task(
        _run_crawl_job,
        job_id=job_id,
        base_url=url_str,
        max_products=body.max_pages or 50,
        max_depth=body.max_depth or 3,
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
    """
    Poll the status of an async crawl job.
    Equivalent to Firecrawl's crawl status polling endpoint.
    """
    r = _get_redis()
    job = _get_job(r, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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

    Checks `sitemap.xml` first, then scrapes links from the homepage.
    Returns a flat list of URLs in seconds.
    Equivalent to Firecrawl's `/map` endpoint.
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

    Fetches the page, converts it to markdown, then uses Claude to extract
    exactly what you describe in the `prompt` field — no CSS selectors needed.
    Equivalent to Firecrawl's `/agent` endpoint.

    **prompt**: e.g. `"Extract product name, current price, was-price, and whether
    it is in stock as a JSON object"`

    **schema**: Optional JSON schema to constrain the output shape.
    """
    url_str = str(body.url)
    validate_external_url(url_str, field_name="url")

    extractor = AIExtractor()
    result = await extractor.extract(
        url=url_str,
        prompt=body.prompt,
        schema=body.schema,
        include_markdown=body.include_markdown,
    )

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    return result
