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
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import (
    ProductMonitored,
    CompetitorMatch,
    PriceHistory,
    CompetitorWebsite,
    CompetitorPromotion,
    ReviewSnapshot,
    SellerProfile,
    ListingQualitySnapshot,
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

        # ── Pre-batch DB reads so the item loop makes zero extra queries ──────
        # 1. All existing competitor matches for this product, keyed by URL
        existing_by_url = {
            m.competitor_url: m
            for m in self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id
            ).all()
        }

        # 2. Latest recorded price per match (for price-change deduplication).
        #    Uses a MAX(timestamp) subquery — SQLite-compatible.
        existing_latest_price: dict[int, float] = {}
        if existing_by_url:
            existing_ids = [m.id for m in existing_by_url.values()]
            subq = (
                self.db.query(
                    PriceHistory.match_id,
                    func.max(PriceHistory.timestamp).label("max_ts"),
                )
                .filter(PriceHistory.match_id.in_(existing_ids))
                .group_by(PriceHistory.match_id)
                .subquery()
            )
            for row in (
                self.db.query(PriceHistory.match_id, PriceHistory.price)
                .join(
                    subq,
                    (PriceHistory.match_id == subq.c.match_id)
                    & (PriceHistory.timestamp == subq.c.max_ts),
                )
                .all()
            ):
                existing_latest_price[row.match_id] = row.price
        # ─────────────────────────────────────────────────────────────────────

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

            match_method = _detect_match_method(product_dict, candidate_dict)
            brand_equal = _brands_match(product_dict, candidate_dict)

            existing = existing_by_url.get(item_url)

            if existing:
                existing.latest_price = item.get("price")
                existing.stock_status = item.get("stock_status")
                existing.last_scraped_at = now
                existing.match_score = match_score
                existing.match_method = match_method
                existing.title_similarity = match_score
                existing.brand_match = brand_equal
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
                # Tier 1 — Effective pricing
                existing.subscribe_save_price = item.get("subscribe_save_price")
                existing.coupon_value = item.get("coupon_value")
                existing.coupon_pct = item.get("coupon_pct")
                existing.effective_price = item.get("effective_price")
                existing.is_lightning_deal = item.get("is_lightning_deal")
                existing.deal_end_time = item.get("deal_end_time")
                existing.stock_quantity = item.get("stock_quantity")
                existing.low_stock_warning = item.get("low_stock_warning")
                existing.best_seller_rank = item.get("best_seller_rank")
                existing.best_seller_rank_category = (
                    item.get("best_seller_rank_category") or existing.best_seller_rank_category
                )
                # Tier 2 — Demand & visibility
                existing.units_sold_past_month = item.get("units_sold_past_month")
                existing.badge_amazons_choice = item.get("badge_amazons_choice")
                existing.badge_best_seller = item.get("badge_best_seller")
                existing.badge_new_release = item.get("badge_new_release")
                existing.is_sponsored = item.get("is_sponsored")
                existing.rating_distribution = item.get("rating_distribution")
                # Tier 3 — Product attributes (keep existing if scrape didn't return them)
                existing.specifications = item.get("specifications") or existing.specifications
                existing.variant_options = item.get("variant_options") or existing.variant_options
                existing.date_first_available = (
                    item.get("date_first_available") or existing.date_first_available
                )
                # Gap 1 — Seller Intelligence
                existing.amazon_is_seller = item.get("amazon_is_seller")
                existing.seller_feedback_count = item.get("seller_feedback_count")
                existing.seller_positive_feedback_pct = item.get("seller_positive_feedback_pct")
                existing.lowest_new_offer_price = item.get("lowest_new_offer_price")
                existing.number_of_used_offers = item.get("number_of_used_offers")
                # Gap 2 — Listing Quality
                existing.image_count = item.get("image_count")
                existing.has_video = item.get("has_video")
                existing.has_aplus_content = item.get("has_aplus_content")
                existing.has_brand_story = item.get("has_brand_story")
                existing.bullet_point_count = item.get("bullet_point_count")
                existing.title_char_count = item.get("title_char_count")
                existing.questions_count = item.get("questions_count")
                existing.listing_quality_score = _compute_listing_score(item)
                # Gap 3 — Delivery
                existing.delivery_fastest_days = item.get("delivery_fastest_days")
                existing.delivery_standard_days = item.get("delivery_standard_days")
                existing.has_same_day = item.get("has_same_day")
                existing.ships_from_location = item.get("ships_from_location")
                existing.has_free_returns = item.get("has_free_returns")
                existing.return_window_days = item.get("return_window_days")
                # Gap 4 — Variations
                existing.parent_asin = item.get("parent_asin") or existing.parent_asin
                existing.total_variations = item.get("total_variations")
                existing.is_best_seller_variation = item.get("is_best_seller_variation")
                # Gap 5 — Extended Badges
                existing.climate_pledge_friendly = item.get("climate_pledge_friendly")
                existing.small_business_badge = item.get("small_business_badge")
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
                    match_method=match_method,
                    title_similarity=match_score,
                    brand_match=brand_equal,
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
                    # Tier 1
                    subscribe_save_price=item.get("subscribe_save_price"),
                    coupon_value=item.get("coupon_value"),
                    coupon_pct=item.get("coupon_pct"),
                    effective_price=item.get("effective_price"),
                    is_lightning_deal=item.get("is_lightning_deal"),
                    deal_end_time=item.get("deal_end_time"),
                    stock_quantity=item.get("stock_quantity"),
                    low_stock_warning=item.get("low_stock_warning"),
                    best_seller_rank=item.get("best_seller_rank"),
                    best_seller_rank_category=item.get("best_seller_rank_category"),
                    # Tier 2
                    units_sold_past_month=item.get("units_sold_past_month"),
                    badge_amazons_choice=item.get("badge_amazons_choice"),
                    badge_best_seller=item.get("badge_best_seller"),
                    badge_new_release=item.get("badge_new_release"),
                    is_sponsored=item.get("is_sponsored"),
                    rating_distribution=item.get("rating_distribution"),
                    # Tier 3
                    specifications=item.get("specifications"),
                    variant_options=item.get("variant_options"),
                    date_first_available=item.get("date_first_available"),
                    # Gap 1 — Seller Intelligence
                    amazon_is_seller=item.get("amazon_is_seller"),
                    seller_feedback_count=item.get("seller_feedback_count"),
                    seller_positive_feedback_pct=item.get("seller_positive_feedback_pct"),
                    lowest_new_offer_price=item.get("lowest_new_offer_price"),
                    number_of_used_offers=item.get("number_of_used_offers"),
                    # Gap 2 — Listing Quality
                    image_count=item.get("image_count"),
                    has_video=item.get("has_video"),
                    has_aplus_content=item.get("has_aplus_content"),
                    has_brand_story=item.get("has_brand_story"),
                    bullet_point_count=item.get("bullet_point_count"),
                    title_char_count=item.get("title_char_count"),
                    questions_count=item.get("questions_count"),
                    listing_quality_score=_compute_listing_score(item),
                    # Gap 3 — Delivery
                    delivery_fastest_days=item.get("delivery_fastest_days"),
                    delivery_standard_days=item.get("delivery_standard_days"),
                    has_same_day=item.get("has_same_day"),
                    ships_from_location=item.get("ships_from_location"),
                    has_free_returns=item.get("has_free_returns"),
                    return_window_days=item.get("return_window_days"),
                    # Gap 4 — Variations
                    parent_asin=item.get("parent_asin"),
                    total_variations=item.get("total_variations"),
                    is_best_seller_variation=item.get("is_best_seller_variation"),
                    # Gap 5 — Extended Badges
                    climate_pledge_friendly=item.get("climate_pledge_friendly"),
                    small_business_badge=item.get("small_business_badge"),
                )
                self.db.add(match)
                self.db.flush()
                # Keep the lookup dict consistent so a duplicate URL in the
                # same result set doesn't create a second CompetitorMatch row.
                existing_by_url[item_url] = match

            if item.get("price"):
                # Skip the insert if price hasn't changed — avoids filling
                # price_history with identical rows on every hourly scrape cycle.
                last_price = existing_latest_price.get(match.id)
                if last_price is not None and abs(last_price - item["price"]) < 0.01:
                    _upsert_promotions(self.db, match.id, item.get("promotions") or [])
                    matches_found += 1
                    continue
                existing_latest_price[match.id] = item["price"]  # keep cache current

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
                    source=item.get("source", "playwright"),
                    rating=item.get("rating"),
                    review_count=item.get("review_count"),
                    is_prime=item.get("is_prime"),
                    fulfillment_type=item.get("fulfillment_type"),
                    product_condition=item.get("product_condition"),
                    # Volatile pricing & demand snapshot
                    subscribe_save_price=item.get("subscribe_save_price"),
                    coupon_value=item.get("coupon_value"),
                    coupon_pct=item.get("coupon_pct"),
                    effective_price=item.get("effective_price"),
                    is_lightning_deal=item.get("is_lightning_deal"),
                    deal_end_time=item.get("deal_end_time"),
                    stock_quantity=item.get("stock_quantity"),
                    units_sold_past_month=item.get("units_sold_past_month"),
                    best_seller_rank=item.get("best_seller_rank"),
                    badge_amazons_choice=item.get("badge_amazons_choice"),
                    badge_best_seller=item.get("badge_best_seller"),
                    is_sponsored=item.get("is_sponsored"),
                    # Gap snapshot fields
                    amazon_is_seller=item.get("amazon_is_seller"),
                    seller_name_snapshot=item.get("seller_name"),
                    delivery_fastest_days=item.get("delivery_fastest_days"),
                    has_free_returns=item.get("has_free_returns"),
                ))

            # ── ReviewSnapshot (always insert — enables velocity queries) ──────
            if item.get("review_count") is not None or item.get("rating") is not None:
                self.db.add(ReviewSnapshot(
                    match_id=match.id,
                    review_count=item.get("review_count"),
                    rating=item.get("rating"),
                    rating_distribution=item.get("rating_distribution"),
                    questions_count=item.get("questions_count"),
                    scraped_at=now,
                ))

            # ── ListingQualitySnapshot (insert so listing trends are tracked) ─
            if item.get("image_count") is not None or item.get("bullet_point_count") is not None:
                self.db.add(ListingQualitySnapshot(
                    match_id=match.id,
                    image_count=item.get("image_count"),
                    has_video=item.get("has_video"),
                    has_aplus_content=item.get("has_aplus_content"),
                    has_brand_story=item.get("has_brand_story"),
                    bullet_point_count=item.get("bullet_point_count"),
                    title_char_count=item.get("title_char_count"),
                    questions_count=item.get("questions_count"),
                    listing_score=_compute_listing_score(item),
                    scraped_at=now,
                ))

            # ── SellerProfile upsert (workspace-scoped, one row per workspace+seller) ──
            _upsert_seller_profile(self.db, item, workspace_id=match.workspace_id)

            _upsert_promotions(self.db, match.id, item.get("promotions") or [])
            matches_found += 1

        self.db.commit()
        logger.info("Scraped product %d: %d match(es)", product_id, matches_found)

        # Invalidate analytics cache so next request gets fresh data
        try:
            from services.cache_service import invalidate_cache
            invalidate_cache(f"analytics:trendline:{product_id}:*")
            invalidate_cache(f"analytics:compare:{product_id}:*")
            invalidate_cache(f"analytics:alerts:{product_id}:*")
        except Exception:
            pass  # Cache invalidation is best-effort

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
                .order_by(ProductMonitored.id)
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

