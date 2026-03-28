"""
eBay-Specific Web Scraper

Optimised for ebay.com product pages and search:
  - JSON-LD extraction first (most reliable across DOM changes)
  - Handles both fixed-price (Buy It Now) and auction listings
  - 40+ structured fields including eBay-specific data (condition,
    bids, time remaining, watchers, sold count, seller feedback)
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

_ITEM_ID_RE = re.compile(r"/itm/(?:[^/]+/)?(\d{10,13})", re.IGNORECASE)
_PRICE_RE = re.compile(r"[\d,]+\.?\d*")


class EbayScraper:
    """
    Specialized scraper for ebay.com.

    Usage:
        pool = BrowserPool(pool_size=2)
        scraper = EbayScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.ebay.com/itm/...")
        results = await scraper.search_products("sony headphones")
        await pool.close()
    """

    BASE_URL = "https://www.ebay.com"

    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        self._pool = browser_pool
        self._owns_pool = browser_pool is None

    async def _get_pool(self) -> BrowserPool:
        if self._pool is None:
            self._pool = BrowserPool(pool_size=1)
        return self._pool

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape_product(self, url: str) -> Dict:
        """Scrape an eBay listing and return structured data."""
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

                # Wait for price element
                try:
                    await page.wait_for_selector(
                        ".x-price-primary, #prcIsum, .notranslate",
                        timeout=6000,
                    )
                except Exception:
                    pass

                html = await page.content()

            soup = BeautifulSoup(html, "html.parser")

            # 1. JSON-LD first
            self._extract_json_ld(result, soup)

            # 2. Fill gaps from DOM
            self._extract_dom(result, soup, url)

        except Exception as e:
            result["error"] = str(e)

        return result

    async def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search eBay and return top matching listings."""
        search_url = f"{self.BASE_URL}/sch/i.html?_nkw={quote_plus(query)}&_sop=12"  # sort by Best Match
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
                    return {"error": "CAPTCHA detected on eBay search"}

                try:
                    await page.wait_for_selector(".s-item", timeout=8000)
                except Exception:
                    pass

                soup = BeautifulSoup(await page.content(), "html.parser")

            for card in soup.select(".s-item")[:max_results + 2]:  # +2 for promoted/header items
                product = self._extract_search_card(card)
                if product:
                    results.append(product)
                    if len(results) >= max_results:
                        break

        except Exception as e:
            return {"error": str(e)}

        return results

    # ── JSON-LD extraction ────────────────────────────────────────────────────

    def _extract_json_ld(self, result: Dict, soup: BeautifulSoup):
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, list):
                    data = next((d for d in data if d.get("@type") == "Product"), {})
                if data.get("@type") != "Product":
                    continue

                result["title"] = data.get("name") or result["title"]
                result["description"] = (data.get("description") or "")[:1000] or result["description"]
                result["brand"] = (
                    data.get("brand", {}).get("name")
                    if isinstance(data.get("brand"), dict)
                    else data.get("brand")
                ) or result["brand"]
                result["mpn"] = data.get("mpn") or result["mpn"]
                result["model"] = data.get("model") or result["model"]

                for key in ("gtin13", "gtin12", "gtin8", "gtin"):
                    if data.get(key):
                        result["upc_ean"] = str(data[key]).strip()
                        break

                img = data.get("image")
                if isinstance(img, list):
                    img = img[0]
                if isinstance(img, dict):
                    img = img.get("url") or img.get("contentUrl")
                result["image_url"] = img or result["image_url"]

                agg = data.get("aggregateRating", {})
                if agg:
                    result["rating"] = _safe_float(agg.get("ratingValue"))
                    result["review_count"] = _safe_int(
                        agg.get("reviewCount") or agg.get("ratingCount")
                    )

                offers = data.get("offers") or data.get("offer")
                if isinstance(offers, list):
                    offers = offers[0]
                if isinstance(offers, dict):
                    result["price"] = _safe_float(offers.get("price"))
                    result["currency"] = offers.get("priceCurrency", "USD")
                    availability = offers.get("availability") or ""
                    result["in_stock"] = "InStock" in availability or "PreOrder" in availability
                    result["condition"] = offers.get("itemCondition", "").split("/")[-1] or result["condition"]

                return
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
                ".x-item-title__mainTitle .ux-textspans--BOLD",
                ".x-item-title__mainTitle",
                "#itemTitle span",
                "h1.it-ttl",
                "h1",
            ):
                el = soup.select_one(sel)
                if el:
                    result["title"] = el.get_text(strip=True)
                    break

        # Price — Buy It Now
        if result["price"] is None:
            result["price"], result["currency"] = self._extract_price(soup)

        # Was-price (original / strike-through)
        if result["was_price"] is None:
            result["was_price"] = self._extract_was_price(soup)

        if result["was_price"] and result["price"] and result["was_price"] > result["price"]:
            result["discount_pct"] = round((1 - result["price"] / result["was_price"]) * 100, 1)

        # Auction fields
        bid_el = soup.select_one("#prcIsum_bidPrice, .vi-price--bid .notranslate")
        if bid_el:
            result["current_bid"] = _safe_float(
                re.sub(r"[^\d.]", "", bid_el.get_text(strip=True))
            )

        bids_el = soup.select_one("#qty-test, .vi-bid-count, [class*='bid-count']")
        if bids_el:
            result["bid_count"] = _safe_int(re.sub(r"[^\d]", "", bids_el.get_text()))

        time_el = soup.select_one(".vi-tm-left, [data-testid='TIME_LEFT']")
        if time_el:
            result["time_remaining"] = time_el.get_text(strip=True)

        # Listing type
        if soup.select_one(".vi-bin-btn, #binBtn_btn, [data-testid='ux-call-to-action']"):
            result["listing_type"] = "buy_it_now"
        elif result["bid_count"] is not None:
            result["listing_type"] = "auction"
        else:
            result["listing_type"] = "fixed_price"

        # Condition fallback
        if not result["condition"]:
            el = soup.select_one(
                "#lblCondition, .ux-textspans--SECONDARY, [data-testid='x-item-condition'] .ux-textspans"
            )
            if el:
                result["condition"] = el.get_text(strip=True)

        # Image fallback
        if not result["image_url"]:
            for sel in (
                "#icImg",
                ".ux-image-carousel-item img",
                ".vi-image-gallery__image img",
                "[data-testid='ux-image-carousel-item'] img",
            ):
                img = soup.select_one(sel)
                if img:
                    src = img.get("src") or img.get("data-zoom-src") or img.get("data-src")
                    if src and not src.startswith("data:"):
                        result["image_url"] = src
                        break

        # Seller info
        seller_el = soup.select_one(
            ".seller-persona, [data-testid='x-seller-info'] a, .mbg-nw"
        )
        if seller_el:
            result["seller_name"] = seller_el.get_text(strip=True)

        feedback_el = soup.select_one(
            "[data-testid='x-seller-info'] .ux-textspans--PSEUDOLINK + span, "
            ".mbg-feedback span"
        )
        if feedback_el:
            text = feedback_el.get_text(strip=True)
            m = re.search(r"([\d.]+)%", text)
            if m:
                result["seller_feedback_pct"] = float(m.group(1))

        # Watchers / sold count
        social_el = soup.select_one(
            "[data-testid='x-quantity-sold'], .vi-quantity, .watchcount"
        )
        if social_el:
            text = social_el.get_text(strip=True)
            if "sold" in text.lower():
                result["sold_count"] = _safe_int(re.sub(r"[^\d]", "", text))
            elif "watch" in text.lower():
                result["watcher_count"] = _safe_int(re.sub(r"[^\d]", "", text))

        # Shipping
        ship_el = soup.select_one(
            "[data-testid='ux-labels-values--shipping'] .ux-textspans, "
            ".vi-shipping-cost .notranslate"
        )
        if ship_el:
            text = ship_el.get_text(strip=True).lower()
            if "free" in text:
                result["shipping_cost"] = 0.0
            else:
                m = _PRICE_RE.search(text.replace(",", ""))
                if m:
                    result["shipping_cost"] = _safe_float(m.group())

        # Returns
        returns_el = soup.select_one(
            "[data-testid='ux-labels-values--returns'] .ux-textspans"
        )
        if returns_el:
            result["returns_accepted"] = "no return" not in returns_el.get_text(strip=True).lower()

        # Item specifics (specs table)
        specs = {}
        for row in soup.select(
            ".ux-layout-section-evo__item, "
            ".ux-labels-values, "
            "[data-testid='ux-labels-values']"
        ):
            label = row.select_one(".ux-labels-values__labels .ux-textspans")
            value = row.select_one(".ux-labels-values__values .ux-textspans")
            if label and value:
                specs[label.get_text(strip=True)] = value.get_text(strip=True)
        result["specifications"] = specs or None

        # Promotions
        promos = []
        for sel in ("[class*='discount-badge']", ".vi-seller-deal", "[class*='deal']"):
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    promos.append({"type": "discount", "description": text})
        result["promotions"] = promos
        result["promotion_label"] = promos[0]["description"] if promos else None

    # ── Price helpers ─────────────────────────────────────────────────────────

    def _extract_price(self, soup: BeautifulSoup):
        for sel in (
            ".x-price-primary .ux-textspans",
            "#prcIsum",
            ".notranslate.vi-price",
            "[itemprop='price']",
        ):
            el = soup.select_one(sel)
            if el:
                raw = el.get("content") or el.get_text(strip=True)
                currency = "USD"
                if "£" in raw or "GBP" in raw:
                    currency = "GBP"
                elif "€" in raw or "EUR" in raw:
                    currency = "EUR"
                m = _PRICE_RE.search(raw.replace(",", ""))
                if m:
                    try:
                        return float(m.group()), currency
                    except ValueError:
                        pass
        return None, "USD"

    def _extract_was_price(self, soup: BeautifulSoup) -> Optional[float]:
        for sel in (
            ".x-strikethrough-price .ux-textspans",
            "#orgPrc",
            ".vi-originalPrice .notranslate",
            "[class*='original-price'] .notranslate",
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

    def _extract_search_card(self, card) -> Optional[Dict]:
        try:
            title_el = card.select_one(
                ".s-item__title, .s-item__title span"
            )
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            # Skip the injected "Shop on eBay" card
            if "shop on ebay" in title.lower() or not title:
                return None

            link_el = card.select_one(".s-item__link, a.s-item__link")
            url = link_el.get("href") if link_el else None

            price_el = card.select_one(".s-item__price")
            price = None
            if price_el:
                m = _PRICE_RE.search(price_el.get_text(strip=True).replace(",", ""))
                if m:
                    try:
                        price = float(m.group())
                    except ValueError:
                        pass

            img = card.select_one(".s-item__image-wrapper img")
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")
                # Skip placeholder SVGs
                if image_url and image_url.startswith("data:"):
                    image_url = None

            condition_el = card.select_one(".SECONDARY_INFO")
            condition = condition_el.get_text(strip=True) if condition_el else None

            shipping_el = card.select_one(".s-item__shipping")
            shipping_cost = None
            if shipping_el:
                text = shipping_el.get_text(strip=True).lower()
                if "free" in text:
                    shipping_cost = 0.0

            return {
                "title": title,
                "url": url,
                "price": price,
                "currency": "USD",
                "image_url": image_url,
                "condition": condition,
                "shipping_cost": shipping_cost,
            }
        except Exception:
            return None

    # ── Block detection ───────────────────────────────────────────────────────

    @staticmethod
    async def _is_blocked(page) -> bool:
        try:
            content = (await page.content()).lower()
            return any(k in content for k in (
                "robot check", "captcha", "security check",
                "access to this page has been denied",
                "unusual activity",
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
            "model": None,
            "description": None,
            # Pricing
            "price": None,
            "was_price": None,
            "discount_pct": None,
            "currency": "USD",
            "shipping_cost": None,
            # Stock / listing
            "in_stock": True,
            "listing_type": None,          # "buy_it_now" | "auction" | "fixed_price"
            "condition": None,             # "New", "Used", "Refurbished", etc.
            # Auction-specific
            "current_bid": None,
            "bid_count": None,
            "time_remaining": None,
            # Seller
            "seller_name": None,
            "seller_feedback_pct": None,
            # Social proof
            "rating": None,
            "review_count": None,
            "sold_count": None,
            "watcher_count": None,
            # Media
            "image_url": None,
            # Identifiers
            "mpn": None,
            "upc_ean": None,
            # Misc
            "returns_accepted": None,
            "promotion_label": None,
            "promotions": [],
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
