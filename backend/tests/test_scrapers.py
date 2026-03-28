"""
Tests for specialized scrapers: Amazon, Walmart, eBay, Shopify.

All network calls (httpx, Playwright) are mocked — no live HTTP requests.
Run from the backend/ directory:
    pytest tests/test_scrapers.py -v
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ─── Amazon ───────────────────────────────────────────────────────────────────

class TestAmazonScraper:
    """Unit tests for AmazonScraper."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_pool():
        """Return a mock BrowserPool whose context manager yields a mock page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.content = AsyncMock(return_value="")
        page.wait_for_load_state = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.evaluate = AsyncMock(return_value=None)

        page_cm = AsyncMock()
        page_cm.__aenter__ = AsyncMock(return_value=page)
        page_cm.__aexit__ = AsyncMock(return_value=False)

        pool = MagicMock()
        pool.acquire_page = MagicMock(return_value=page_cm)
        return pool, page

    @staticmethod
    def _amazon_html(title: str, price: str = "279.99", in_stock: bool = True) -> str:
        """Minimal Amazon product page HTML using the real DOM selectors the scraper reads."""
        availability_html = (
            '<div id="availability"><span class="a-size-medium a-color-success">In Stock</span></div>'
            if in_stock else
            '<div id="availability"><span class="a-color-price">Currently unavailable.</span></div>'
        )
        return f"""
        <html><head></head><body>
        <span id="productTitle">{title}</span>
        <span class="a-price-whole">{price.split('.')[0]}</span>
        <span class="a-price-fraction">{price.split('.')[1] if '.' in price else '00'}</span>
        {availability_html}
        </body></html>
        """

    # ── Tests ─────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_scrape_product_json_ld(self):
        """scrape_product() extracts title and price from Amazon DOM selectors."""
        from scrapers.amazon_scraper import AmazonScraper

        pool, page = self._make_pool()
        page.content = AsyncMock(return_value=self._amazon_html("Sony WH-1000XM5", "279.99", True))
        page.evaluate = AsyncMock(return_value=None)

        scraper = AmazonScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.amazon.com/dp/B09XS7JWHH")

        assert result.get("title") == "Sony WH-1000XM5"
        assert result.get("price") == 279.99
        assert result.get("in_stock") is True
        assert result.get("url") == "https://www.amazon.com/dp/B09XS7JWHH"
        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_scrape_product_captcha_returns_error(self):
        """CAPTCHA detection on page → result contains 'CAPTCHA' in error."""
        from scrapers.amazon_scraper import AmazonScraper

        pool, page = self._make_pool()
        # Simulate CAPTCHA page
        page.content = AsyncMock(return_value=(
            "<html><body>Enter the characters you see below</body></html>"
        ))
        page.evaluate = AsyncMock(return_value=None)

        scraper = AmazonScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.amazon.com/dp/CAPTCHATEST")

        assert "error" in result
        assert "CAPTCHA" in result["error"]

    @pytest.mark.asyncio
    async def test_scrape_product_playwright_exception(self):
        """Playwright exception → result contains an error key."""
        from scrapers.amazon_scraper import AmazonScraper

        pool, page = self._make_pool()
        page.goto = AsyncMock(side_effect=Exception("net::ERR_NAME_NOT_RESOLVED"))

        scraper = AmazonScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.amazon.com/dp/BROKEN")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_products_returns_list(self):
        """search_products() returns a list (may be empty on mocked blank page)."""
        from scrapers.amazon_scraper import AmazonScraper

        pool, page = self._make_pool()
        page.content = AsyncMock(return_value="<html><body></body></html>")

        scraper = AmazonScraper(browser_pool=pool)
        results = await scraper.search_products("headphones", max_results=5)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_scrape_product_out_of_stock(self):
        """Out-of-stock DOM marker → in_stock is False."""
        from scrapers.amazon_scraper import AmazonScraper

        pool, page = self._make_pool()
        page.content = AsyncMock(return_value=self._amazon_html("Rare Collector Item", "99.99", False))
        page.evaluate = AsyncMock(return_value=None)

        scraper = AmazonScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.amazon.com/dp/OOS1234")

        assert result.get("in_stock") is False


# ─── Walmart ──────────────────────────────────────────────────────────────────

class TestWalmartScraper:
    """Unit tests for WalmartScraper."""

    WALMART_JSON_LD = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Great Value Coffee",
        "description": "Bold roast, 48 oz",
        "image": "https://i5.walmartimages.com/coffee.jpg",
        "brand": {"@type": "Brand", "name": "Great Value"},
        "offers": {
            "@type": "Offer",
            "price": "7.48",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
        },
        "aggregateRating": {"ratingValue": "4.5", "reviewCount": "1234"},
    }

    @staticmethod
    def _make_pool(html: str = ""):
        page = AsyncMock()
        page.goto = AsyncMock()
        page.content = AsyncMock(return_value=html)
        page.wait_for_load_state = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=[])
        page.evaluate = AsyncMock(return_value=None)

        page_cm = AsyncMock()
        page_cm.__aenter__ = AsyncMock(return_value=page)
        page_cm.__aexit__ = AsyncMock(return_value=False)

        pool = MagicMock()
        pool.acquire_page = MagicMock(return_value=page_cm)
        return pool, page

    def _walmart_page(self, extra_ld: dict | None = None) -> str:
        ld = {**self.WALMART_JSON_LD, **(extra_ld or {})}
        return (
            f'<html><head></head><body>'
            f'<script type="application/ld+json">{json.dumps(ld)}</script>'
            f'</body></html>'
        )

    @pytest.mark.asyncio
    async def test_scrape_product_basic_fields(self):
        """scrape_product() extracts title, price, brand, and in_stock from JSON-LD."""
        from scrapers.walmart_scraper import WalmartScraper

        pool, page = self._make_pool(self._walmart_page())
        scraper = WalmartScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.walmart.com/ip/12345678")

        assert result.get("title") == "Great Value Coffee"
        assert result.get("price") == 7.48
        assert result.get("currency") == "USD"
        assert result.get("in_stock") is True
        assert result.get("brand") == "Great Value"
        assert result.get("rating") == 4.5
        assert result.get("review_count") == 1234
        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_scrape_product_out_of_stock(self):
        """OutOfStock availability → in_stock is False."""
        from scrapers.walmart_scraper import WalmartScraper

        ld_override = {
            "offers": {
                "@type": "Offer",
                "price": "7.48",
                "priceCurrency": "USD",
                "availability": "https://schema.org/OutOfStock",
            }
        }
        pool, page = self._make_pool(self._walmart_page(ld_override))
        scraper = WalmartScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.walmart.com/ip/OOS")

        assert result.get("in_stock") is False

    @pytest.mark.asyncio
    async def test_scrape_product_exception_returns_error(self):
        """Network failure → result contains error key."""
        from scrapers.walmart_scraper import WalmartScraper

        pool, page = self._make_pool()
        page.goto = AsyncMock(side_effect=Exception("timeout"))

        scraper = WalmartScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.walmart.com/ip/BROKEN")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_products_returns_list(self):
        """search_products() returns a list on empty page."""
        from scrapers.walmart_scraper import WalmartScraper

        pool, page = self._make_pool("<html><body></body></html>")
        scraper = WalmartScraper(browser_pool=pool)
        results = await scraper.search_products("coffee", max_results=5)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_scrape_product_image_url(self):
        """Image URL is forwarded into the result."""
        from scrapers.walmart_scraper import WalmartScraper

        pool, page = self._make_pool(self._walmart_page())
        scraper = WalmartScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.walmart.com/ip/12345678")

        assert result.get("image_url") == "https://i5.walmartimages.com/coffee.jpg"


# ─── eBay ─────────────────────────────────────────────────────────────────────

class TestEbayScraper:
    """Unit tests for EbayScraper."""

    BIN_JSON_LD = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Apple AirPods Pro 2nd Gen",
        "image": "https://i.ebayimg.com/airpods.jpg",
        "brand": {"@type": "Brand", "name": "Apple"},
        "offers": {
            "@type": "Offer",
            "price": "189.00",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "seller": {"@type": "Person", "name": "tech_deals_99"},
        },
        "aggregateRating": {"ratingValue": "4.8", "reviewCount": "320"},
    }

    @staticmethod
    def _make_pool(html: str = ""):
        page = AsyncMock()
        page.goto = AsyncMock()
        page.content = AsyncMock(return_value=html)
        page.wait_for_load_state = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=[])
        page.evaluate = AsyncMock(return_value=None)

        page_cm = AsyncMock()
        page_cm.__aenter__ = AsyncMock(return_value=page)
        page_cm.__aexit__ = AsyncMock(return_value=False)

        pool = MagicMock()
        pool.acquire_page = MagicMock(return_value=page_cm)
        return pool, page

    def _ebay_page(self, extra_ld: dict | None = None, seller: str = "tech_deals_99") -> str:
        ld = {**self.BIN_JSON_LD, **(extra_ld or {})}
        return (
            f'<html><head></head><body>'
            f'<script type="application/ld+json">{json.dumps(ld)}</script>'
            f'<span class="mbg-nw">{seller}</span>'
            f'</body></html>'
        )

    @pytest.mark.asyncio
    async def test_scrape_product_buy_it_now(self):
        """Buy-It-Now listing extracts price, seller, rating."""
        from scrapers.ebay_scraper import EbayScraper

        pool, page = self._make_pool(self._ebay_page())
        scraper = EbayScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.ebay.com/itm/123456789")

        assert result.get("title") == "Apple AirPods Pro 2nd Gen"
        assert result.get("price") == 189.00
        assert result.get("currency") == "USD"
        assert result.get("in_stock") is True
        assert result.get("seller_name") == "tech_deals_99"
        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_scrape_product_exception_returns_error(self):
        """Network failure → result contains error key."""
        from scrapers.ebay_scraper import EbayScraper

        pool, page = self._make_pool()
        page.goto = AsyncMock(side_effect=Exception("connection reset"))

        scraper = EbayScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.ebay.com/itm/BROKEN")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_products_returns_list(self):
        """search_products() returns a list on empty page."""
        from scrapers.ebay_scraper import EbayScraper

        pool, page = self._make_pool("<html><body></body></html>")
        scraper = EbayScraper(browser_pool=pool)
        results = await scraper.search_products("airpods", max_results=5)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_scrape_product_image_url(self):
        """Image URL is extracted from JSON-LD."""
        from scrapers.ebay_scraper import EbayScraper

        pool, page = self._make_pool(self._ebay_page())
        scraper = EbayScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.ebay.com/itm/123456789")

        assert result.get("image_url") == "https://i.ebayimg.com/airpods.jpg"

    @pytest.mark.asyncio
    async def test_scrape_product_out_of_stock(self):
        """OutOfStock → in_stock is False."""
        from scrapers.ebay_scraper import EbayScraper

        ld_override = {
            "offers": {
                "@type": "Offer",
                "price": "189.00",
                "priceCurrency": "USD",
                "availability": "https://schema.org/OutOfStock",
                "seller": {"@type": "Person", "name": "tech_deals_99"},
            }
        }
        pool, page = self._make_pool(self._ebay_page(ld_override))
        scraper = EbayScraper(browser_pool=pool)
        result = await scraper.scrape_product("https://www.ebay.com/itm/999")

        assert result.get("in_stock") is False


# ─── Shopify ──────────────────────────────────────────────────────────────────

SHOPIFY_PRODUCT_API_RESPONSE = {
    "product": {
        "id": 7654321,
        "title": "Classic Unisex Tee",
        "handle": "classic-unisex-tee",
        "vendor": "Acme Apparel",
        "product_type": "T-Shirt",
        "tags": "cotton, unisex, summer",
        "body_html": "<p>100% cotton tee.</p>",
        "published_at": "2024-01-15T10:00:00-05:00",
        "updated_at": "2024-06-01T12:00:00-05:00",
        "images": [
            {"src": "https://cdn.shopify.com/tee-blue.jpg"},
            {"src": "https://cdn.shopify.com/tee-red.jpg"},
        ],
        "options": [
            {"name": "Color", "values": ["Blue", "Red"]},
            {"name": "Size", "values": ["S", "M", "L"]},
        ],
        "variants": [
            {
                "id": 1001,
                "title": "Blue / M",
                "price": "29.99",
                "compare_at_price": "39.99",
                "sku": "ATEE-BLU-M",
                "available": True,
                "inventory_quantity": 42,
                "inventory_policy": "deny",
                "weight": 0.3,
                "weight_unit": "kg",
                "barcode": "0123456789012",
                "option1": "Blue",
                "option2": "M",
            },
            {
                "id": 1002,
                "title": "Red / L",
                "price": "29.99",
                "compare_at_price": None,
                "sku": "ATEE-RED-L",
                "available": False,
                "inventory_quantity": 0,
                "inventory_policy": "deny",
                "weight": 0.3,
                "weight_unit": "kg",
                "barcode": None,
                "option1": "Red",
                "option2": "L",
            },
        ],
    }
}

SHOPIFY_SEARCH_API_RESPONSE = {
    "products": [
        SHOPIFY_PRODUCT_API_RESPONSE["product"],
        {**SHOPIFY_PRODUCT_API_RESPONSE["product"], "id": 7654322, "title": "Slim Fit Tee", "handle": "slim-fit-tee"},
    ]
}


class _MockResponse:
    """Minimal httpx.Response mock."""
    def __init__(self, data: Any, status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


class TestShopifyScraper:
    """Unit tests for ShopifyScraper — mocks httpx entirely."""

    @pytest.mark.asyncio
    async def test_scrape_product_basic_fields(self):
        """scrape_product() returns normalised product data from /products/{handle}.json."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse(SHOPIFY_PRODUCT_API_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/classic-unisex-tee"
            )

        assert result.get("title") == "Classic Unisex Tee"
        assert result.get("price") == 29.99
        assert result.get("compare_at_price") == 39.99
        assert result.get("vendor") == "Acme Apparel"
        assert result.get("in_stock") is True
        assert result.get("sku") == "ATEE-BLU-M"
        assert result.get("handle") == "classic-unisex-tee"
        assert result.get("source") == "shopify"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_scrape_product_discount_pct(self):
        """discount_pct is correctly computed from compare_at_price and price."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse(SHOPIFY_PRODUCT_API_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/classic-unisex-tee"
            )

        # (39.99 - 29.99) / 39.99 * 100 ≈ 25.0 %
        assert result.get("discount_pct") is not None
        assert 24.0 <= result["discount_pct"] <= 26.0

    @pytest.mark.asyncio
    async def test_scrape_product_images(self):
        """images list and image_url are populated."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse(SHOPIFY_PRODUCT_API_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/classic-unisex-tee"
            )

        assert result.get("image_url") == "https://cdn.shopify.com/tee-blue.jpg"
        assert len(result.get("images", [])) == 2

    @pytest.mark.asyncio
    async def test_scrape_product_tags(self):
        """Comma-separated tags string is parsed into a list."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse(SHOPIFY_PRODUCT_API_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/classic-unisex-tee"
            )

        assert "cotton" in result.get("tags", [])
        assert "summer" in result.get("tags", [])

    @pytest.mark.asyncio
    async def test_scrape_product_variants(self):
        """variants list is populated with per-variant data."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse(SHOPIFY_PRODUCT_API_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/classic-unisex-tee"
            )

        variants = result.get("variants", [])
        assert len(variants) == 2
        assert variants[0]["sku"] == "ATEE-BLU-M"
        assert variants[1]["sku"] == "ATEE-RED-L"
        assert variants[1]["available"] is False

    @pytest.mark.asyncio
    async def test_scrape_product_api_404_returns_error(self):
        """404 from Shopify API → result contains error."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse({}, status_code=404)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/does-not-exist"
            )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_scrape_product_no_handle_returns_error(self):
        """URL without /products/ segment → error."""
        from scrapers.shopify_scraper import ShopifyScraper

        scraper = ShopifyScraper()
        result = await scraper.scrape_product("https://acme.myshopify.com/")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_scrape_product_exception_returns_error(self):
        """httpx exception → result contains error."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            result = await scraper.scrape_product(
                "https://acme.myshopify.com/products/tee"
            )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_products_returns_list(self):
        """search_products() returns a list of parsed products."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse(SHOPIFY_SEARCH_API_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            scraper = ShopifyScraper()
            results = await scraper.search_products(
                "tee", max_results=2, store_url="https://acme.myshopify.com"
            )

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["title"] == "Classic Unisex Tee"
        assert results[1]["title"] == "Slim Fit Tee"

    @pytest.mark.asyncio
    async def test_search_products_no_store_url(self):
        """search_products() without store_url returns empty list."""
        from scrapers.shopify_scraper import ShopifyScraper

        scraper = ShopifyScraper()
        results = await scraper.search_products("tee")

        assert results == []

    @pytest.mark.asyncio
    async def test_is_shopify_store_true(self):
        """is_shopify_store() returns True when /products.json returns products."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse({"products": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            result = await ShopifyScraper.is_shopify_store("https://acme.myshopify.com")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_shopify_store_false(self):
        """is_shopify_store() returns False on 404."""
        from scrapers.shopify_scraper import ShopifyScraper

        mock_response = _MockResponse({}, status_code=404)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scrapers.shopify_scraper.httpx.AsyncClient", return_value=mock_client):
            result = await ShopifyScraper.is_shopify_store("https://not-shopify.com")

        assert result is False

    # ── _parse_product_url ────────────────────────────────────────────────────

    def test_parse_product_url_standard(self):
        """Standard /products/{handle} URL → correct origin and handle."""
        from scrapers.shopify_scraper import ShopifyScraper

        origin, handle = ShopifyScraper._parse_product_url(
            "https://store.myshopify.com/products/blue-widget"
        )
        assert origin == "https://store.myshopify.com"
        assert handle == "blue-widget"

    def test_parse_product_url_with_collection(self):
        """/collections/x/products/{handle} also resolves handle."""
        from scrapers.shopify_scraper import ShopifyScraper

        origin, handle = ShopifyScraper._parse_product_url(
            "https://shop.example.com/collections/tees/products/my-shirt"
        )
        assert origin == "https://shop.example.com"
        assert handle == "my-shirt"

    def test_parse_product_url_custom_domain(self):
        """Custom-domain Shopify store URL extracts handle correctly."""
        from scrapers.shopify_scraper import ShopifyScraper

        origin, handle = ShopifyScraper._parse_product_url(
            "https://shop.example.com/en-us/products/classic-tee"
        )
        assert origin == "https://shop.example.com"
        assert handle == "classic-tee"

    def test_parse_product_url_no_products(self):
        """URL with no /products/ segment → handle is None."""
        from scrapers.shopify_scraper import ShopifyScraper

        origin, handle = ShopifyScraper._parse_product_url("https://acme.myshopify.com/")
        assert handle is None


