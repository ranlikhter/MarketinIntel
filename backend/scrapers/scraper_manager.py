"""
Scraper Manager — Intelligent Scraper Selection

Automatically routes URLs to the right scraper:
  - AmazonScraper   for *.amazon.* URLs
  - GenericWebScraper for everything else

Performance additions over the original:
  - CircuitBreaker  — stops hammering domains that are blocking us
  - DomainRateLimiter — throttles per domain to avoid bans
  - ResponseCache   — skips re-scraping the same URL within 5 minutes
  - Thread-safe singleton via threading.Lock
"""

import threading
from typing import Dict, Optional
from urllib.parse import urlparse

from scrapers.amazon_scraper import AmazonScraper
from scrapers.generic_scraper import GenericWebScraper
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
        self.generic_scraper = GenericWebScraper(browser_pool=browser_pool)

        self.specialized_scrapers = {
            "amazon.com": self.amazon_scraper,
            "amazon.co.uk": self.amazon_scraper,
            "amazon.ca": self.amazon_scraper,
            "amazon.de": self.amazon_scraper,
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
                if isinstance(scraper, AmazonScraper):
                    result = await scraper.scrape_product(url)
                else:
                    result = await scraper.scrape_product(
                        url, price_selector, title_selector, stock_selector, image_selector
                    )

                if result.get("error"):
                    if "CAPTCHA" in result["error"]:
                        circuit_breaker.record_failure(domain)
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
            return {"error": f"No specialized scraper for {website}."}
        if isinstance(scraper, AmazonScraper):
            return await scraper.search_products(query, max_results)
        return {"error": "Search not implemented for this website"}

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
