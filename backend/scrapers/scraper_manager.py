"""
Scraper Manager - Intelligent Scraper Selection

This module automatically selects the best scraper for a given URL:
- Amazon scraper for Amazon.com URLs
- Walmart scraper for Walmart.com URLs (future)
- Generic scraper for all other websites

It also handles scraping queues, retries, and error handling.
"""

from typing import Dict, Optional
from urllib.parse import urlparse
import asyncio

from scrapers.amazon_scraper import AmazonScraper
from scrapers.generic_scraper import GenericWebScraper


class ScraperManager:
    """
    Manages scraping operations and selects appropriate scraper based on URL.

    Usage:
        manager = ScraperManager()

        # Automatically uses Amazon scraper
        result = await manager.scrape("https://www.amazon.com/dp/B0BSHF7WHW")

        # Automatically uses generic scraper
        result = await manager.scrape(
            "https://competitor.com/product/123",
            price_selector=".price"
        )
    """

    def __init__(self):
        self.amazon_scraper = AmazonScraper()
        self.generic_scraper = GenericWebScraper()

        # Map domains to specialized scrapers
        self.specialized_scrapers = {
            'amazon.com': self.amazon_scraper,
            'amazon.co.uk': self.amazon_scraper,
            'amazon.ca': self.amazon_scraper,
            'amazon.de': self.amazon_scraper,
            # Add more specialized scrapers here in the future
            # 'walmart.com': WalmartScraper(),
            # 'ebay.com': EbayScraper(),
        }


    async def scrape(
        self,
        url: str,
        price_selector: Optional[str] = None,
        title_selector: Optional[str] = None,
        stock_selector: Optional[str] = None,
        image_selector: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Scrape a product URL using the appropriate scraper.

        Args:
            url: Product URL
            price_selector: CSS selector for price (optional)
            title_selector: CSS selector for title (optional)
            stock_selector: CSS selector for stock status (optional)
            image_selector: CSS selector for image (optional)
            max_retries: Number of retry attempts on failure

        Returns:
            Dictionary with scraped data
        """
        # Determine which scraper to use
        domain = self._extract_domain(url)
        scraper = self.specialized_scrapers.get(domain, self.generic_scraper)

        # Attempt scraping with retries
        for attempt in range(max_retries):
            try:
                if isinstance(scraper, AmazonScraper):
                    # Amazon scraper doesn't need CSS selectors
                    result = await scraper.scrape_product(url)
                else:
                    # Generic scraper uses CSS selectors
                    result = await scraper.scrape_product(
                        url,
                        price_selector,
                        title_selector,
                        stock_selector,
                        image_selector
                    )

                # Check for CAPTCHA or blocking
                if result.get('error') and 'CAPTCHA' in result['error']:
                    if attempt < max_retries - 1:
                        # Wait longer before retry
                        await asyncio.sleep((attempt + 1) * 5)
                        continue

                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                else:
                    return {
                        "url": url,
                        "error": f"Failed after {max_retries} attempts: {str(e)}"
                    }

        return {
            "url": url,
            "error": "Max retries exceeded"
        }


    async def search(
        self,
        query: str,
        website: str = "amazon.com",
        max_results: int = 10
    ) -> list:
        """
        Search for products on a specific website.

        Args:
            query: Search term
            website: Website to search (default: amazon.com)
            max_results: Maximum number of results

        Returns:
            List of product dictionaries
        """
        scraper = self.specialized_scrapers.get(website)

        if not scraper:
            return {"error": f"No specialized scraper for {website}. Only direct URL scraping is supported."}

        if isinstance(scraper, AmazonScraper):
            return await scraper.search_products(query, max_results)

        return {"error": "Search not implemented for this website"}


    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain
        except:
            return ""


    def get_scraper_type(self, url: str) -> str:
        """
        Get the type of scraper that would be used for a URL.

        Returns:
            "amazon", "generic", etc.
        """
        domain = self._extract_domain(url)

        if domain in self.specialized_scrapers:
            return domain.split('.')[0]  # e.g., "amazon" from "amazon.com"

        return "generic"


# Global scraper manager instance
_manager = None


def get_scraper_manager() -> ScraperManager:
    """Get or create the global scraper manager"""
    global _manager
    if _manager is None:
        _manager = ScraperManager()
    return _manager


# Convenience functions
async def scrape_url(
    url: str,
    price_selector: Optional[str] = None,
    title_selector: Optional[str] = None,
    stock_selector: Optional[str] = None,
    image_selector: Optional[str] = None
) -> Dict:
    """
    Convenience function to scrape any URL.

    Usage:
        # Amazon (automatic)
        result = await scrape_url("https://www.amazon.com/dp/B0BSHF7WHW")

        # Custom site
        result = await scrape_url(
            "https://competitor.com/product/123",
            price_selector=".price"
        )
    """
    manager = get_scraper_manager()
    return await manager.scrape(
        url,
        price_selector,
        title_selector,
        stock_selector,
        image_selector
    )


async def search_products(query: str, website: str = "amazon.com", max_results: int = 10) -> list:
    """
    Search for products on a website.

    Usage:
        results = await search_products("Sony headphones", max_results=5)
    """
    manager = get_scraper_manager()
    return await manager.search(query, website, max_results)
