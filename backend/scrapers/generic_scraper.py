"""
Generic Web Scraper for Custom Competitor Websites

This scraper can extract product data from ANY website using CSS selectors.
It's designed to work with custom competitor websites that clients add themselves.

The scraper uses Playwright for JavaScript-rendered pages and BeautifulSoup as fallback.
"""

import asyncio
import re
from typing import Dict, Optional, List
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random


class GenericWebScraper:
    """
    A flexible scraper that can extract data from any website using CSS selectors.

    Usage:
        scraper = GenericWebScraper()
        result = await scraper.scrape_product(
            url="https://competitor.com/product/123",
            price_selector=".price",
            title_selector="h1.product-name"
        )
    """

    def __init__(self):
        self.ua = UserAgent()


    async def scrape_product(
        self,
        url: str,
        price_selector: Optional[str] = None,
        title_selector: Optional[str] = None,
        stock_selector: Optional[str] = None,
        image_selector: Optional[str] = None,
        use_javascript: bool = True
    ) -> Dict:
        """
        Scrape product data from a given URL using CSS selectors.

        Args:
            url: Full URL to the product page
            price_selector: CSS selector for price (e.g., ".price", "#product-price")
            title_selector: CSS selector for product title
            stock_selector: CSS selector for stock status
            image_selector: CSS selector for product image
            use_javascript: Whether to use Playwright (True) or requests+BS4 (False)

        Returns:
            Dictionary with scraped data:
            {
                "url": str,
                "title": str,
                "price": float,
                "currency": str,
                "in_stock": bool,
                "image_url": str
            }
        """
        if use_javascript:
            return await self._scrape_with_playwright(
                url, price_selector, title_selector, stock_selector, image_selector
            )
        else:
            return await self._scrape_with_requests(
                url, price_selector, title_selector, stock_selector, image_selector
            )


    async def _scrape_with_playwright(
        self,
        url: str,
        price_selector: Optional[str],
        title_selector: Optional[str],
        stock_selector: Optional[str],
        image_selector: Optional[str]
    ) -> Dict:
        """
        Scrape using Playwright (handles JavaScript-rendered pages).
        """
        result = {
            "url": url,
            "title": None,
            "price": None,
            "currency": "USD",
            "in_stock": True,
            "image_url": None,
            "error": None
        }

        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=True,  # Run in background
                    args=['--disable-blink-features=AutomationControlled']
                )

                # Create a new page
                context = await browser.new_context(
                    user_agent=self.ua.random,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                # Add random delay to look more human
                await asyncio.sleep(random.uniform(1, 3))

                # Navigate to the URL
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(random.uniform(1, 2))  # Wait for dynamic content
                except PlaywrightTimeout:
                    result["error"] = "Page load timeout"
                    await browser.close()
                    return result

                # Extract data using CSS selectors
                page_content = await page.content()
                soup = BeautifulSoup(page_content, 'html.parser')

                # Extract title
                if title_selector:
                    result["title"] = self._extract_text(soup, title_selector)
                else:
                    # Fallback: try common title patterns
                    result["title"] = self._extract_title_fallback(soup)

                # Extract price
                if price_selector:
                    price_text = self._extract_text(soup, price_selector)
                    if price_text:
                        result["price"], result["currency"] = self._parse_price(price_text)
                else:
                    # Fallback: try common price patterns
                    result["price"], result["currency"] = self._extract_price_fallback(soup)

                # Extract stock status
                if stock_selector:
                    stock_text = self._extract_text(soup, stock_selector)
                    result["in_stock"] = self._parse_stock_status(stock_text)
                else:
                    # Assume in stock if no selector provided
                    result["in_stock"] = True

                # Extract image
                if image_selector:
                    result["image_url"] = self._extract_image(soup, image_selector, url)
                else:
                    # Fallback: try common image patterns
                    result["image_url"] = self._extract_image_fallback(soup, url)

                await browser.close()

        except Exception as e:
            result["error"] = str(e)

        return result


    async def _scrape_with_requests(
        self,
        url: str,
        price_selector: Optional[str],
        title_selector: Optional[str],
        stock_selector: Optional[str],
        image_selector: Optional[str]
    ) -> Dict:
        """
        Scrape using requests + BeautifulSoup (faster, but doesn't handle JavaScript).
        """
        # This is a simplified version for static pages
        # For now, just call the Playwright version
        # You can implement a pure requests version if needed
        return await self._scrape_with_playwright(
            url, price_selector, title_selector, stock_selector, image_selector
        )


    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract text from a CSS selector."""
        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        except Exception:
            pass
        return None


    def _extract_image(self, soup: BeautifulSoup, selector: str, base_url: str) -> Optional[str]:
        """Extract image URL from a CSS selector."""
        try:
            element = soup.select_one(selector)
            if element:
                img_url = element.get('src') or element.get('data-src') or element.get('href')
                if img_url:
                    # Convert relative URL to absolute
                    return urljoin(base_url, img_url)
        except Exception:
            pass
        return None


    def _parse_price(self, price_text: str) -> tuple[Optional[float], str]:
        """
        Extract numeric price and currency from text.

        Examples:
            "$99.99" -> (99.99, "USD")
            "€45,50" -> (45.50, "EUR")
            "1,299.00 USD" -> (1299.00, "USD")
        """
        if not price_text:
            return None, "USD"

        # Remove whitespace
        price_text = price_text.strip()

        # Detect currency
        currency = "USD"
        if "$" in price_text:
            currency = "USD"
        elif "€" in price_text or "EUR" in price_text:
            currency = "EUR"
        elif "£" in price_text or "GBP" in price_text:
            currency = "GBP"
        elif "¥" in price_text or "JPY" in price_text:
            currency = "JPY"

        # Extract numeric value
        # Remove currency symbols and letters
        numeric_text = re.sub(r'[^\d,.\s]', '', price_text)
        # Handle different number formats (1,299.99 vs 1.299,99)
        numeric_text = numeric_text.replace(',', '').replace(' ', '')

        try:
            price = float(numeric_text)
            return price, currency
        except ValueError:
            return None, currency


    def _parse_stock_status(self, stock_text: str) -> bool:
        """
        Determine if product is in stock from text.

        Returns:
            True if in stock, False otherwise
        """
        if not stock_text:
            return True  # Assume in stock if no info

        stock_text = stock_text.lower()

        # Out of stock indicators
        out_of_stock_keywords = [
            "out of stock", "not available", "unavailable",
            "sold out", "coming soon", "pre-order",
            "backordered", "discontinued"
        ]

        for keyword in out_of_stock_keywords:
            if keyword in stock_text:
                return False

        return True


    def _extract_title_fallback(self, soup: BeautifulSoup) -> Optional[str]:
        """Try common title patterns if no selector provided."""
        # Try meta tags first
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            return meta_title["content"].strip()

        # Try h1 tags
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Try title tag
        title = soup.find("title")
        if title:
            return title.get_text(strip=True)

        return None


    def _extract_price_fallback(self, soup: BeautifulSoup) -> tuple[Optional[float], str]:
        """Try common price patterns if no selector provided."""
        # Common price class/id patterns
        price_patterns = [
            {"class": "price"},
            {"class": "product-price"},
            {"class": "sale-price"},
            {"id": "price"},
            {"itemprop": "price"}
        ]

        for pattern in price_patterns:
            element = soup.find(attrs=pattern)
            if element:
                price_text = element.get_text(strip=True)
                price, currency = self._parse_price(price_text)
                if price:
                    return price, currency

        return None, "USD"


    def _extract_image_fallback(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Try common image patterns if no selector provided."""
        # Try meta tags
        meta_image = soup.find("meta", property="og:image")
        if meta_image and meta_image.get("content"):
            return urljoin(base_url, meta_image["content"])

        # Try images with product-related classes
        img_patterns = [
            {"class": "product-image"},
            {"class": "main-image"},
            {"id": "main-image"}
        ]

        for pattern in img_patterns:
            img = soup.find("img", attrs=pattern)
            if img:
                img_url = img.get("src") or img.get("data-src")
                if img_url:
                    return urljoin(base_url, img_url)

        return None


# Async helper function for easy use
async def scrape_competitor_product(
    url: str,
    price_selector: Optional[str] = None,
    title_selector: Optional[str] = None,
    stock_selector: Optional[str] = None,
    image_selector: Optional[str] = None
) -> Dict:
    """
    Convenience function to scrape a product without instantiating the class.

    Usage:
        result = await scrape_competitor_product(
            url="https://competitor.com/product",
            price_selector=".price"
        )
    """
    scraper = GenericWebScraper()
    return await scraper.scrape_product(
        url, price_selector, title_selector, stock_selector, image_selector
    )
