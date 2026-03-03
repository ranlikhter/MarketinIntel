"""
Scraping Background Tasks
Handles automated product scraping via Celery workers.

Key improvements over the original:
  - asyncio.run() instead of manual new_event_loop() / set_event_loop() /
    loop.close() to avoid event-loop leaks and deprecation warnings.
  - A BrowserPool is created once per task invocation and shared across all
    scrape calls within that task, eliminating per-call browser startup cost.
  - Retry backoff starts at 10 s (not 60 s) so transient errors recover fast.
  - scrape_all_products uses .yield_per() / .limit() to avoid loading the
    entire products table into memory at once.
  - retry_failed_scrapes targets matches that have had NO price-history
    recorded in the last 24 h (i.e. actually failed), not just stale ones.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from celery import Task
from celery_app import celery_app
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import (
    ProductMonitored,
    CompetitorMatch,
    PriceHistory,
    CompetitorWebsite,
    CompetitorPromotion,
)
from scrapers.amazon_scraper import AmazonScraper
from scrapers.browser_pool import BrowserPool
from matchers.simple_matcher import SimpleProductMatcher

logger = logging.getLogger(__name__)

# ── Per-task page budget (caps memory / time per Celery worker slot) ──────────
_SEARCH_RESULTS_PER_PRODUCT = 5
_BULK_SCRAPE_PAGE_SIZE = 100   # products loaded per DB query in scrape_all_products


# ── Base task ─────────────────────────────────────────────────────────────────

class DatabaseTask(Task):
    """Base task with lazy database session creation and guaranteed cleanup."""

    _db: Session = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


# ── Core async logic ──────────────────────────────────────────────────────────

async def _run_scrape_for_product(product, competitor_id) -> dict:
    """
    Async work for a single product scrape.

    Creates one BrowserPool for the lifetime of this async call so all
    Playwright page loads within the call share the same browser process.
    """
    pool = BrowserPool(pool_size=1)
    try:
        scraper = AmazonScraper(browser_pool=pool)
        matcher = SimpleProductMatcher()

        results = await scraper.search_products(
            product.title, max_results=_SEARCH_RESULTS_PER_PRODUCT
        )

        if isinstance(results, dict) and "error" in results:
            raise RuntimeError(results["error"])

        items = results if isinstance(results, list) else []

        product_dict = {
            "title": product.title or "",
            "brand": product.brand or "",
            "description": product.description or "",
            "mpn": product.mpn or "",
            "upc_ean": product.upc_ean or "",
        }

        return {"items": items, "product_dict": product_dict}

    finally:
        await pool.close()


# ── Celery tasks ──────────────────────────────────────────────────────────────

@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def scrape_single_product(self, product_id: int, website: str = "amazon.com"):
    """
    Scrape a single monitored product from a competitor website.
    """
    try:
        logger.info("Starting scrape for product %d on %s", product_id, website)

        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id
        ).first()

        if not product:
            logger.error("Product %d not found", product_id)
            return {"success": False, "error": "Product not found"}

        competitor = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.base_url.contains(website)
        ).first()

        if "amazon" not in website.lower():
            return {"success": False, "error": f"Unsupported website: {website}"}

        # Run all async work (pool lifecycle, search, optional detail scrapes)
        # inside a single asyncio.run() call so the pool is properly cleaned up.
        scrape_result = asyncio.run(_run_scrape_for_product(product, competitor))

        items = scrape_result["items"]
        product_dict = scrape_result["product_dict"]
        matcher = SimpleProductMatcher()
        matches_found = 0
        now = datetime.utcnow()

        for item in items:
            candidate_dict = {
                "title": item.get("title", ""),
                "brand": item.get("brand", ""),
                "description": item.get("description", ""),
                "mpn": item.get("mpn", ""),
                "upc_ean": item.get("upc_ean", ""),
            }

            match_score = matcher._calculate_similarity(product_dict, candidate_dict)
            if match_score < 0.7:
                continue

            item_url = item.get("url", "")
            if not item_url:
                continue

            existing = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id,
                CompetitorMatch.competitor_url == item_url,
            ).first()

            if existing:
                existing.latest_price = item.get("price")
                existing.stock_status = item.get("stock_status")
                existing.last_scraped_at = now
                existing.match_score = match_score
                existing.external_id = item.get("asin") or existing.external_id
                existing.rating = item.get("rating")
                existing.review_count = item.get("review_count")
                existing.is_prime = item.get("is_prime")
                existing.fulfillment_type = item.get("fulfillment_type")
                existing.product_condition = item.get("product_condition") or existing.product_condition
                existing.seller_name = item.get("seller_name")
                existing.seller_count = item.get("seller_count")
                existing.category = item.get("category") or existing.category
                existing.variant = item.get("variant")
                existing.brand = existing.brand or item.get("brand")
                existing.description = existing.description or item.get("description")
                existing.mpn = existing.mpn or item.get("mpn")
                existing.upc_ean = existing.upc_ean or item.get("upc_ean")
                existing.image_url = item.get("image_url") or existing.image_url
                match = existing
            else:
                match = CompetitorMatch(
                    monitored_product_id=product_id,
                    competitor_website_id=competitor.id if competitor else None,
                    competitor_name=website,
                    competitor_url=item_url,
                    competitor_product_title=item.get("title", ""),
                    latest_price=item.get("price"),
                    stock_status=item.get("stock_status"),
                    image_url=item.get("image_url"),
                    match_score=match_score,
                    last_scraped_at=now,
                    external_id=item.get("asin"),
                    rating=item.get("rating"),
                    review_count=item.get("review_count"),
                    is_prime=item.get("is_prime"),
                    fulfillment_type=item.get("fulfillment_type"),
                    product_condition=item.get("product_condition"),
                    seller_name=item.get("seller_name"),
                    seller_count=item.get("seller_count"),
                    category=item.get("category"),
                    variant=item.get("variant"),
                    brand=item.get("brand"),
                    description=item.get("description"),
                    mpn=item.get("mpn"),
                    upc_ean=item.get("upc_ean"),
                )
                self.db.add(match)
                self.db.flush()

            if item.get("price"):
                self.db.add(PriceHistory(
                    match_id=match.id,
                    price=item["price"],
                    currency=item.get("currency", "USD"),
                    in_stock=item.get("in_stock", True),
                    timestamp=now,
                    was_price=item.get("was_price"),
                    discount_pct=item.get("discount_pct"),
                    shipping_cost=item.get("shipping_cost"),
                    total_price=item.get("total_price"),
                    promotion_label=item.get("promotion_label"),
                    seller_name=item.get("seller_name"),
                    seller_count=item.get("seller_count"),
                    scrape_quality=item.get("scrape_quality"),
                    rating=item.get("rating"),
                    review_count=item.get("review_count"),
                    is_prime=item.get("is_prime"),
                    fulfillment_type=item.get("fulfillment_type"),
                    product_condition=item.get("product_condition"),
                ))

            _upsert_promotions(self.db, match.id, item.get("promotions") or [])
            matches_found += 1

        self.db.commit()
        logger.info("Scraped product %d: %d match(es)", product_id, matches_found)

        return {
            "success": True,
            "product_id": product_id,
            "matches_found": matches_found,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Error scraping product %d: %s", product_id, e)
        # Backoff: 10 s, 20 s, 40 s — much more reasonable than the original 60/120/240 s
        raise self.retry(exc=e, countdown=10 * (2 ** self.request.retries))


@celery_app.task(base=DatabaseTask, bind=True)
def scrape_all_products(self):
    """
    Queue scrape tasks for every active monitored product.

    Uses paginated queries so we never load the whole products table at once.
    """
    try:
        logger.info("Starting bulk scrape for all products")

        task_ids = []
        offset = 0

        while True:
            page = (
                self.db.query(ProductMonitored)
                .limit(_BULK_SCRAPE_PAGE_SIZE)
                .offset(offset)
                .all()
            )
            if not page:
                break
            for product in page:
                task = scrape_single_product.delay(product.id)
                task_ids.append(task.id)
            offset += _BULK_SCRAPE_PAGE_SIZE

        if not task_ids:
            logger.warning("No products found to scrape")
            return {"success": True, "message": "No products to scrape"}

        logger.info("Queued %d scraping tasks", len(task_ids))
        return {
            "success": True,
            "products_queued": len(task_ids),
            "task_ids": task_ids,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Error in bulk scrape: %s", e)
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def scrape_products_by_priority(self):
    """
    Scrape products whose competitor data has gone stale (> 24 h old).
    """
    try:
        logger.info("Starting priority-based scraping")

        cutoff = datetime.utcnow() - timedelta(hours=24)
        stale = (
            self.db.query(ProductMonitored)
            .join(CompetitorMatch)
            .filter(CompetitorMatch.last_scraped_at < cutoff)
            .distinct()
            .limit(50)
            .all()
        )

        task_ids = [scrape_single_product.delay(p.id).id for p in stale]
        logger.info("Queued %d priority tasks", len(task_ids))

        return {
            "success": True,
            "priority_products_queued": len(task_ids),
            "task_ids": task_ids,
        }

    except Exception as e:
        logger.error("Error in priority scraping: %s", e)
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def retry_failed_scrapes(self):
    """
    Re-queue products whose last scrape produced no price-history entry in
    the past 24 hours (i.e. the scrape ran but yielded nothing useful).
    """
    try:
        logger.info("Retrying failed scrapes")

        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Products that have competitor matches but no recent price history
        failed_match_ids = (
            self.db.query(CompetitorMatch.monitored_product_id)
            .outerjoin(
                PriceHistory,
                (PriceHistory.match_id == CompetitorMatch.id)
                & (PriceHistory.timestamp >= cutoff),
            )
            .filter(PriceHistory.id.is_(None))
            .distinct()
            .limit(20)
            .all()
        )

        product_ids = [row[0] for row in failed_match_ids]
        task_ids = [scrape_single_product.delay(pid).id for pid in product_ids]

        logger.info("Queued %d retry tasks", len(task_ids))
        return {
            "success": True,
            "retries_queued": len(task_ids),
            "task_ids": task_ids,
        }

    except Exception as e:
        logger.error("Error retrying failed scrapes: %s", e)
        return {"success": False, "error": str(e)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upsert_promotions(db, match_id: int, promotions: list):
    """
    Sync the competitor_promotions table with freshly scraped promo data.

    Active promos that disappeared are deactivated; new ones are inserted;
    returning ones get their last_seen_at updated.
    """
    now = datetime.utcnow()

    db.query(CompetitorPromotion).filter_by(match_id=match_id, is_active=True).update(
        {"is_active": False}, synchronize_session=False
    )

    for p in promotions:
        desc = (p.get("description") or "").strip()[:500]
        if not desc:
            continue

        existing = (
            db.query(CompetitorPromotion)
            .filter_by(match_id=match_id, description=desc)
            .first()
        )
        if existing:
            existing.is_active = True
            existing.last_seen_at = now
        else:
            db.add(CompetitorPromotion(
                match_id=match_id,
                promo_type=p.get("promo_type") or "other",
                description=desc,
                buy_qty=p.get("buy_qty"),
                get_qty=p.get("get_qty"),
                discount_pct=p.get("discount_pct"),
                free_item_name=p.get("free_item_name"),
                first_seen_at=now,
                last_seen_at=now,
                is_active=True,
            ))
