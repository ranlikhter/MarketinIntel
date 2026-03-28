"""
Scraper Manager — Intelligent Scraper Selection

Automatically routes URLs to the right scraper:
  - AmazonScraper   for *.amazon.* URLs  (with Apify cloud fallback on CAPTCHA)
  - GenericWebScraper for everything else

Performance additions over the original:
  - CircuitBreaker  — stops hammering domains that are blocking us
  - DomainRateLimiter — throttles per domain to avoid bans
  - ResponseCache   — skips re-scraping the same URL within 5 minutes
  - Thread-safe singleton via threading.Lock

Apify fallback:
  When local Amazon scraping hits a CAPTCHA, the request is automatically
  retried via Apify's cloud infrastructure (proxy rotation, residential IPs).
  Requires APIFY_API_TOKEN in the environment and `pip install apify-client`.
"""

import logging
import threading
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from scrapers.amazon_scraper import AmazonScraper
from scrapers.apify_scraper import ApifyScraper
from scrapers.ebay_scraper import EbayScraper
from scrapers.generic_scraper import GenericWebScraper
from scrapers.walmart_scraper import WalmartScraper
from scrapers.browser_pool import (
    BrowserPool,
    circuit_breaker,
    rate_limiter,
    response_cache,
)


class ScraperManager:
    """
    Routes scrape requests to the correct backend and enforces
    circuit-breaking, rate-limiting, and response caching.

    Typically obtained via get_scraper_manager() rather than instantiated
    directly, so a single BrowserPool is shared across the process.
    """

    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        self._pool = browser_pool
        self.amazon_scraper = AmazonScraper(browser_pool=browser_pool)
        self.apify_scraper = ApifyScraper()
        self.walmart_scraper = WalmartScraper(browser_pool=browser_pool)
        self.ebay_scraper = EbayScraper(browser_pool=browser_pool)
        self.generic_scraper = GenericWebScraper(browser_pool=browser_pool)

        self.specialized_scrapers = {
            # Amazon — all major locales
            "amazon.com": self.amazon_scraper,
            "amazon.co.uk": self.amazon_scraper,
            "amazon.ca": self.amazon_scraper,
            "amazon.de": self.amazon_scraper,
            "amazon.fr": self.amazon_scraper,
            "amazon.es": self.amazon_scraper,
            "amazon.it": self.amazon_scraper,
            "amazon.co.jp": self.amazon_scraper,
            "amazon.com.au": self.amazon_scraper,
            # Walmart
            "walmart.com": self.walmart_scraper,
            # eBay — major locales
            "ebay.com": self.ebay_scraper,
            "ebay.co.uk": self.ebay_scraper,
            "ebay.de": self.ebay_scraper,
            "ebay.fr": self.ebay_scraper,
            "ebay.com.au": self.ebay_scraper,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape(
        self,
        url: str,
        price_selector: Optional[str] = None,
        title_selector: Optional[str] = None,
        stock_selector: Optional[str] = None,
        image_selector: Optional[str] = None,
        max_retries: int = 3,
        bypass_cache: bool = False,
    ) -> Dict:
        """
        Scrape a product URL using the appropriate scraper.

        Checks the response cache first, enforces per-domain rate limiting,
        and uses the circuit breaker to skip domains that are blocking us.
        """
        domain = self._extract_domain(url)

        # ── Cache check ──────────────────────────────────────────────────
        if not bypass_cache:
            cached = response_cache.get(url)
            if cached is not None:
                return cached

        # ── Circuit breaker ──────────────────────────────────────────────
        if circuit_breaker.is_open(domain):
            secs = int(circuit_breaker.seconds_until_reset(domain))
            return {
                "url": url,
                "error": f"Domain {domain} is temporarily blocked (circuit open, resets in {secs}s)",
            }

        # ── Rate limiter ─────────────────────────────────────────────────
        await rate_limiter.acquire(domain)

        # ── Route to scraper ─────────────────────────────────────────────
        scraper = self.specialized_scrapers.get(domain, self.generic_scraper)

        for attempt in range(max_retries):
            try:
                if isinstance(scraper, (AmazonScraper, WalmartScraper, EbayScraper)):
                    result = await scraper.scrape_product(url)
                else:
                    result = await scraper.scrape_product(
                        url, price_selector, title_selector, stock_selector, image_selector
                    )

                if result.get("error"):
                    if "CAPTCHA" in result["error"]:
                        circuit_breaker.record_failure(domain)
                        # Fall back to Apify cloud scraper for Amazon CAPTCHA blocks
                        if isinstance(scraper, AmazonScraper) and self.apify_scraper.is_configured:
                            apify_result = await self.apify_scraper.scrape_product(url)
                            if not apify_result.get("error"):
                                response_cache.set(url, apify_result)
                                return apify_result
                    if attempt < max_retries - 1:
                        await _backoff(attempt, base=5)
                        continue
                    return result

                # Success
                circuit_breaker.record_success(domain)
                if not result.get("error"):
                    response_cache.set(url, result)
                return result

            except Exception as e:
                circuit_breaker.record_failure(domain)
                if attempt < max_retries - 1:
                    await _backoff(attempt, base=2)
                    continue
                return {"url": url, "error": f"Failed after {max_retries} attempts: {e}"}

        return {"url": url, "error": "Max retries exceeded"}

    async def search(
        self,
        query: str,
        website: str = "amazon.com",
        max_results: int = 10,
    ) -> list:
        """Search for products on a specific website."""
        scraper = self.specialized_scrapers.get(website)
        if not scraper:
            logger.warning("No specialized scraper for %s", website)
            return []
        if isinstance(scraper, AmazonScraper):
            results = await scraper.search_products(query, max_results)
            # Fall back to Apify if local search was blocked by CAPTCHA
            if isinstance(results, dict) and "CAPTCHA" in results.get("error", ""):
                if self.apify_scraper.is_configured:
                    return await self.apify_scraper.search_products(query, max_results)
            return results if isinstance(results, list) else []
        if isinstance(scraper, (WalmartScraper, EbayScraper)):
            results = await scraper.search_products(query, max_results)
            return results if isinstance(results, list) else []
        logger.warning("Search not implemented for %s", website)
        return []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def get_scraper_type(self, url: str) -> str:
        domain = self._extract_domain(url)
        if domain in self.specialized_scrapers:
            return domain.split(".")[0]
        return "generic"


async def _backoff(attempt: int, base: int = 2):
    import asyncio
    await asyncio.sleep(base * (2 ** attempt))


# ── Thread-safe singleton ─────────────────────────────────────────────────────

_manager: Optional[ScraperManager] = None
_manager_lock = threading.Lock()


def get_scraper_manager() -> ScraperManager:
    """Return (and lazily create) the process-wide ScraperManager singleton."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ScraperManager()
    return _manager


# ── Convenience wrappers ─────────────────────────────────────────────────────

async def scrape_url(
    url: str,
    price_selector: Optional[str] = None,
    title_selector: Optional[str] = None,
    stock_selector: Optional[str] = None,
    image_selector: Optional[str] = None,
) -> Dict:
    return await get_scraper_manager().scrape(
        url, price_selector, title_selector, stock_selector, image_selector
    )


async def search_products(
    query: str, website: str = "amazon.com", max_results: int = 10
) -> list:
    return await get_scraper_manager().search(query, website, max_results)