def _detect_match_method(product_dict: dict, candidate_dict: dict) -> str:
    """
    Return which signal produced the match, from most to least authoritative.

    upc_exact  — barcode equality (gold standard, 1.0 confidence)
    mpn_exact  — manufacturer part number equality (0.95 confidence)
    text_fuzzy — weighted title/brand/description similarity
    """
    p_upc = (product_dict.get("upc_ean") or "").strip()
    c_upc = (candidate_dict.get("upc_ean") or "").strip()
    if p_upc and c_upc and p_upc == c_upc:
        return "upc_exact"

    p_mpn = (product_dict.get("mpn") or "").strip().lower()
    c_mpn = (candidate_dict.get("mpn") or "").strip().lower()
    if p_mpn and c_mpn and p_mpn == c_mpn:
        return "mpn_exact"

    return "text_fuzzy"


def _brands_match(product_dict: dict, candidate_dict: dict) -> bool | None:
    """Return True/False brand equality, or None when either brand is unknown."""
    p_brand = (product_dict.get("brand") or "").strip().lower()
    c_brand = (candidate_dict.get("brand") or "").strip().lower()
    if not p_brand or not c_brand:
        return None
    return p_brand == c_brand


def _compute_listing_score(item: dict) -> int:
    """
    Compute a 0-100 listing quality score from scraped item fields.
    Weighting: images(20) + video(15) + aplus(20) + brand_story(10) + bullets(15) + title(10) + qa(10)
    """
    score = 0
    image_count = item.get("image_count") or 0
    score += min(image_count, 7) / 7 * 20
    if item.get("has_video"):
        score += 15
    if item.get("has_aplus_content"):
        score += 20
    if item.get("has_brand_story"):
        score += 10
    bullet_count = item.get("bullet_point_count") or 0
    score += min(bullet_count, 5) / 5 * 15
    title_len = item.get("title_char_count") or 0
    if 80 <= title_len <= 200:
        score += 10
    elif 50 <= title_len < 80 or 200 < title_len <= 250:
        score += 5
    q_count = item.get("questions_count") or 0
    score += min(q_count, 50) / 50 * 10
    return round(score)


def _upsert_seller_profile(db, item: dict, workspace_id: int | None = None):
    """
    Create or update a SellerProfile row scoped to workspace_id.

    One row per (workspace_id, seller_name) — isolates seller intelligence
    per shop so Shop A's data never leaks to Shop B.
    """
    seller_name = (item.get("seller_name") or "").strip()
    if not seller_name:
        return
    from datetime import datetime
    existing = db.query(SellerProfile).filter_by(
        workspace_id=workspace_id,
        seller_name=seller_name,
    ).first()
    is_1p = seller_name.lower() in ("amazon.com", "amazon", "amazon warehouse")
    if existing:
        existing.amazon_is_1p = is_1p
        if item.get("seller_feedback_count") is not None:
            existing.feedback_count = item["seller_feedback_count"]
        if item.get("seller_positive_feedback_pct") is not None:
            existing.positive_feedback_pct = item["seller_positive_feedback_pct"]
        existing.last_updated_at = datetime.utcnow()
    else:
        db.add(SellerProfile(
            workspace_id=workspace_id,
            seller_name=seller_name,
            amazon_is_1p=is_1p,
            feedback_count=item.get("seller_feedback_count"),
            positive_feedback_pct=item.get("seller_positive_feedback_pct"),
        ))


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
