"""
Shopify Scraper

Uses Shopify's deterministic JSON API endpoints:
  - /products/{handle}.json   → single product
  - /products.json?q=...      → search

Detection: a store is Shopify if it responds to /products.json.
No HTML parsing needed — the API always returns clean structured data.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlencode

import httpx

logger = logging.getLogger(__name__)

# Timeout for all Shopify API requests
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class ShopifyScraper:
    """
    Scraper for Shopify-powered stores.

    Works against any myshopify.com subdomain or custom domain running Shopify
    by querying the public Storefront JSON API (no API key required).
    """

    def __init__(self, browser_pool=None):
        # browser_pool accepted for API-compatibility with other scrapers;
        # Shopify's JSON API doesn't require a browser.
        self._pool = browser_pool

    # ── Public interface ──────────────────────────────────────────────────────

    async def scrape_product(self, url: str) -> Dict:
        """
        Scrape a single Shopify product page.

        Strategy:
        1. Extract the store origin + product handle from the URL.
        2. Fetch /{origin}/products/{handle}.json
        3. Parse the rich product object returned by the API.
        """
        try:
            origin, handle = self._parse_product_url(url)
            if not handle:
                return {"url": url, "error": "Could not extract product handle from URL"}

            api_url = f"{origin}/products/{handle}.json"
            data = await self._get_json(api_url)
            if data is None:
                return {"url": url, "error": "Shopify product API returned no data"}

            product = data.get("product") or data
            return self._parse_product(product, url)

        except Exception as exc:
            logger.exception("ShopifyScraper.scrape_product failed for %s", url)
            return {"url": url, "error": str(exc)}

    async def search_products(self, query: str, max_results: int = 10, store_url: str = "") -> List[Dict]:
        """
        Search products on a Shopify store.

        Requires a store_url (e.g. "https://shop.example.com") since Shopify
        search is per-store, not cross-store.
        """
        if not store_url:
            logger.warning("ShopifyScraper.search_products: store_url is required")
            return []

        try:
            origin = self._normalise_origin(store_url)
            params = urlencode({"q": query, "limit": min(max_results, 250)})
            api_url = f"{origin}/products.json?{params}"
            data = await self._get_json(api_url)
            if data is None:
                return []

            products = data.get("products", [])
            results = []
            for p in products[:max_results]:
                parsed = self._parse_product(p, f"{origin}/products/{p.get('handle', '')}")
                results.append(parsed)
            return results

        except Exception as exc:
            logger.exception("ShopifyScraper.search_products failed")
            return [{"error": str(exc)}]

    @staticmethod
    async def is_shopify_store(store_url: str) -> bool:
        """
        Probe whether a URL belongs to a Shopify store.

        Returns True if /products.json responds with HTTP 200 and a
        {"products": [...]} body.
        """
        try:
            origin = ShopifyScraper._normalise_origin(store_url)
            async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
                r = await client.get(f"{origin}/products.json?limit=1")
            return r.status_code == 200 and "products" in r.json()
        except Exception:
            return False

    # ── Parsing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_product(product: dict, url: str) -> Dict:
        """Convert a raw Shopify product object to our normalised schema."""
        if not product:
            return {"url": url, "error": "Empty product data"}

        # ── Variants ─────────────────────────────────────────────────────────
        variants: List[dict] = product.get("variants") or []
        first_variant: dict = variants[0] if variants else {}

        # Price (Shopify returns strings like "29.99")
        price_str = first_variant.get("price") or product.get("price") or ""
        compare_price_str = first_variant.get("compare_at_price") or ""

        price = _parse_price(price_str)
        compare_price = _parse_price(compare_price_str)

        discount_pct: Optional[float] = None
        if compare_price and price and compare_price > price:
            discount_pct = round((compare_price - price) / compare_price * 100, 1)

        # ── Stock ─────────────────────────────────────────────────────────────
        inventory_policy = first_variant.get("inventory_policy", "")
        inventory_qty = first_variant.get("inventory_quantity")
        in_stock: Optional[bool] = None
        if inventory_qty is not None:
            in_stock = inventory_qty > 0 or inventory_policy == "continue"
        elif first_variant.get("available") is not None:
            in_stock = bool(first_variant["available"])

        # ── Images ───────────────────────────────────────────────────────────
        images: List[dict] = product.get("images") or []
        image_urls = [img["src"] for img in images if img.get("src")]

        # ── Options / Variants summary ────────────────────────────────────────
        options: List[dict] = product.get("options") or []
        option_names = [o.get("name") for o in options if o.get("name")]

        variant_summary: List[Dict] = []
        for v in variants:
            vs: Dict = {
                "id": v.get("id"),
                "title": v.get("title"),
                "price": _parse_price(v.get("price") or ""),
                "compare_at_price": _parse_price(v.get("compare_at_price") or ""),
                "sku": v.get("sku") or None,
                "available": v.get("available"),
                "inventory_quantity": v.get("inventory_quantity"),
                "weight": v.get("weight"),
                "weight_unit": v.get("weight_unit"),
                "barcode": v.get("barcode") or None,
            }
            # Option values
            for i, name in enumerate(option_names, start=1):
                val = v.get(f"option{i}")
                if val:
                    vs[name.lower()] = val
            variant_summary.append(vs)

        # ── Tags / Collections ────────────────────────────────────────────────
        tags_raw = product.get("tags") or ""
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if isinstance(tags_raw, str) else list(tags_raw)

        # Normalise stock status string (matches pipeline expectations)
        stock_status = "In Stock" if in_stock else ("Out of Stock" if in_stock is False else "Unknown")

        # Strip HTML from body_html description
        import re as _re
        raw_desc = product.get("body_html") or ""
        description = _re.sub(r"<[^>]+>", " ", raw_desc).strip()[:1000] or None

        return {
            "url": url,
            "source": "shopify",
            # Core identity — matches scraping-pipeline field names
            "id": str(product.get("id") or ""),
            "handle": product.get("handle") or "",
            "title": product.get("title") or "",
            "brand": product.get("vendor") or None,   # Shopify "vendor" = brand
            "vendor": product.get("vendor") or None,
            "product_type": product.get("product_type") or None,
            "tags": tags,
            # Pricing
            "price": price,
            "was_price": compare_price,               # was_price = compare_at_price
            "compare_at_price": compare_price,
            "currency": None,
            "discount_pct": discount_pct,
            # Stock
            "in_stock": in_stock,
            "stock_status": stock_status,
            "inventory_quantity": inventory_qty,
            "inventory_policy": inventory_policy or None,
            # Description
            "description": description,
            # Media
            "image_url": image_urls[0] if image_urls else None,
            "images": image_urls,
            # Variants / Options
            "variants": variant_summary,
            "options": option_names,
            "total_variants": len(variants),
            # SKU / barcode / identifiers from first variant
            "sku": first_variant.get("sku") or None,
            "barcode": first_variant.get("barcode") or None,
            "upc_ean": first_variant.get("barcode") or None,  # barcode = UPC/EAN on Shopify
            "mpn": None,
            # Weight
            "weight": first_variant.get("weight"),
            "weight_unit": first_variant.get("weight_unit") or None,
            # Published status
            "published_at": product.get("published_at") or None,
            "updated_at": product.get("updated_at") or None,
            "_raw_variant_count": len(variants),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_product_url(url: str):
        """
        Return (origin, handle) from a Shopify product URL.

        Handles patterns:
          https://store.myshopify.com/products/blue-widget
          https://shop.example.com/en-us/products/blue-widget
          https://shop.example.com/collections/tees/products/my-shirt
        """
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        path_parts = [p for p in parsed.path.split("/") if p]

        handle: Optional[str] = None
        for i, part in enumerate(path_parts):
            if part == "products" and i + 1 < len(path_parts):
                handle = path_parts[i + 1]
                break

        return origin, handle

    @staticmethod
    def _normalise_origin(url: str) -> str:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    async def _get_json(url: str) -> Optional[dict]:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
        if r.status_code == 200:
            return r.json()
        logger.warning("Shopify API %s → HTTP %s", url, r.status_code)
        return None


# ── Utility ───────────────────────────────────────────────────────────────────

def _parse_price(value) -> Optional[float]:
    """Parse a Shopify price string like '29.99' or None/'' into float."""
    if value is None:
        return None
    try:
        f = float(str(value).replace(",", "").strip())
        return f if f >= 0 else None
    except (ValueError, TypeError):
        return None
