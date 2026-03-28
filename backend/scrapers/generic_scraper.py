"""
Generic Web Scraper for Custom Competitor Websites

Extracts product data from ANY website using CSS selectors.

Performance design:
  - Tries a fast httpx (HTTP-only) path first; falls back to Playwright only
    when the page appears to be JavaScript-rendered (thin body text or no
    price found, or a 403/429/503 response).
  - Accepts an optional BrowserPool so the caller can share one pool across
    multiple scrape calls, eliminating per-call browser-startup overhead.
  - Pre-navigation sleeps removed; a short post-load settle is kept only in
    Playwright mode to allow dynamic content to render.
"""

import asyncio
import base64
import json
import random
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.async_api import TimeoutError as PlaywrightTimeout

from scrapers.browser_pool import BrowserPool

try:
    import html2text as _html2text
    _HTML2TEXT_AVAILABLE = True
except ImportError:
    _HTML2TEXT_AVAILABLE = False


class GenericWebScraper:
    """
    Flexible scraper that extracts data from any website via CSS selectors.

    Usage:
        pool = BrowserPool(pool_size=2)
        scraper = GenericWebScraper(browser_pool=pool)
        result = await scraper.scrape_product(
            url="https://competitor.com/product/123",
            price_selector=".price",
        )
        await pool.close()
    """

    # Minimum body-text length that indicates a fully server-rendered page.
    _MIN_STATIC_BODY_LEN = 500

    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        self.ua = UserAgent()
        self._pool = browser_pool
        self._owns_pool = browser_pool is None

    async def _get_pool(self) -> BrowserPool:
        if self._pool is None:
            self._pool = BrowserPool(pool_size=1)
        return self._pool

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape_product(
        self,
        url: str,
        price_selector: Optional[str] = None,
        title_selector: Optional[str] = None,
        stock_selector: Optional[str] = None,
        image_selector: Optional[str] = None,
        use_javascript: Optional[bool] = None,
        output_format: str = "json",
        capture_screenshot: bool = False,
    ) -> Dict:
        """
        Scrape product data from a given URL.

        use_javascript=None  → auto: try HTTP first, fall back to Playwright
        use_javascript=True  → always use Playwright
        use_javascript=False → always use httpx (no fallback)
        output_format="json" → return structured product fields (default)
        output_format="markdown" → return {"url", "markdown", "title"} instead
        capture_screenshot=True → add base64 PNG under "screenshot" key
                                  (requires Playwright path)
        """
        # Screenshot or markdown always forces Playwright for full render
        force_js = use_javascript is True or capture_screenshot or (
            output_format == "markdown" and use_javascript is not False
        )

        if force_js:
            return await self._scrape_with_playwright(
                url, price_selector, title_selector, stock_selector, image_selector,
                output_format=output_format, capture_screenshot=capture_screenshot,
            )
        if use_javascript is False:
            return await self._scrape_with_requests(
                url, price_selector, title_selector, stock_selector, image_selector,
                output_format=output_format,
            )

        # Auto mode: try fast HTTP path; fall back to Playwright if needed
        result = await self._scrape_with_requests(
            url, price_selector, title_selector, stock_selector, image_selector,
            output_format=output_format,
        )
        if result.get("_needs_js"):
            result = await self._scrape_with_playwright(
                url, price_selector, title_selector, stock_selector, image_selector,
                output_format=output_format, capture_screenshot=capture_screenshot,
            )
        result.pop("_needs_js", None)
        return result

    # ── HTTP (httpx) path ─────────────────────────────────────────────────────

    async def _scrape_with_requests(
        self,
        url: str,
        price_selector: Optional[str],
        title_selector: Optional[str],
        stock_selector: Optional[str],
        image_selector: Optional[str],
        output_format: str = "json",
    ) -> Dict:
        """
        Fast path: fetch the page with httpx (no browser overhead).

        Sets _needs_js=True in the result when the page looks JS-rendered so
        the caller can fall back to Playwright automatically.
        """
        result = self._empty_result(url)

        try:
            headers = {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            async with httpx.AsyncClient(
                headers=headers,
                timeout=15.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Detect JS-rendered page (nearly empty body text)
            if len(soup.get_text(strip=True)) < self._MIN_STATIC_BODY_LEN:
                result["_needs_js"] = True
                return result

            if output_format == "markdown":
                result["markdown"] = self._html_to_markdown(response.text)
                result["title"] = self._extract_title_fallback(soup)
                return result

            self._populate_result(
                result, soup, url,
                price_selector, title_selector, stock_selector, image_selector,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 429, 503):
                result["_needs_js"] = True
            else:
                result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)

        return result

    # ── Playwright path ───────────────────────────────────────────────────────

    async def _scrape_with_playwright(
        self,
        url: str,
        price_selector: Optional[str],
        title_selector: Optional[str],
        stock_selector: Optional[str],
        image_selector: Optional[str],
        output_format: str = "json",
        capture_screenshot: bool = False,
    ) -> Dict:
        """Full-browser scrape using a shared BrowserPool context."""
        result = self._empty_result(url)

        try:
            pool = await self._get_pool()
            async with pool.acquire_page(user_agent=self.ua.random) as page:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # Brief settle for dynamic content
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                except PlaywrightTimeout:
                    result["error"] = "Page load timeout"
                    return result

                page_html = await page.content()

                if capture_screenshot:
                    png_bytes = await page.screenshot(full_page=True)
                    result["screenshot"] = base64.b64encode(png_bytes).decode("ascii")

            soup = BeautifulSoup(page_html, "html.parser")

            if output_format == "markdown":
                result["markdown"] = self._html_to_markdown(page_html)
                result["title"] = self._extract_title_fallback(soup)
                return result

            self._populate_result(
                result, soup, url,
                price_selector, title_selector, stock_selector, image_selector,
            )

        except Exception as e:
            result["error"] = str(e)

        return result

    # ── Shared field extraction ───────────────────────────────────────────────

    def _populate_result(
        self,
        result: Dict,
        soup: BeautifulSoup,
        url: str,
        price_selector: Optional[str],
        title_selector: Optional[str],
        stock_selector: Optional[str],
        image_selector: Optional[str],
    ):
        # Title
        if title_selector:
            result["title"] = self._extract_text(soup, title_selector)
        else:
            result["title"] = self._extract_title_fallback(soup)

        # Price
        if price_selector:
            price_text = self._extract_text(soup, price_selector)
            if price_text:
                result["price"], result["currency"] = self._parse_price(price_text)
                result["scrape_quality"] = "clean"
            else:
                result["scrape_quality"] = "partial"
        else:
            result["price"], result["currency"] = self._extract_price_fallback(soup)
            result["scrape_quality"] = "fallback" if result["price"] else "partial"

        # Was price & discount
        result["was_price"] = self._extract_was_price_fallback(soup)
        if result["was_price"] and result["price"] and result["was_price"] > result["price"]:
            result["discount_pct"] = round(
                (1 - result["price"] / result["was_price"]) * 100, 1
            )

        # Stock
        if stock_selector:
            result["in_stock"] = self._parse_stock_status(
                self._extract_text(soup, stock_selector)
            )

        # Image
        if image_selector:
            result["image_url"] = self._extract_image(soup, image_selector, url)
        else:
            result["image_url"] = self._extract_image_fallback(soup, url)

        # Shipping & total
        result["shipping_cost"] = self._extract_shipping_fallback(soup)
        if result["price"] is not None:
            result["total_price"] = (
                round(result["price"] + result["shipping_cost"], 2)
                if result["shipping_cost"] is not None
                else result["price"]
            )

        # Promotions
        promo_label, promos = self._extract_promotion_fallback(soup)
        result["promotion_label"] = promo_label
        result["promotions"] = promos

        # Identifiers
        result["brand"] = self._extract_brand_fallback(soup)
        result["description"] = self._extract_description_fallback(soup)
        result["mpn"], result["upc_ean"] = self._extract_identifiers_fallback(soup)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """Convert raw HTML to clean LLM-ready markdown."""
        if not _HTML2TEXT_AVAILABLE:
            # Fallback: strip tags with BeautifulSoup
            return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
        h = _html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0          # no line wrapping
        h.ignore_emphasis = False
        return h.handle(html)

    @staticmethod
    def _empty_result(url: str) -> Dict:
        return {
            "url": url,
            "title": None,
            "price": None,
            "was_price": None,
            "discount_pct": None,
            "currency": "USD",
            "in_stock": True,
            "image_url": None,
            "shipping_cost": None,
            "total_price": None,
            "promotion_label": None,
            "promotions": [],
            "brand": None,
            "description": None,
            "mpn": None,
            "upc_ean": None,
            "scrape_quality": "clean",
            "error": None,
        }

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        except Exception:
            pass
        return None

    def _extract_image(self, soup: BeautifulSoup, selector: str, base_url: str) -> Optional[str]:
        try:
            element = soup.select_one(selector)
            if element:
                img_url = element.get("src") or element.get("data-src") or element.get("href")
                if img_url:
                    return urljoin(base_url, img_url)
        except Exception:
            pass
        return None

    def _parse_price(self, price_text: str) -> tuple:
        if not price_text:
            return None, "USD"

        price_text = price_text.strip()

        currency = "USD"
        if "€" in price_text or "EUR" in price_text:
            currency = "EUR"
        elif "£" in price_text or "GBP" in price_text:
            currency = "GBP"
        elif "¥" in price_text or "JPY" in price_text:
            currency = "JPY"

        numeric_text = re.sub(r"[^\d,.\s]", "", price_text)
        numeric_text = numeric_text.replace(",", "").replace(" ", "")
        try:
            return float(numeric_text), currency
        except ValueError:
            return None, currency

    def _parse_stock_status(self, stock_text: Optional[str]) -> bool:
        if not stock_text:
            return True
        stock_text = stock_text.lower()
        out_keywords = [
            "out of stock", "not available", "unavailable",
            "sold out", "coming soon", "pre-order",
            "backordered", "discontinued",
        ]
        return not any(k in stock_text for k in out_keywords)

    def _extract_title_fallback(self, soup: BeautifulSoup) -> Optional[str]:
        meta = soup.find("meta", property="og:title")
        if meta and meta.get("content"):
            return meta["content"].strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        title = soup.find("title")
        if title:
            return title.get_text(strip=True)
        return None

    def _extract_price_fallback(self, soup: BeautifulSoup) -> tuple:
        patterns = [
            {"class": "price"},
            {"class": "product-price"},
            {"class": "sale-price"},
            {"id": "price"},
            {"itemprop": "price"},
        ]
        for pattern in patterns:
            element = soup.find(attrs=pattern)
            if element:
                price, currency = self._parse_price(element.get_text(strip=True))
                if price:
                    return price, currency
        return None, "USD"

    def _extract_image_fallback(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        meta = soup.find("meta", property="og:image")
        if meta and meta.get("content"):
            return urljoin(base_url, meta["content"])
        for pattern in [{"class": "product-image"}, {"class": "main-image"}, {"id": "main-image"}]:
            img = soup.find("img", attrs=pattern)
            if img:
                img_url = img.get("src") or img.get("data-src")
                if img_url:
                    return urljoin(base_url, img_url)
        return None

    def _extract_was_price_fallback(self, soup: BeautifulSoup) -> Optional[float]:
        for tag in soup.find_all(["del", "s", "strike"]):
            price, _ = self._parse_price(tag.get_text(strip=True))
            if price and price > 0:
                return price
        for pattern in [
            {"class": "was-price"}, {"class": "original-price"}, {"class": "old-price"},
            {"class": "regular-price"}, {"class": "list-price"}, {"itemprop": "highPrice"},
        ]:
            elem = soup.find(attrs=pattern)
            if elem:
                price, _ = self._parse_price(elem.get_text(strip=True))
                if price and price > 0:
                    return price
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    high = data.get("highPrice") or data.get("offers", {}).get("highPrice")
                    if high:
                        return float(high)
            except Exception:
                pass
        return None

    def _extract_shipping_fallback(self, soup: BeautifulSoup) -> Optional[float]:
        for pattern in [
            {"class": "shipping-cost"}, {"class": "delivery-price"},
            {"id": "shipping-cost"}, {"class": "freight"},
        ]:
            elem = soup.find(attrs=pattern)
            if elem:
                text = elem.get_text(strip=True).lower()
                if "free" in text:
                    return 0.0
                price, _ = self._parse_price(text)
                if price is not None:
                    return price
        page_text = soup.get_text(" ", strip=True).lower()
        if "free shipping" in page_text or "free delivery" in page_text:
            return 0.0
        return None

    def _extract_brand_fallback(self, soup: BeautifulSoup) -> Optional[str]:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    brand = data.get("brand")
                    if isinstance(brand, dict):
                        brand = brand.get("name")
                    if brand and isinstance(brand, str):
                        return brand.strip()
            except Exception:
                pass
        for attr, val in [("itemprop", "brand"), ("property", "product:brand")]:
            elem = soup.find(attrs={attr: val})
            if elem:
                text = elem.get("content") or elem.get_text(strip=True)
                if text:
                    return text.strip()
        for pattern in [{"class": "brand"}, {"id": "brand"}, {"class": "product-brand"}]:
            elem = soup.find(attrs=pattern)
            if elem:
                text = elem.get_text(strip=True)
                if text and len(text) < 100:
                    return text
        return None

    def _extract_description_fallback(self, soup: BeautifulSoup) -> Optional[str]:
        for prop in ["og:description", "description"]:
            meta = soup.find("meta", attrs={"property": prop}) or soup.find(
                "meta", attrs={"name": prop}
            )
            if meta and meta.get("content"):
                return meta["content"].strip()[:1000]
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    desc = data.get("description")
                    if desc and isinstance(desc, str):
                        return desc.strip()[:1000]
            except Exception:
                pass
        elem = soup.find(attrs={"itemprop": "description"})
        if elem:
            return elem.get_text(strip=True)[:1000]
        return None

    def _extract_identifiers_fallback(self, soup: BeautifulSoup) -> tuple:
        mpn = None
        upc_ean = None

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    if not mpn and data.get("mpn"):
                        mpn = str(data["mpn"]).strip()
                    for key in ("gtin13", "gtin12", "gtin8", "gtin"):
                        if not upc_ean and data.get(key):
                            upc_ean = re.sub(r"\s+", "", str(data[key]))
                            break
            except Exception:
                pass

        if not mpn:
            elem = soup.find(attrs={"itemprop": "mpn"})
            if elem:
                mpn = (elem.get("content") or elem.get_text(strip=True)).strip()
        for gtin_prop in ("gtin13", "gtin12", "gtin8", "gtin"):
            if not upc_ean:
                elem = soup.find(attrs={"itemprop": gtin_prop})
                if elem:
                    upc_ean = re.sub(r"\s+", "", elem.get("content") or elem.get_text(strip=True))

        return mpn, upc_ean

    def _extract_promotion_fallback(self, soup: BeautifulSoup) -> tuple:
        from scrapers.promotion_detector import detect_promotions
        page_text = soup.get_text(" ", strip=True)
        promos = detect_promotions(soup, page_text)
        label = promos[0]["description"] if promos else None
        return label, promos


# ── Convenience function ──────────────────────────────────────────────────────

async def scrape_competitor_product(
    url: str,
    price_selector: Optional[str] = None,
    title_selector: Optional[str] = None,
    stock_selector: Optional[str] = None,
    image_selector: Optional[str] = None,
    output_format: str = "json",
    capture_screenshot: bool = False,
) -> Dict:
    """
    One-shot convenience wrapper.  Creates a single-use pool for this call.
    For scraping multiple URLs, instantiate GenericWebScraper with a shared
    BrowserPool instead to amortise the browser startup cost.
    """
    pool = BrowserPool(pool_size=1)
    try:
        scraper = GenericWebScraper(browser_pool=pool)
        return await scraper.scrape_product(
            url, price_selector, title_selector, stock_selector, image_selector,
            output_format=output_format, capture_screenshot=capture_screenshot,
        )
    finally:
        await pool.close()