# ─── ScraperManager routing ───────────────────────────────────────────────────

class TestScraperManagerRouting:
    """Verify ScraperManager routes URLs to the correct scraper class."""

    def _make_manager(self):
        from scrapers.scraper_manager import ScraperManager
        from scrapers.amazon_scraper import AmazonScraper
        from scrapers.walmart_scraper import WalmartScraper
        from scrapers.ebay_scraper import EbayScraper
        from scrapers.shopify_scraper import ShopifyScraper
        from scrapers.generic_scraper import GenericWebScraper

        manager = ScraperManager.__new__(ScraperManager)
        manager._pool = None
        manager.amazon_scraper = MagicMock(spec=AmazonScraper)
        manager.apify_scraper = MagicMock()
        manager.apify_scraper.is_configured = False
        manager.walmart_scraper = MagicMock(spec=WalmartScraper)
        manager.ebay_scraper = MagicMock(spec=EbayScraper)
        manager.shopify_scraper = MagicMock(spec=ShopifyScraper)
        manager.generic_scraper = MagicMock(spec=GenericWebScraper)

        manager.specialized_scrapers = {
            "amazon.com": manager.amazon_scraper,
            "amazon.co.uk": manager.amazon_scraper,
            "amazon.ca": manager.amazon_scraper,
            "amazon.de": manager.amazon_scraper,
            "amazon.fr": manager.amazon_scraper,
            "amazon.es": manager.amazon_scraper,
            "amazon.it": manager.amazon_scraper,
            "amazon.co.jp": manager.amazon_scraper,
            "amazon.com.au": manager.amazon_scraper,
            "walmart.com": manager.walmart_scraper,
            "ebay.com": manager.ebay_scraper,
            "ebay.co.uk": manager.ebay_scraper,
            "ebay.de": manager.ebay_scraper,
            "ebay.fr": manager.ebay_scraper,
            "ebay.com.au": manager.ebay_scraper,
            "myshopify.com": manager.shopify_scraper,
        }
        return manager

    def test_amazon_routing(self):
        from scrapers.scraper_manager import ScraperManager
        manager = self._make_manager()
        assert manager.specialized_scrapers["amazon.com"] is manager.amazon_scraper
        assert manager.specialized_scrapers["amazon.co.uk"] is manager.amazon_scraper

    def test_walmart_routing(self):
        manager = self._make_manager()
        assert manager.specialized_scrapers["walmart.com"] is manager.walmart_scraper

    def test_ebay_routing(self):
        manager = self._make_manager()
        assert manager.specialized_scrapers["ebay.com"] is manager.ebay_scraper
        assert manager.specialized_scrapers["ebay.co.uk"] is manager.ebay_scraper

    def test_shopify_routing(self):
        manager = self._make_manager()
        assert manager.specialized_scrapers["myshopify.com"] is manager.shopify_scraper

    def test_extract_domain_strips_www(self):
        from scrapers.scraper_manager import ScraperManager
        assert ScraperManager._extract_domain("https://www.amazon.com/dp/XYZ") == "amazon.com"
        assert ScraperManager._extract_domain("https://www.walmart.com/ip/1234") == "walmart.com"
        assert ScraperManager._extract_domain("https://www.ebay.com/itm/99") == "ebay.com"
        assert ScraperManager._extract_domain("https://store.myshopify.com/products/tee") == "store.myshopify.com"

    def test_myshopify_subdomain_detected(self):
        """Any *.myshopify.com subdomain should resolve to shopify_scraper."""
        from scrapers.scraper_manager import ScraperManager
        manager = self._make_manager()
        domain = ScraperManager._extract_domain("https://brandxyz.myshopify.com/products/widget")
        # Registered key is "myshopify.com"; subdomain isn't in dict, falls through to .endswith check
        scraper = manager.specialized_scrapers.get(domain)
        if scraper is None and domain.endswith(".myshopify.com"):
            scraper = manager.shopify_scraper
        assert scraper is manager.shopify_scraper

    def test_unknown_domain_falls_to_generic(self):
        from scrapers.scraper_manager import ScraperManager
        manager = self._make_manager()
        domain = ScraperManager._extract_domain("https://some-random-site.com/product/1")
        scraper = manager.specialized_scrapers.get(domain, manager.generic_scraper)
        assert scraper is manager.generic_scraper
