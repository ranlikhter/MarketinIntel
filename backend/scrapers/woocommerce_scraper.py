"""
WooCommerce Competitor Scraper

Scrapes competitor stores running WooCommerce without requiring API credentials.
Uses two strategies in order:

  1. WC Store API  (/wp-json/wc/store/v1/products)  — public, no auth, clean JSON
  2. WC REST API   (/wp-json/wc/v3/products)         — sometimes public on older stores
  3. JSON-LD       (HTML Product schema on pages)     — universal fallback

Detection: a site is WooCommerce if /wp-json/wc/store/v1/products returns HTTP 200.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
}


class WooCommerceScraper:
    """
    Scraper for WooCommerce-powered competitor stores.

    Works against any WooCommerce store that exposes the public Store API
    (available since WC 4.4 / Gutenberg Blocks).  No API keys required.
    """

    def __init__(self, browser_pool=None):
        self._pool = browser_pool  # accepted for API compatibility; not used

    # ── Public interface ──────────────────────────────────────────────────────

    async def scrape_product(self, url: str) -> Dict:
        """
        Scrape a single WooCommerce product page.

        Strategy: extract product ID from URL → fetch via Store API → fallback JSON-LD.
        """
        try:
            origin = _normalise_origin(url)
            product_id = _extract_wc_product_id(url)

            if product_id:
                api_url = f"{origin}/wp-json/wc/store/v1/products/{product_id}"
                data = await _get_json(api_url)
                if data and isinstance(data, dict) and data.get("id"):
                    return _parse_store_product(data, origin)

            # Fallback: fetch the page and extract JSON-LD
            return await self._scrape_via_html(url)

        except Exception as exc:
            logger.exception("WooCommerceScraper.scrape_product failed for %s", url)
            return {"url": url, "error": str(exc)}

    async def search_products(
        self,
        query: str,
        max_results: int = 10,
        store_url: str = "",
    ) -> List[Dict]:
        """
        Search products on a WooCommerce store.

        Tries WC Store API then WC REST API v3; returns [] on failure.
        store_url is required (e.g. "https://competitor.com").
        """
        if not store_url:
            logger.warning("WooCommerceScraper.search_products: store_url required")
            return []

        origin = _normalise_origin(store_url)

        # Strategy 1 — WC Store API (public, no auth)
        results = await self._search_store_api(origin, query, max_results)
        if results:
            return results

        # Strategy 2 — WC REST API v3 (may be open on some stores)
        results = await self._search_rest_api(origin, query, max_results)
        return results

    @staticmethod
    async def is_woocommerce_store(store_url: str) -> bool:
        """
        Probe whether the URL points to a WooCommerce store.

        Returns True if the Store API endpoint responds with a JSON array.
        """
        try:
            origin = _normalise_origin(store_url)
            probe = f"{origin}/wp-json/wc/store/v1/products?per_page=1"
            async with httpx.AsyncClient(
                headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
            ) as client:
                r = await client.get(probe)
            return r.status_code == 200 and isinstance(r.json(), list)
        except Exception:
            return False

    # ── Strategy implementations ──────────────────────────────────────────────

    async def _search_store_api(
        self, origin: str, query: str, max_results: int
    ) -> List[Dict]:
        """WC Store API: /wp-json/wc/store/v1/products?search=..."""
        url = (
            f"{origin}/wp-json/wc/store/v1/products"
            f"?search={quote_plus(query)}&per_page={min(max_results, 100)}"
        )
        data = await _get_json(url)
        if not data or not isinstance(data, list):
            return []
        return [_parse_store_product(p, origin) for p in data[:max_results]]

    async def _search_rest_api(
        self, origin: str, query: str, max_results: int
    ) -> List[Dict]:
        """WC REST API v3: /wp-json/wc/v3/products?search=... (sometimes public)"""
        url = (
            f"{origin}/wp-json/wc/v3/products"
            f"?search={quote_plus(query)}&per_page={min(max_results, 100)}&status=publish"
        )
        data = await _get_json(url)
        if not data or not isinstance(data, list):
            return []
        return [_parse_rest_product(p, origin) for p in data[:max_results]]

    async def _scrape_via_html(self, url: str) -> Dict:
        """Fetch the HTML page and extract Product JSON-LD."""
        try:
            async with httpx.AsyncClient(
                headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
            ) as client:
                r = await client.get(url)
            if r.status_code != 200:
                return {"url": url, "error": f"HTTP {r.status_code}"}
            return _parse_html_json_ld(r.text, url)
        except Exception as exc:
            return {"url": url, "error": str(exc)}


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_store_product(p: dict, origin: str) -> Dict:
    """Parse a WC Store API v1 product object into the normalised schema."""
    prices = p.get("prices") or {}
    minor = int(prices.get("currency_minor_unit") or 2)
    divisor = 10 ** minor

    def _price(key: str) -> Optional[float]:
        raw = prices.get(key)
        if raw is None:
            return None
        try:
            return int(raw) / divisor
        except (ValueError, TypeError):
            return None

    price = _price("price")
    regular = _price("regular_price")
    was_price = regular if (regular and price and regular > price) else None
    discount_pct = (
        round((regular - price) / regular * 100, 1)
        if was_price else None
    )

    images = p.get("images") or []
    image_url = images[0].get("src") if images else None

    in_stock = bool(p.get("is_in_stock", True))

    # Extract brand from attributes
    brand = _extract_attr(p.get("attributes") or [], "brand", "manufacturer", "vendor")

    return {
        "url": p.get("permalink") or f"{origin}/?p={p.get('id', '')}",
        "source": "woocommerce",
        "id": str(p.get("id", "")),
        "title": p.get("name") or "",
        "brand": brand,
        "description": _strip_html(p.get("short_description") or p.get("description") or ""),
        "sku": p.get("sku") or None,
        "price": price,
        "was_price": was_price,
        "currency": prices.get("currency_code") or "USD",
        "discount_pct": discount_pct,
        "in_stock": in_stock,
        "stock_status": "In Stock" if in_stock else "Out of Stock",
        "image_url": image_url,
        "rating": _safe_float(p.get("average_rating")),
        "review_count": p.get("review_count"),
    }


def _parse_rest_product(p: dict, origin: str) -> Dict:
    """Parse a WC REST API v3 product object."""
    price = _safe_float(p.get("price"))
    regular = _safe_float(p.get("regular_price"))
    was_price = regular if (regular and price and regular > price) else None
    discount_pct = (
        round((regular - price) / regular * 100, 1)
        if was_price else None
    )

    images = p.get("images") or []
    image_url = images[0].get("src") if images else None
    in_stock = (p.get("stock_status") or "instock") == "instock"

    brand = _extract_attr(p.get("attributes") or [], "brand", "manufacturer", "vendor")

    return {
        "url": p.get("permalink") or f"{origin}/?p={p.get('id', '')}",
        "source": "woocommerce",
        "id": str(p.get("id", "")),
        "title": p.get("name") or "",
        "brand": brand,
        "description": _strip_html(p.get("short_description") or p.get("description") or ""),
        "sku": p.get("sku") or None,
        "mpn": None,
        "upc_ean": None,
        "price": price,
        "was_price": was_price,
        "currency": "USD",
        "discount_pct": discount_pct,
        "in_stock": in_stock,
        "stock_status": "In Stock" if in_stock else "Out of Stock",
        "image_url": image_url,
        "rating": _safe_float(p.get("average_rating")),
        "review_count": _safe_int(p.get("rating_count")),
    }


def _parse_html_json_ld(html: str, url: str) -> Dict:
    """Extract Product structured data from JSON-LD in HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Product":
                    return _parse_json_ld_product(item, url)
        except (json.JSONDecodeError, AttributeError):
            continue

    return {"url": url, "error": "No Product JSON-LD found"}


