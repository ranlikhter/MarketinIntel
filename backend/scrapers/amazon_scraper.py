"""
Amazon-Specific Web Scraper

Optimised for Amazon.com:
  - Uses a shared BrowserPool so the Chromium process is launched once and
    reused across all scrape calls (eliminates the 2-3 s per-call startup).
  - Pre-navigation delays removed; only a short post-load settle is kept.
  - Anti-bot headers, random user agents, and CAPTCHA detection retained.
"""

import asyncio
import json
import random
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeout

from scrapers.browser_pool import BrowserPool


# ── Shared HTTP headers ───────────────────────────────────────────────────────
_ACCEPT_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class AmazonScraper:
    """
    Specialized scraper for Amazon.com with anti-detection measures.

    Pass a shared BrowserPool for best performance across multiple calls:
        pool = BrowserPool(pool_size=2)
        scraper = AmazonScraper(browser_pool=pool)
        results = await scraper.search_products("Sony headphones")
        data    = await scraper.scrape_product("https://www.amazon.com/dp/...")
        await pool.close()
    """

    def __init__(
        self,
        domain: str = "amazon.com",
        browser_pool: Optional[BrowserPool] = None,
    ):
        self.domain = domain
        self.base_url = f"https://www.{domain}"
        self._pool = browser_pool
        self._owns_pool = browser_pool is None

    async def _get_pool(self) -> BrowserPool:
        if self._pool is None:
            self._pool = BrowserPool(pool_size=1)
        return self._pool

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Amazon and return the top results."""
        search_url = f"{self.base_url}/s?k={quote_plus(query)}"
        results = []

        try:
            pool = await self._get_pool()
            ua = random.choice(_USER_AGENTS)
            async with pool.acquire_page(
                user_agent=ua,
                extra_headers=_ACCEPT_HEADERS,
            ) as page:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                if await self._detect_captcha(page):
                    return {"error": "CAPTCHA detected — Amazon is blocking automated access"}

                try:
                    await page.wait_for_selector(
                        '[data-component-type="s-search-result"]', timeout=8000
                    )
                except Exception:
                    pass

                soup = BeautifulSoup(await page.content(), "html.parser")

            for card in soup.select('[data-component-type="s-search-result"]')[:max_results]:
                product = self._extract_search_result(card)
                if product:
                    results.append(product)

        except Exception as e:
            return {"error": str(e)}

        return results

    async def scrape_product(self, url: str) -> Dict:
        """Scrape detailed data from an Amazon product page."""
        result = {
            "url": url,
            "title": None, "asin": None,
            "price": None, "was_price": None, "discount_pct": None,
            "currency": "USD",
            "in_stock": True,
            "image_url": None,
            "rating": None, "review_count": None,
            "brand": None, "description": None,
            "mpn": None, "upc_ean": None,
            "promotion_label": None,
            "seller_name": None, "seller_count": None,
            "is_prime": None, "fulfillment_type": None,
            "product_condition": "New",
            "category": None, "variant": None,
            "shipping_cost": None, "total_price": None,
            "scrape_quality": "clean",
            "error": None,
        }

        try:
            pool = await self._get_pool()
            ua = random.choice(_USER_AGENTS)
            async with pool.acquire_page(
                user_agent=ua,
                extra_headers=_ACCEPT_HEADERS,
            ) as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.evaluate("window.scrollBy(0, Math.random() * 400)")
                await asyncio.sleep(random.uniform(0.4, 0.8))

                if await self._detect_captcha(page):
                    result["error"] = "CAPTCHA detected"
                    return result

                soup = BeautifulSoup(await page.content(), "html.parser")

        except PlaywrightTimeout:
            result["error"] = "Page load timeout"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

        asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
        if asin_match:
            result["asin"] = asin_match.group(1)

        result["title"] = self._extract_title(soup)
        result["price"], result["currency"] = self._extract_price(soup)
        result["was_price"] = self._extract_was_price(soup)
        result["in_stock"] = self._extract_stock_status(soup)
        result["image_url"] = self._extract_image(soup, url)
        result["rating"], result["review_count"] = self._extract_reviews(soup)
        result["brand"] = self._extract_brand(soup)
        result["description"] = self._extract_description(soup)
        result["promotion_label"] = self._extract_promotion_label(soup)
        result["seller_name"], result["fulfillment_type"] = self._extract_seller_info(soup)
        result["seller_count"] = self._extract_seller_count(soup)
        result["is_prime"] = self._extract_is_prime(soup)
        result["product_condition"] = self._extract_condition(soup)
        result["category"] = self._extract_category(soup)
        result["variant"] = self._extract_variant(soup)
        result["shipping_cost"] = self._extract_shipping_cost(soup)
        result["mpn"], result["upc_ean"] = self._extract_product_identifiers(soup)
        result["scrape_quality"] = "partial" if not result["price"] else "clean"

        if result["was_price"] and result["price"] and result["was_price"] > result["price"]:
            result["discount_pct"] = round(
                (1 - result["price"] / result["was_price"]) * 100, 1
            )
        if result["price"] is not None:
            result["total_price"] = (
                round(result["price"] + result["shipping_cost"], 2)
                if result["shipping_cost"] is not None
                else result["price"]
            )

        return result

    # ── Anti-detection ────────────────────────────────────────────────────────

    async def _detect_captcha(self, page) -> bool:
        content = await page.content()
        indicators = [
            "Enter the characters you see below",
            "Type the characters you see in this image",
            "api-services-support@amazon.com",
            "Sorry, we just need to make sure you're not a robot",
        ]
        content_lower = content.lower()
        return any(ind.lower() in content_lower for ind in indicators)

    # ── Search result extraction ──────────────────────────────────────────────

    def _extract_search_result(self, card) -> Optional[Dict]:
        try:
            asin = card.get("data-asin")
            if not asin:
                return None

            title_elem = card.select_one("h2 a span")
            title = title_elem.text.strip() if title_elem else None

            url_elem = card.select_one("h2 a")
            url = urljoin(self.base_url, url_elem["href"]) if url_elem else None

            price_whole = card.select_one(".a-price-whole")
            price_fraction = card.select_one(".a-price-fraction")
            price = None
            if price_whole:
                price_text = price_whole.text.strip().replace(",", "")
                if price_fraction:
                    price_text += "." + price_fraction.text.strip()
                try:
                    price = float(price_text)
                except (ValueError, TypeError):
                    pass

            image_elem = card.select_one("img.s-image")
            image_url = image_elem["src"] if image_elem else None

            rating_elem = card.select_one(".a-icon-star-small span.a-icon-alt")
            rating = None
            if rating_elem:
                m = re.search(r"(\d+\.?\d*)", rating_elem.text)
                if m:
                    rating = float(m.group(1))

            review_count = None
            review_elem = card.select_one('[aria-label*="stars"]')
            if review_elem:
                m = re.search(r"([\d,]+)", review_elem.get("aria-label", ""))
                if m:
                    review_count = int(m.group(1).replace(",", ""))

            was_price = None
            was_elem = card.select_one(".a-price.a-text-price .a-offscreen")
            if was_elem:
                try:
                    was_price = float(
                        was_elem.get_text(strip=True).replace("$", "").replace(",", "")
                    )
                except (ValueError, TypeError):
                    pass

            promo_elem = card.select_one(".a-badge-label, .s-coupon-unclipped")
            promotion_label = promo_elem.get_text(strip=True)[:100] if promo_elem else None
            is_prime = bool(card.select_one(".a-icon-prime"))

            return {
                "title": title,
                "asin": asin,
                "price": price,
                "was_price": was_price,
                "discount_pct": (
                    round((1 - price / was_price) * 100, 1)
                    if was_price and price and was_price > price
                    else None
                ),
                "currency": "USD",
                "url": url,
                "image_url": image_url,
                "rating": rating,
                "review_count": review_count,
                "promotion_label": promotion_label,
                "is_prime": is_prime,
                "scrape_quality": "clean" if price else "partial",
            }

        except Exception:
            return None

    # ── Product page extraction ───────────────────────────────────────────────

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        for sel in ["#productTitle", "#title", "span#productTitle", "h1.a-size-large"]:
            elem = soup.select_one(sel)
            if elem:
                return elem.text.strip()
        return None

    def _extract_price(self, soup: BeautifulSoup) -> tuple:
        price_whole = soup.select_one(".a-price-whole")
        price_fraction = soup.select_one(".a-price-fraction")
        if price_whole:
            price_text = price_whole.text.strip().replace(",", "").replace(".", "")
            if price_fraction:
                price_text += "." + price_fraction.text.strip()
            try:
                return float(price_text), "USD"
            except (ValueError, TypeError):
                pass

        for sel in [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-color-price",
        ]:
            elem = soup.select_one(sel)
            if elem:
                try:
                    return float(elem.text.strip().replace("$", "").replace(",", "")), "USD"
                except (ValueError, TypeError):
                    pass

        return None, "USD"

    def _extract_stock_status(self, soup: BeautifulSoup) -> bool:
        for sel in [
            "#availability .a-color-price",
            "#availability .a-color-state",
            ".a-color-price",
        ]:
            elem = soup.select_one(sel)
            if elem:
                text = elem.text.lower()
                if any(w in text for w in ["unavailable", "out of stock", "currently unavailable"]):
                    return False
        avail = soup.select_one("#availability span")
        if avail and "in stock" in avail.text.lower():
            return True
        return True

    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        for sel in ["#landingImage", "#imgBlkFront", ".a-dynamic-image"]:
            img = soup.select_one(sel)
            if img:
                data_old = img.get("data-old-hires")
                if data_old:
                    return data_old
                src = img.get("src")
                if src:
                    return src
        return None

    def _extract_reviews(self, soup: BeautifulSoup) -> tuple:
        rating = None
        review_count = None
        rating_elem = soup.select_one("#acrPopover")
        if rating_elem:
            m = re.search(r"(\d+\.?\d*)", rating_elem.get("title", ""))
            if m:
                rating = float(m.group(1))
        review_elem = soup.select_one("#acrCustomerReviewText")
        if review_elem:
            m = re.search(r"([\d,]+)", review_elem.text)
            if m:
                review_count = int(m.group(1).replace(",", ""))
        return rating, review_count

    def _extract_brand(self, soup: BeautifulSoup) -> Optional[str]:
        elem = soup.select_one("#bylineInfo")
        if elem:
            return re.sub(r"Visit the |Store| Brand:", "", elem.text.strip()).strip()
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        features = soup.select("#feature-bullets ul li span.a-list-item")
        if features:
            return " | ".join(
                f.text.strip() for f in features[:5] if f.text.strip()
            )[:1000]
        elem = soup.select_one("#productDescription")
        if elem:
            return elem.text.strip()[:1000]
        return None

    def _extract_product_identifiers(self, soup: BeautifulSoup) -> tuple:
        mpn = None
        upc_ean = None

        for row in soup.select(
            "#productDetails_techSpec_section_1 tr, "
            "#productDetails_detailBullets_sections1 tr"
        ):
            th = row.select_one("th")
            td = row.select_one("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            value = td.get_text(strip=True)
            if any(k in label for k in ["part number", "item model number", "model number", "mpn"]):
                if not mpn:
                    mpn = value
            elif "upc" in label and not upc_ean:
                upc_ean = re.sub(r"\s+", "", value)
            elif "ean" in label and not upc_ean:
                upc_ean = re.sub(r"\s+", "", value)

        for li in soup.select(
            "#detailBulletsWrapper_feature_div li, #detail-bullets .content li"
        ):
            text = li.get_text(" ", strip=True)
            label_lower = text.lower()
            if ("part number" in label_lower or "item model number" in label_lower) and not mpn:
                m = re.search(r"[:\u200e]\s*(.+)", text)
                if m:
                    mpn = m.group(1).strip()
            elif "upc" in label_lower and not upc_ean:
                m = re.search(r"[:\u200e]\s*([\d ]+)", text)
                if m:
                    upc_ean = re.sub(r"\s+", "", m.group(1))
            elif "ean" in label_lower and not upc_ean:
                m = re.search(r"[:\u200e]\s*([\d ]+)", text)
                if m:
                    upc_ean = re.sub(r"\s+", "", m.group(1))

        return mpn, upc_ean

    def _extract_was_price(self, soup: BeautifulSoup) -> Optional[float]:
        for sel in [
            ".a-price.a-text-price .a-offscreen",
            "#listPrice",
            ".a-text-strike",
            "[data-a-strike='true'] .a-offscreen",
        ]:
            elem = soup.select_one(sel)
            if elem:
                try:
                    val = float(elem.get_text(strip=True).replace("$", "").replace(",", ""))
                    if val > 0:
                        return val
                except (ValueError, TypeError):
                    pass
        basis = soup.select_one("#basisPrice .a-offscreen")
        if basis:
            try:
                return float(basis.get_text(strip=True).replace("$", "").replace(",", ""))
            except (ValueError, TypeError):
                pass
        return None

    def _extract_promotion_label(self, soup: BeautifulSoup) -> Optional[str]:
        for sel in [
            "#dealBadgeOverlay .a-badge-label",
            "#promotionBadgeWrapper",
            ".promoPriceBlockMessage",
            "[id^='couponBadge']",
            ".a-badge-text",
            "#savingsCallout",
        ]:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if text and len(text) < 100:
                    return text[:100]
        coupon = soup.select_one("#couponBadge_feature_div")
        if coupon:
            text = coupon.get_text(strip=True)
            if text:
                return text[:100]
        return None

    def _extract_seller_info(self, soup: BeautifulSoup) -> tuple:
        seller_name = None
        fulfillment_type = "merchant"

        merchant_info = soup.select_one("#merchantInfo") or soup.select_one("#tabular-buybox")
        if merchant_info:
            text = merchant_info.get_text(" ", strip=True)
            if "amazon.com" in text.lower() or "amazon" in text.lower():
                seller_name = "Amazon"
                fulfillment_type = "FBA"
            else:
                m = re.search(r"(?:Sold by|seller:)\s+([^\n.]+)", text, re.IGNORECASE)
                if m:
                    seller_name = m.group(1).strip()
                if re.search(r"Fulfilled by Amazon", text, re.IGNORECASE):
                    fulfillment_type = "FBA"
                elif seller_name:
                    fulfillment_type = "FBM"

        if not seller_name:
            sold_by = soup.select_one("#sellerProfileTriggerId")
            if sold_by:
                seller_name = sold_by.get_text(strip=True)
                fulfillment_type = "FBM"

        return seller_name, fulfillment_type

    def _extract_seller_count(self, soup: BeautifulSoup) -> Optional[int]:
        offers_link = soup.select_one("#olp-upd-new a, #olp_feature_div a, .olp-link")
        if offers_link:
            m = re.search(r"(\d+)\s+(?:new|used)", offers_link.get_text(strip=True), re.IGNORECASE)
            if m:
                return int(m.group(1))
        other = soup.select_one("#buybox-see-all-buying-choices")
        if other:
            m = re.search(r"(\d+)", other.get_text(strip=True))
            if m:
                return int(m.group(1))
        return None

    def _extract_is_prime(self, soup: BeautifulSoup) -> Optional[bool]:
        if soup.select_one('.a-icon-prime, #primeSavingsUpsellCaption, [aria-label*="Prime"]'):
            return True
        if soup.find(string=re.compile(r"FREE Prime delivery|Prime FREE", re.IGNORECASE)):
            return True
        if soup.find(string=re.compile(r"Not Prime eligible", re.IGNORECASE)):
            return False
        return None

    def _extract_condition(self, soup: BeautifulSoup) -> str:
        elem = soup.select_one("#newAccordionRow .a-color-secondary")
        if elem:
            text = elem.get_text(strip=True).lower()
            if "used" in text:
                return "Used"
            if "refurb" in text or "renewed" in text:
                return "Refurbished"
        return "New"

    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        breadcrumbs = soup.select(
            "#wayfinding-breadcrumbs_container li:not(.a-breadcrumb-divider)"
        )
        if breadcrumbs:
            crumbs = [b.get_text(strip=True) for b in breadcrumbs if b.get_text(strip=True)]
            if crumbs:
                return " > ".join(crumbs[:3])
        return None

    def _extract_variant(self, soup: BeautifulSoup) -> Optional[str]:
        sel = soup.select_one(".selection, #selected-color-name, #selected-size-name")
        if sel:
            return sel.get_text(strip=True)[:100]
        parts = [
            t.get_text(strip=True)
            for t in soup.select(".a-form-label + .selection")[:2]
            if t.get_text(strip=True)
        ]
        if parts:
            return ", ".join(parts)[:100]
        return None

    def _extract_shipping_cost(self, soup: BeautifulSoup) -> Optional[float]:
        for sel in ["#deliveryMessageMirId", "#ddmDeliveryMessage", "#fast-track-message"]:
            elem = soup.select_one(sel)
            if elem and "free" in elem.get_text(strip=True).lower():
                return 0.0
        for sel in ["#shippingMessageInsideBuyBox_feature_div", ".shipping3P"]:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if "free" in text.lower():
                    return 0.0
                m = re.search(r"\$(\d+\.?\d*)", text)
                if m:
                    try:
                        return float(m.group(1))
                    except (ValueError, TypeError):
                        pass
        return None


# ── Convenience functions ─────────────────────────────────────────────────────

async def search_amazon(query: str, max_results: int = 10) -> List[Dict]:
    """One-shot Amazon search.  Creates a single-use pool for this call."""
    pool = BrowserPool(pool_size=1)
    try:
        return await AmazonScraper(browser_pool=pool).search_products(query, max_results)
    finally:
        await pool.close()


async def scrape_amazon_product(url: str) -> Dict:
    """One-shot Amazon product scrape.  Creates a single-use pool for this call."""
    pool = BrowserPool(pool_size=1)
    try:
        return await AmazonScraper(browser_pool=pool).scrape_product(url)
    finally:
        await pool.close()
