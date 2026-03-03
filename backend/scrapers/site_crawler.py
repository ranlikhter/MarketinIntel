"""
Intelligent Full-Site Crawler

Automatically discovers and scrapes all products from competitor websites.

Performance improvements over the original:
  - Iterative BFS queue instead of unbounded recursion (no stack overflow
    on deep sites; simpler flow control).
  - BrowserPool reuses one Chromium process for the whole crawl.
  - wait_until='domcontentloaded' instead of 'networkidle' — 3–5× faster
    per page; networkidle waits for ALL network activity to stop, which is
    rarely necessary for link / price extraction.
  - Concurrent product extraction: multiple pages scraped in parallel using
    the pool's semaphore for back-pressure.
  - All regex patterns pre-compiled at module level.
  - Configurable delay (default 1 s, down from 2 s).
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeout

from scrapers.browser_pool import BrowserPool

logger = logging.getLogger(__name__)


# ── Pre-compiled patterns ─────────────────────────────────────────────────────

_PRODUCT_URL_RE = re.compile(
    r"/product/|/item/|/p/|/dp/|/gp/product/"
    r"|\d+$"                      # ends with an ID
    r"|/[a-z0-9\-]+-\d+",         # slug-ID pattern
    re.IGNORECASE,
)
_CATEGORY_URL_RE = re.compile(
    r"/category/|/collection/|/shop/|/catalog/|/products/"
    r"|/c/|/cat/|/department/|/browse/",
    re.IGNORECASE,
)
_SKIP_URL_RE = re.compile(
    r"/cart|/checkout|/account|/login|/register"
    r"|/search|/wishlist|/compare|/track"
    r"|/blog|/about|/contact|/faq|/help"
    r"|/terms|/privacy|/shipping|/returns"
    r"|\.jpg|\.png|\.gif|\.pdf|\.zip"
    r"|javascript:|mailto:|tel:",
    re.IGNORECASE,
)
_PRODUCT_CARD_RE = re.compile(r"product[_-]?(card|item|tile)", re.IGNORECASE)
_PAGINATION_RE = re.compile(r"pagination", re.IGNORECASE)
_NEXT_PAGE_RE = re.compile(r"next|previous|page \d+", re.IGNORECASE)
_FILTER_RE = re.compile(r"filter|sort", re.IGNORECASE)
_PRODUCT_PRICE_CLASS_RE = re.compile(r"product[_-]?price", re.IGNORECASE)
_ADD_TO_CART_CLASS_RE = re.compile(r"add[_-]?to[_-]?cart", re.IGNORECASE)
_PRODUCT_DETAILS_CLASS_RE = re.compile(r"product[_-]?details", re.IGNORECASE)
_PRODUCT_CLASS_RE = re.compile(r"product", re.IGNORECASE)
_PRODUCT_TITLE_CLASS_RE = re.compile(r"product[_-]?title", re.IGNORECASE)
_PRICE_CLASS_RE = re.compile(r"price", re.IGNORECASE)
_PRODUCT_IMAGE_CLASS_RE = re.compile(r"product[_-]?image", re.IGNORECASE)
_STOCK_TEXT_RE = re.compile(r"in stock|out of stock|available|unavailable", re.IGNORECASE)
_PRODUCT_SCHEMA_RE = re.compile(r"Product", re.IGNORECASE)
_PRICE_NUM_RE = re.compile(r"[\d,]+\.?\d*")


class SiteCrawler:
    """
    Crawls an entire competitor website to discover and optionally scrape
    all product pages.

    Usage:
        crawler = SiteCrawler()
        result = await crawler.crawl_site("https://competitor.com", max_products=50)
    """

    def __init__(self, delay: float = 1.0, concurrency: int = 3):
        """
        Args:
            delay:       Seconds to wait between page loads (per worker).
            concurrency: Number of parallel browser pages (= pool size).
        """
        self.delay = delay
        self.concurrency = concurrency

        self.visited_urls: Set[str] = set()
        self.product_urls: Set[str] = set()
        self.category_urls: Set[str] = set()
        self.max_depth = 3
        self.max_pages = 500

    # ── Public API ────────────────────────────────────────────────────────────

    async def crawl_site(
        self,
        base_url: str,
        max_products: int = 100,
        max_depth: int = 3,
        category_only: bool = False,
    ) -> Dict:
        """
        Crawl the site starting from base_url and return discovered URLs and
        optionally scraped product data.
        """
        self.max_depth = max_depth
        self.visited_urls.clear()
        self.product_urls.clear()
        self.category_urls.clear()

        logger.info("Starting site crawl for: %s", base_url)

        pool = BrowserPool(pool_size=self.concurrency)
        try:
            await pool.start()
            await self._crawl_bfs(pool, base_url)

            logger.info(
                "Crawl complete. %d products, %d categories discovered.",
                len(self.product_urls), len(self.category_urls),
            )

            products = []
            if not category_only and self.product_urls:
                urls_to_scrape = list(self.product_urls)[:max_products]
                products = await self._extract_products_concurrent(pool, urls_to_scrape)

            return {
                "success": True,
                "base_url": base_url,
                "categories_found": len(self.category_urls),
                "products_found": len(self.product_urls),
                "products_scraped": len(products),
                "category_urls": list(self.category_urls),
                "product_urls": list(self.product_urls)[:max_products],
                "products": products,
            }

        except Exception as e:
            logger.error("Site crawl failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "categories_found": len(self.category_urls),
                "products_found": len(self.product_urls),
            }
        finally:
            await pool.close()

    async def discover_categories(self, base_url: str) -> List[str]:
        """Quick category-only discovery (max depth 2)."""
        result = await self.crawl_site(
            base_url=base_url, max_depth=2, category_only=True
        )
        return result.get("category_urls", [])

    # ── BFS crawl ─────────────────────────────────────────────────────────────

    async def _crawl_bfs(self, pool: BrowserPool, base_url: str):
        """
        Iterative BFS over the site.  A single page is fetched at a time to
        keep politeness delays simple; the pool is used for product extraction
        later, where parallelism is safe.
        """
        queue: List[tuple] = [(base_url, 0)]   # (url, depth)

        while queue:
            if len(self.visited_urls) >= self.max_pages:
                break

            url, depth = queue.pop(0)

            if depth > self.max_depth:
                continue
            if url in self.visited_urls:
                continue
            if not self._is_same_domain(url, base_url):
                continue
            if _SKIP_URL_RE.search(url):
                continue

            self.visited_urls.add(url)
            logger.info("Crawling [depth=%d]: %s", depth, url)

            try:
                async with pool.acquire_page() as page:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(self.delay)
                    except PlaywrightTimeout:
                        logger.warning("Timeout crawling %s", url)
                        continue

                    content = await page.content()

                soup = BeautifulSoup(content, "html.parser")
                page_type = self._detect_page_type(soup, url)

                if page_type == "product":
                    self.product_urls.add(url)
                    logger.debug("  → product")

                elif page_type == "category":
                    self.category_urls.add(url)
                    logger.debug("  → category (%d links)", 0)

                    links = self._extract_links(soup, url)
                    for link in links:
                        if _PRODUCT_URL_RE.search(link) and link not in self.visited_urls:
                            self.visited_urls.add(link)
                            self.product_urls.add(link)
                        elif _CATEGORY_URL_RE.search(link) and link not in self.visited_urls:
                            queue.append((link, depth + 1))

                else:
                    links = self._extract_links(soup, url)
                    for link in links[:20]:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))

            except Exception as e:
                logger.error("Error crawling %s: %s", url, e)

    # ── Concurrent product extraction ─────────────────────────────────────────

    async def _extract_products_concurrent(
        self, pool: BrowserPool, product_urls: List[str]
    ) -> List[Dict]:
        """Extract product data from a list of URLs, concurrently."""
        sem = asyncio.Semaphore(self.concurrency)
        results = await asyncio.gather(
            *[self._extract_one(pool, sem, url) for url in product_urls],
            return_exceptions=False,
        )
        return [r for r in results if r is not None]

    async def _extract_one(
        self, pool: BrowserPool, sem: asyncio.Semaphore, url: str
    ) -> Optional[Dict]:
        async with sem:
            try:
                async with pool.acquire_page() as page:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(self.delay)
                    content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                return self._parse_product_page(soup, url)
            except Exception as e:
                logger.error("Error extracting %s: %s", url, e)
                return None

    # ── Page classification ───────────────────────────────────────────────────

    def _detect_page_type(self, soup: BeautifulSoup, url: str) -> str:
        """Classify a page as 'product', 'category', or 'general'."""
        url_lower = url.lower()

        if _PRODUCT_URL_RE.search(url_lower):
            return "product"

        product_signals = (
            soup.find("script", type="application/ld+json", string=_PRODUCT_SCHEMA_RE)
            or soup.find("meta", property="og:type", content="product")
            or soup.find("meta", property="product:price")
            or soup.find(class_=_PRODUCT_PRICE_CLASS_RE)
            or soup.find(class_=_ADD_TO_CART_CLASS_RE)
            or soup.find("button", string=re.compile(r"add to (cart|basket)", re.IGNORECASE))
            or soup.find(class_=_PRODUCT_DETAILS_CLASS_RE)
        )
        if product_signals:
            return "product"

        if _CATEGORY_URL_RE.search(url_lower):
            return "category"

        category_signals = (
            len(soup.find_all(class_=_PRODUCT_CARD_RE)) > 3
            or soup.find(class_=_PAGINATION_RE)
            or soup.find("a", string=_NEXT_PAGE_RE)
            or soup.find(class_=_FILTER_RE)
        )
        if category_signals:
            return "category"

        return "general"

    # ── URL helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _is_same_domain(url: str, base_url: str) -> bool:
        url_domain = urlparse(url).netloc
        base_domain = urlparse(base_url).netloc
        return (
            url_domain == base_domain
            or url_domain == ""
            or url_domain == base_domain.replace("www.", "")
        )

    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        seen: Set[str] = set()
        links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(current_url, href)
            parsed = urlparse(absolute)
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if clean and clean not in seen and not _SKIP_URL_RE.search(clean):
                seen.add(clean)
                links.append(clean)
        return links

    # ── Product page parser ───────────────────────────────────────────────────

    def _parse_product_page(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        try:
            title = None
            for elem in [
                soup.find("h1"),
                soup.find(class_=_PRODUCT_TITLE_CLASS_RE),
                soup.find(itemprop="name"),
                soup.find("meta", property="og:title"),
            ]:
                if elem:
                    title = elem.get("content") if elem.name == "meta" else elem.get_text(strip=True)
                    if title:
                        break
            if not title:
                return None

            price = None
            for elem in [
                soup.find(class_=_PRICE_CLASS_RE),
                soup.find(itemprop="price"),
                soup.find("meta", property="product:price:amount"),
            ]:
                if elem:
                    price_text = (
                        elem.get("content") if elem.name == "meta" else elem.get_text(strip=True)
                    )
                    if price_text:
                        m = _PRICE_NUM_RE.search(price_text.replace(",", ""))
                        if m:
                            try:
                                price = float(m.group())
                                break
                            except ValueError:
                                pass

            image_url = None
            for elem in [
                soup.find("meta", property="og:image"),
                soup.find(itemprop="image"),
                soup.find("img", class_=_PRODUCT_IMAGE_CLASS_RE),
            ]:
                if elem:
                    image_url = (
                        elem.get("content") or elem.get("src") or elem.get("data-src")
                    )
                    if image_url:
                        break

            stock_status = "Unknown"
            for match in soup.find_all(string=_STOCK_TEXT_RE):
                text_lower = match.lower()
                if "in stock" in text_lower or "available" in text_lower:
                    stock_status = "In Stock"
                elif "out of stock" in text_lower or "unavailable" in text_lower:
                    stock_status = "Out of Stock"
                break

            return {
                "title": title,
                "price": price,
                "image_url": image_url,
                "stock_status": stock_status,
                "url": url,
            }

        except Exception as e:
            logger.error("Error parsing product page %s: %s", url, e)
            return None
