"""
Apify-Based Amazon Scraper (Cloud Fallback)

Uses Apify's cloud infrastructure to scrape Amazon when local Playwright
scraping is blocked by CAPTCHA or bot-detection.

Setup:
  1. Sign up at https://apify.com and get your API token
  2. Set APIFY_API_TOKEN in your .env file
  3. pip install apify-client

The actor used is `vaclavrut/amazon-crawler`, a well-maintained community
actor with proxy rotation built-in.
"""

import asyncio
import os
from typing import Dict, List, Optional


class ApifyScraper:
    """
    Wraps Apify's Amazon actor for cloud-based scraping.

    Instantiated automatically by ScraperManager — no manual setup needed
    beyond setting APIFY_API_TOKEN in the environment.
    """

    ACTOR_ID = "vaclavrut/amazon-crawler"

    def __init__(self, api_token: Optional[str] = None):
        self._token = api_token or os.getenv("APIFY_API_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        """True when an API token is present."""
        return bool(self._token)

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape_product(self, url: str) -> Dict:
        """Scrape an Amazon product page via Apify cloud."""
        if not self.is_configured:
            return {"url": url, "error": "Apify API token not configured (set APIFY_API_TOKEN)"}
        try:
            return await asyncio.to_thread(self._scrape_product_sync, url)
        except Exception as e:
            return {"url": url, "error": f"Apify scrape failed: {e}"}

    async def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Amazon via Apify cloud."""
        if not self.is_configured:
            return [{"error": "Apify API token not configured (set APIFY_API_TOKEN)"}]
        try:
            return await asyncio.to_thread(self._search_products_sync, query, max_results)
        except Exception as e:
            return [{"error": f"Apify search failed: {e}"}]

    # ── Sync helpers (run inside a thread) ───────────────────────────────────

    def _client(self):
        from apify_client import ApifyClient  # lazy import — optional dependency
        return ApifyClient(self._token)

    def _scrape_product_sync(self, url: str) -> Dict:
        client = self._client()
        run = client.actor(self.ACTOR_ID).call(
            run_input={"startUrls": [{"url": url}], "maxItems": 1, "country": "US"}
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return {"url": url, "error": "Apify returned no results"}
        return self._normalize(items[0], url=url)

    def _search_products_sync(self, query: str, max_results: int) -> List[Dict]:
        client = self._client()
        run = client.actor(self.ACTOR_ID).call(
            run_input={"queries": [query], "maxItems": max_results, "country": "US"}
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return [self._normalize(item) for item in items[:max_results]]

    # ── Normalisation ─────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(item: Dict, url: Optional[str] = None) -> Dict:
        """Map Apify actor output to the standard product schema used across scrapers."""

        def _float(value) -> Optional[float]:
            if value is None:
                return None
            try:
                return float(str(value).replace("$", "").replace(",", "").strip())
            except (ValueError, TypeError):
                return None

        def _int(value) -> Optional[int]:
            if value is None:
                return None
            try:
                return int(str(value).replace(",", "").strip())
            except (ValueError, TypeError):
                return None

        price = _float(item.get("price") or item.get("salePrice"))
        was_price = _float(item.get("originalPrice") or item.get("listPrice"))
        rating = _float(item.get("stars") or item.get("rating"))
        review_count = _int(item.get("reviewsCount") or item.get("ratingsCount"))

        discount_pct = None
        if was_price and price and was_price > price:
            discount_pct = round((1 - price / was_price) * 100, 1)

        return {
            "url": url or item.get("url", ""),
            "title": item.get("title") or item.get("name"),
            "asin": item.get("asin"),
            "price": price,
            "was_price": was_price,
            "discount_pct": discount_pct,
            "currency": item.get("currency", "USD"),
            "in_stock": item.get("inStock", True),
            "image_url": item.get("thumbnailImage") or item.get("imageUrl"),
            "rating": rating,
            "review_count": review_count,
            "brand": item.get("brand"),
            "description": item.get("description"),
            "mpn": None,
            "upc_ean": None,
            "promotion_label": item.get("promotionLabel"),
            "seller_name": item.get("seller") or item.get("sellerName"),
            "seller_count": None,
            "is_prime": item.get("isPrime"),
            "fulfillment_type": None,
            "product_condition": item.get("condition", "New"),
            "category": item.get("breadcrumbs") or item.get("category"),
            "variant": None,
            "shipping_cost": None,
            "total_price": price,
            "scrape_quality": "clean" if price else "partial",
            "source": "apify",
            "error": None,
        }
