"""
Discovery Background Tasks

Celery tasks for auto-matching monitored products against competitor websites.
Each task crawls one or more competitor sites for a single product, scores
candidates with SimpleProductMatcher, and persists confirmed matches to the DB.
"""

import asyncio
import logging
from typing import List
from urllib.parse import urlparse

from celery_app import celery_app
from database.connection import SessionLocal
from database.models import (
    CompetitorMatch,
    CompetitorWebsite,
    ProductMonitored,
)
from matchers.simple_matcher import SimpleProductMatcher
from scrapers.site_crawler import SiteCrawler

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.discovery_tasks.auto_match_product_task",
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=1800,   # 30 min — crawling is slow
    time_limit=2100,        # 35 min hard cap
)
def auto_match_product_task(
    self,
    product_id: int,
    site_ids: List[int],
    min_confidence: float = 0.7,
) -> dict:
    """
    Crawl each competitor site and persist matches for *product_id*.

    Args:
        product_id:     ID of the ProductMonitored row to match.
        site_ids:       List of CompetitorWebsite IDs to crawl.
        min_confidence: Minimum SimpleProductMatcher score (0.0–1.0).

    Returns:
        Dict summarising how many matches were created / skipped.
    """
    db = SessionLocal()
    try:
        product = db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id
        ).first()
        if not product:
            logger.warning("auto_match_product_task: product %d not found", product_id)
            return {"product_id": product_id, "error": "product not found"}

        sites = db.query(CompetitorWebsite).filter(
            CompetitorWebsite.id.in_(site_ids),
            CompetitorWebsite.is_active == True,  # noqa: E712
        ).all()

        if not sites:
            return {"product_id": product_id, "sites_checked": 0, "matches_created": 0}

        # Build the reference dict that the matcher expects
        product_ref = {
            "title":       product.title,
            "brand":       product.brand or "",
            "description": product.description or "",
            "mpn":         product.mpn or "",
            "upc_ean":     product.upc_ean or "",
        }

        matcher = SimpleProductMatcher(threshold=min_confidence)
        matches_created = 0
        matches_skipped = 0

        for site in sites:
            try:
                candidates = asyncio.run(_crawl_site(site.base_url))
            except Exception as exc:
                logger.warning(
                    "auto_match_product_task: crawl failed for %s: %s",
                    site.base_url, exc,
                )
                continue

            if not candidates:
                continue

            best = matcher.match(product_ref, candidates)
            if not best:
                continue

            # Check if this (product, URL) pair already exists
            competitor_url = best.get("url") or best.get("competitor_url", "")
            existing = db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id,
                CompetitorMatch.competitor_url == competitor_url,
            ).first()

            if existing:
                matches_skipped += 1
                continue

            site_name = site.name or _domain(site.base_url)
            match = CompetitorMatch(
                monitored_product_id=product_id,
                competitor_name=site_name,
                competitor_url=competitor_url,
                competitor_product_title=best.get("title", ""),
                match_score=round(best.get("match_score", 0.0) * 100, 1),
                latest_price=best.get("price"),
                stock_status=best.get("stock_status"),
                image_url=best.get("image_url"),
                competitor_website_id=site.id,
                brand=best.get("brand"),
                description=best.get("description"),
            )
            db.add(match)
            matches_created += 1

        db.commit()
        logger.info(
            "auto_match_product_task: product=%d created=%d skipped=%d",
            product_id, matches_created, matches_skipped,
        )
        return {
            "product_id": product_id,
            "sites_checked": len(sites),
            "matches_created": matches_created,
            "matches_skipped": matches_skipped,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("auto_match_product_task: unexpected error: %s", exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


async def _crawl_site(base_url: str, max_products: int = 50) -> list:
    """
    Run SiteCrawler against *base_url* and return normalised product dicts.

    Each dict has at minimum: title, url.
    Optional keys: price, brand, description, image_url, stock_status.
    """
    crawler = SiteCrawler(delay=1.0, concurrency=2)
    result = await crawler.crawl_site(base_url, max_products=max_products)

    raw_products = result.get("products", [])
    normalised = []
    for p in raw_products:
        title = p.get("title") or p.get("name") or ""
        if not title:
            continue
        normalised.append({
            "title":        title.strip(),
            "url":          p.get("url") or p.get("competitor_url") or "",
            "price":        _to_float(p.get("price")),
            "brand":        p.get("brand") or "",
            "description":  p.get("description") or "",
            "image_url":    p.get("image_url") or "",
            "stock_status": p.get("stock_status") or "Unknown",
        })
    return normalised


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url
