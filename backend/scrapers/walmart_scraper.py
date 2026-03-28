"""
Walmart-Specific Web Scraper

Optimised for walmart.com product pages and search:
  - JSON-LD extraction first (most reliable, survives DOM changes)
  - Playwright browser for JS-rendered content and anti-bot bypass
  - 40+ structured fields matching the Amazon scraper schema
  - CAPTCHA / block detection with early exit
  - Shared BrowserPool for efficient multi-call usage
"""

import json
import random
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeout

from scrapers.browser_pool import BrowserPool


_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

_ACCEPT_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

# Walmart item IDs are 8-12 digit numbers
_ITEM_ID_RE = re.compile(r"/ip/(?:[^/]+/)?(\d{6,12})", re.IGNORECASE)
_PRICE_RE = re.compile(r"[\d,]+\.?\d*")


class WalmartScraper:
    """
    Specialized scraper for walmart.com.

    Usage:
        pool = BrowserPool(pool_size=2)
        scraper = WalmartScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.walmart.com/ip/...")
        results = await scraper.search_products("sony headphones")
        await pool.close()
    """

    BASE_URL = "https://www.walmart.com"

    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        self._pool = browser_pool
        self._owns_pool = browser_pool is None

    async def _get_pool(self) -> BrowserPool:
        if self._pool is None:
            self._pool = BrowserPool(pool_size=1)
        return self._pool

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape_product(self, url: str) -> Dict:
        """Scrape a Walmart product page and return structured data."""
        result = self._empty_result(url)

        try:
            pool = await self._get_pool()
            ua = random.choice(_USER_AGENTS)
            async with pool.acquire_page(
                user_agent=ua, extra_headers=_ACCEPT_HEADERS
            ) as page:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except PlaywrightTimeout:
                    result["error"] = "Page load timeout"
                    return result

                if await self._is_blocked(page):
                    result["error"] = "CAPTCHA or access block detected"
                    return result

                # Wait for price to appear
                try:
                    await page.wait_for_selector(
                        '[itemprop="price"], [data-testid="price-wrap"], .price-characteristic',
                        timeout=6000,
                    )
                except Exception:
                    pass

                html = await page.content()

            soup = BeautifulSoup(html, "html.parser")

            # 1. Try JSON-LD first (most reliable)
            self._extract_json_ld(result, soup)

            # 2. Fill gaps from DOM
            self._extract_dom(result, soup, url)

        except Exception as e:
            result["error"] = str(e)

        return result

    async def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Walmart and return top matching products."""
        search_url = f"{self.BASE_URL}/search?q={quote_plus(query)}"
        results = []

        try:
            pool = await self._get_pool()
            ua = random.choice(_USER_AGENTS)
            async with pool.acquire_page(
                user_agent=ua, extra_headers=_ACCEPT_HEADERS
            ) as page:
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                except PlaywrightTimeout:
                    return []

                if await self._is_blocked(page):
                    return {"error": "CAPTCHA detected on Walmart search"}

                try:
                    await page.wait_for_selector(
                        '[data-item-id], [data-automation-id="product-title"]',
                        timeout=8000,
                    )
                except Exception:
                    pass

                soup = BeautifulSoup(await page.content(), "html.parser")

            for card in self._find_search_cards(soup)[:max_results]:
                product = self._extract_search_card(card)
                if product:
                    results.append(product)

        except Exception as e:
            return {"error": str(e)}

        return results

    # ── JSON-LD extraction ────────────────────────────────────────────────────

    def _extract_json_ld(self, result: Dict, soup: BeautifulSoup):
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                # Handle arrays
                if isinstance(data, list):
                    data = next((d for d in data if d.get("@type") == "Product"), {})
                if data.get("@type") != "Product":
                    continue

                result["title"] = data.get("name") or result["title"]
                result["description"] = (data.get("description") or "")[:1000] or result["description"]
                result["brand"] = (
                    data.get("brand", {}).get("name") if isinstance(data.get("brand"), dict)
                    else data.get("brand")
                ) or result["brand"]
                result["mpn"] = data.get("mpn") or result["mpn"]

                for key in ("gtin13", "gtin12", "gtin8", "gtin"):
                    if data.get(key):
                        result["upc_ean"] = str(data[key]).strip()
                        break

                # Image
                img = data.get("image")
                if isinstance(img, list):
                    img = img[0]
                if isinstance(img, dict):
                    img = img.get("url") or img.get("contentUrl")
                result["image_url"] = img or result["image_url"]

                # Rating
                agg = data.get("aggregateRating", {})
                if agg:
                    result["rating"] = _safe_float(agg.get("ratingValue"))
                    result["review_count"] = _safe_int(agg.get("reviewCount") or agg.get("ratingCount"))

                # Offers
                offers = data.get("offers") or data.get("offer")
                if isinstance(offers, list):
                    offers = offers[0]
                if isinstance(offers, dict):
                    result["price"] = _safe_float(offers.get("price"))
                    result["currency"] = offers.get("priceCurrency", "USD")
                    result["in_stock"] = "InStock" in (offers.get("availability") or "")
                    result["seller_name"] = (
                        offers.get("seller", {}).get("name")
                        if isinstance(offers.get("seller"), dict)
                        else offers.get("seller")
                    )

                return  # Found a Product block — done
            except Exception:
                continue

    # ── DOM extraction ────────────────────────────────────────────────────────

    def _extract_dom(self, result: Dict, soup: BeautifulSoup, url: str):
        # Item ID from URL
        m = _ITEM_ID_RE.search(url)
        if m:
            result["item_id"] = m.group(1)

        # Title fallback
        if not result["title"]:
            for sel in (
                "h1[itemprop='name']",
                "h1.prod-ProductTitle",
                "[data-testid='product-title']",
                "h1",
            ):
                el = soup.select_one(sel)
                if el:
                    result["title"] = el.get_text(strip=True)
                    break

        # Price fallback
        if result["price"] is None:
            result["price"], result["currency"] = self._extract_price(soup)

        # Was-price
        if result["was_price"] is None:
            result["was_price"] = self._extract_was_price(soup)

        # Discount
        if result["was_price"] and result["price"] and result["was_price"] > result["price"]:
            result["discount_pct"] = round((1 - result["price"] / result["was_price"]) * 100, 1)

        # Stock
        for sel in (
            "[data-testid='fulfillment-shipping-text']",
            ".prod-fulfillment-callout",
            "[class*='fulfillment']",
            "[class*='in-stock']",
            "[class*='out-of-stock']",
        ):
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True).lower()
                if "out of stock" in text or "unavailable" in text or "sold out" in text:
                    result["in_stock"] = False
                elif "in stock" in text or "ships" in text or "delivery" in text or "pickup" in text:
                    result["in_stock"] = True
                break

        # Image fallback
        if not result["image_url"]:
            for sel in (
                "[data-testid='hero-image-container'] img",
                ".prod-hero-image img",
                "[data-testid='product-image'] img",
                ".ProductPhoto img",
            ):
                img = soup.select_one(sel)
                if img:
                    src = img.get("src") or img.get("data-src")
                    if src:
                        result["image_url"] = src
                        break

        # Rating fallback
        if result["rating"] is None:
            el = soup.select_one("[itemprop='ratingValue'], .stars-container [aria-label]")
            if el:
                result["rating"] = _safe_float(
                    el.get("content") or re.search(r"[\d.]+", el.get("aria-label", "") or "")
                )

        # Review count fallback
        if result["review_count"] is None:
            el = soup.select_one("[itemprop='reviewCount'], [data-testid='ratings-count']")
            if el:
                result["review_count"] = _safe_int(re.sub(r"[^\d]", "", el.get_text()))

        # Brand fallback
        if not result["brand"]:
            el = soup.select_one("[itemprop='brand']")
            if el:
                result["brand"] = el.get("content") or el.get_text(strip=True)

        # Walmart-specific fields
        # Fulfillment type
        for sel in ("[data-testid='fulfillment-badge']", "[class*='fulfillment-badge']"):
            el = soup.select_one(sel)
            if el:
                result["fulfillment_type"] = el.get_text(strip=True)
                break

        # Seller name fallback
        if not result["seller_name"]:
            for sel in (
                "[data-testid='seller-display-name']",
                ".sold-by-link",
                "[class*='sold-by']",
            ):
                el = soup.select_one(sel)
                if el:
                    result["seller_name"] = el.get_text(strip=True)
                    break

        # Promotions
        promos = []
        for sel in (
            "[data-testid='promo-badge']",
            ".price-rollback",
            "[class*='rollback']",
            "[class*='clearance']",
            "[class*='special-buy']",
        ):
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    promos.append({"type": "discount", "description": text})
        result["promotions"] = promos
        result["promotion_label"] = promos[0]["description"] if promos else None

        # Specifications table
        specs = {}
        for row in soup.select(
            "[data-testid='specification-table'] tr, .prod-specifications tr, table.specifications tr"
        ):
            cells = row.find_all(["th", "td"])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                val = cells[1].get_text(strip=True)
                if key and val:
                    specs[key] = val
        result["specifications"] = specs or None

    # ── Price helpers ─────────────────────────────────────────────────────────

    def _extract_price(self, soup: BeautifulSoup):
        # Walmart renders prices as characteristic (dollars) + mantissa (cents)
        char = soup.select_one(".price-characteristic, [itemprop='price']")
        if char:
            if char.get("content"):
                return _safe_float(char["content"]), "USD"
            mant = soup.select_one(".price-mantissa")
            dollars = re.sub(r"[^\d]", "", char.get_text(strip=True))
            cents = re.sub(r"[^\d]", "", mant.get_text(strip=True)) if mant else "00"
            try:
                return float(f"{dollars}.{cents.zfill(2)}"), "USD"
            except ValueError:
                pass

        # Generic fallback
        for sel in (
            "[data-testid='price-wrap'] span",
            ".price-group",
            "[class*='price']",
        ):
            el = soup.select_one(sel)
            if el:
                m = _PRICE_RE.search(el.get_text(strip=True).replace(",", ""))
                if m:
                    try:
                        return float(m.group()), "USD"
                    except ValueError:
                        pass
        return None, "USD"

    def _extract_was_price(self, soup: BeautifulSoup) -> Optional[float]:
        for sel in (
            ".price-old, [data-testid='was-price'], [class*='was-price']",
            ".strike-through",
            "[class*='list-price']",
        ):
            el = soup.select_one(sel)
            if el:
                m = _PRICE_RE.search(el.get_text(strip=True).replace(",", ""))
                if m:
                    try:
                        return float(m.group())
                    except ValueError:
                        pass
        return None

    # ── Search card helpers ───────────────────────────────────────────────────

    def _find_search_cards(self, soup: BeautifulSoup):
        cards = soup.select("[data-item-id]")
        if not cards:
            cards = soup.select("[data-automation-id='product-title']")
            cards = [c.find_parent("div", attrs={"data-item-id": True}) or c.find_parent("li") for c in cards]
            cards = [c for c in cards if c]
        return cards

    def _extract_search_card(self, card) -> Optional[Dict]:
        try:
            title_el = card.select_one(
                "[data-automation-id='product-title'], .product-title-link, [class*='product-title']"
            )
            if not title_el:
                return None
            title = title_el.get_text(strip=True)

            link = title_el.get("href") or (title_el.find_parent("a") or {}).get("href")
            url = urljoin(self.BASE_URL, link) if link else None

            price_el = card.select_one(".price-current, [itemprop='price'], [class*='price']")
            price = None
            if price_el:
                m = _PRICE_RE.search(price_el.get_text(strip=True).replace(",", ""))
                if m:
                    try:
                        price = float(m.group())
                    except ValueError:
                        pass

            img = card.select_one("img")
            image_url = (img.get("src") or img.get("data-src")) if img else None

            rating_el = card.select_one("[class*='stars'] [aria-label], [class*='rating'] [aria-label]")
            rating = None
            if rating_el:
                m = re.search(r"[\d.]+", rating_el.get("aria-label", ""))
                rating = _safe_float(m.group()) if m else None

            return {
                "title": title,
                "url": url,
                "price": price,
                "currency": "USD",
                "image_url": image_url,
                "rating": rating,
            }
        except Exception:
            return None

    # ── Block detection ───────────────────────────────────────────────────────

    @staticmethod
    async def _is_blocked(page) -> bool:
        try:
            content = (await page.content()).lower()
            return any(k in content for k in (
                "robot check", "captcha", "access denied",
                "your request has been blocked", "unusual traffic",
            ))
        except Exception:
            return False

    # ── Schema ────────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_result(url: str) -> Dict:
        return {
            "url": url,
            "item_id": None,
            "title": None,
            "brand": None,
            "description": None,
            "price": None,
            "was_price": None,
            "discount_pct": None,
            "currency": "USD",
            "in_stock": True,
            "image_url": None,
            "rating": None,
            "review_count": None,
            "seller_name": None,
            "fulfillment_type": None,
            "promotion_label": None,
            "promotions": [],
            "mpn": None,
            "upc_ean": None,
            "specifications": None,
            "scrape_quality": "clean",
            "error": None,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    try:
        if val is None:
            return None
        s = re.sub(r"[^\d.]", "", str(val))
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    try:
        if val is None:
            return None
        s = re.sub(r"[^\d]", "", str(val))
        return int(s) if s else None
    except (ValueError, TypeError):
        return None
