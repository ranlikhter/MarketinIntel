"""
Celery task for async site crawl jobs.

Moved out of FastAPI BackgroundTasks so that:
  - Jobs survive process restarts / redeploys
  - Celery enforces time limits and retries
  - Redis state is always updated even if a worker dies
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional

import redis as _redis_sync

from celery_app import celery_app
from database.connection import SessionLocal
from database.models import CompetitorMatch, CompetitorWebsite, ProductMonitored
from scrapers.site_crawler import SiteCrawler

logger = logging.getLogger(__name__)

_JOB_TTL = 86_400   # 24 h


# ── Sync Redis helpers (used inside Celery worker thread) ─────────────────────

def _redis_client():
    return _redis_sync.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )


def _set_job(r, job_id: str, data: dict):
    r.set(f"crawl_jobs:{job_id}", json.dumps(data), ex=_JOB_TTL)


def _get_job(r, job_id: str) -> Optional[dict]:
    raw = r.get(f"crawl_jobs:{job_id}")
    return json.loads(raw) if raw else None


# ── Celery task ───────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.crawl_site_task",
    max_retries=0,           # don't auto-retry crawls — they're expensive
    time_limit=3600,         # hard kill at 1 h
    soft_time_limit=3000,    # SoftTimeLimitExceeded at 50 min
    acks_late=True,
)
def crawl_site_task(
    self,
    job_id: str,
    base_url: str,
    max_products: int,
    max_depth: int,
    max_pages: int,
    auto_import: bool,
    competitor_id: Optional[int],
    user_id: int,
):
    """
    Run a full-site crawl in a Celery worker and write progress to Redis.
    """
    asyncio.run(
        _async_crawl(
            job_id=job_id,
            base_url=base_url,
            max_products=max_products,
            max_depth=max_depth,
            max_pages=max_pages,
            auto_import=auto_import,
            competitor_id=competitor_id,
            user_id=user_id,
        )
    )


async def _async_crawl(
    job_id: str,
    base_url: str,
    max_products: int,
    max_depth: int,
    max_pages: int,
    auto_import: bool,
    competitor_id: Optional[int],
    user_id: int,
):
    r = _redis_client()

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
            max_pages=max_pages,
            progress_callback=_progress,
        )

        if not result["success"]:
            _set_job(r, job_id, {
                **(_get_job(r, job_id) or {}),
                "status": "failed",
                "error": result.get("error", "Crawl failed"),
            })
            return

        products_imported = 0
        if auto_import and result.get("products"):
            db = SessionLocal()
            try:
                competitor = (
                    db.query(CompetitorWebsite).filter_by(id=competitor_id).first()
                    if competitor_id else None
                )
                for product_data in result["products"]:
                    try:
                        existing = db.query(ProductMonitored).filter_by(
                            title=product_data["title"],
                            user_id=user_id,
                        ).first()
                        if not existing:
                            new_product = ProductMonitored(
                                user_id=user_id,
                                title=product_data["title"],
                                image_url=product_data.get("image_url"),
                            )
                            db.add(new_product)
                            db.flush()          # get PK without committing
                            if competitor:
                                db.add(CompetitorMatch(
                                    monitored_product_id=new_product.id,
                                    competitor_website_id=competitor.id,
                                    competitor_name=competitor.name,
                                    competitor_url=product_data["url"],
                                    competitor_product_title=product_data["title"],
                                    latest_price=product_data.get("price"),
                                    stock_status=product_data.get("stock_status"),
                                    image_url=product_data.get("image_url"),
                                    last_scraped_at=datetime.utcnow(),
                                ))
                            db.commit()
                            products_imported += 1
                    except Exception as e:
                        db.rollback()
                        logger.exception("Error importing crawled product: %s", e)
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
        logger.exception("Crawl job %s failed: %s", job_id, e)
        _set_job(r, job_id, {
            **(_get_job(r, job_id) or {}),
            "status": "failed",
            "error": str(e),
        })