def _parse_json_ld_product(ld: dict, url: str) -> Dict:
    """Parse a JSON-LD Product object."""
    offers = ld.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    price = _safe_float(offers.get("price"))
    in_stock = "instock" in (offers.get("availability") or "").lower()

    agg_rating = ld.get("aggregateRating") or {}
    rating = _safe_float(agg_rating.get("ratingValue"))
    review_count = _safe_int(agg_rating.get("reviewCount"))

    images = ld.get("image") or []
    if isinstance(images, str):
        images = [images]
    image_url = images[0] if images else None

    return {
        "url": url,
        "source": "woocommerce",
        "title": ld.get("name") or "",
        "brand": (ld.get("brand") or {}).get("name") if isinstance(ld.get("brand"), dict) else ld.get("brand"),
        "description": ld.get("description") or None,
        "sku": ld.get("sku") or None,
        "mpn": ld.get("mpn") or None,
        "upc_ean": ld.get("gtin13") or ld.get("gtin12") or ld.get("gtin") or None,
        "price": price,
        "was_price": None,
        "currency": offers.get("priceCurrency") or "USD",
        "discount_pct": None,
        "in_stock": in_stock,
        "stock_status": "In Stock" if in_stock else "Out of Stock",
        "image_url": image_url,
        "rating": rating,
        "review_count": review_count,
    }


# ── Utilities ──────────────────────────────────────────────────────────────────

async def _get_json(url: str) -> Optional[dict | list]:
    """GET url and return parsed JSON, or None on error / non-200."""
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
        ) as client:
            r = await client.get(url)
        if r.status_code == 200:
            return r.json()
        logger.debug("WC API %s → HTTP %s", url, r.status_code)
        return None
    except Exception as exc:
        logger.debug("WC API request failed for %s: %s", url, exc)
        return None


def _normalise_origin(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _extract_wc_product_id(url: str) -> Optional[int]:
    """Extract WooCommerce product ID from URL (e.g. ?p=123 or /product/slug/?post_id=123)."""
    m = re.search(r"[?&]p=(\d+)", url)
    if m:
        return int(m.group(1))
    # Some themes put /product/{slug}/ — we can't get the ID without an API call
    return None


def _extract_attr(attrs: list, *names: str) -> Optional[str]:
    """Extract the first value from product attributes matching any of the given names."""
    lower_names = {n.lower() for n in names}
    for attr in attrs:
        attr_name = (attr.get("name") or "").lower()
        if attr_name in lower_names:
            terms = attr.get("terms") or attr.get("options") or []
            if terms:
                item = terms[0]
                return item.get("name") if isinstance(item, dict) else str(item)
    return None


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> Optional[str]:
    if not text:
        return None
    clean = _HTML_TAG_RE.sub(" ", text).strip()
    return clean[:1000] if clean else None


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(str(value).replace(",", "").strip())
        return f if f >= 0 else None
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
