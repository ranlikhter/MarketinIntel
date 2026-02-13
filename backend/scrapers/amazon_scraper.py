"""
Amazon-Specific Web Scraper

This scraper is optimized for Amazon.com with:
- Anti-bot detection evasion
- Multiple fallback selectors for Amazon's various layouts
- CAPTCHA detection
- Product search functionality
- Best practices for scraping Amazon without getting blocked

Amazon is one of the most challenging sites to scrape due to aggressive bot detection.
"""

import asyncio
import re
from typing import Dict, Optional, List
from urllib.parse import urljoin, quote_plus
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import random
import time


class AmazonScraper:
    """
    Specialized scraper for Amazon.com with anti-detection measures.

    Usage:
        scraper = AmazonScraper()

        # Search for products
        results = await scraper.search_products("Sony WH-1000XM5")

        # Scrape specific product page
        data = await scraper.scrape_product("https://www.amazon.com/dp/B0BSHF7WHW")
    """

    def __init__(self, domain: str = "amazon.com"):
        self.domain = domain
        self.base_url = f"https://www.{domain}"

        # User agents that work well with Amazon
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]


    async def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search Amazon for products and return top results.

        Args:
            query: Search term (e.g., "Sony headphones")
            max_results: Maximum number of results to return

        Returns:
            List of dictionaries with product data:
            [{
                "title": str,
                "asin": str,  # Amazon Standard Identification Number
                "price": float,
                "currency": str,
                "url": str,
                "image_url": str,
                "rating": float,
                "review_count": int
            }]
        """
        search_url = f"{self.base_url}/s?k={quote_plus(query)}"
        results = []

        try:
            async with async_playwright() as p:
                browser = await self._launch_browser(p)
                page = await browser.new_page()

                # Navigate to search results
                await self._navigate_safely(page, search_url)

                # Check for CAPTCHA
                if await self._detect_captcha(page):
                    await browser.close()
                    return {"error": "CAPTCHA detected - Amazon is blocking automated access"}

                # Wait for search results to load
                await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)

                # Extract product data
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Find product cards
                product_cards = soup.select('[data-component-type="s-search-result"]')[:max_results]

                for card in product_cards:
                    product_data = self._extract_search_result(card)
                    if product_data:
                        results.append(product_data)

                await browser.close()

        except Exception as e:
            return {"error": str(e)}

        return results


    async def scrape_product(self, url: str) -> Dict:
        """
        Scrape detailed data from an Amazon product page.

        Args:
            url: Full Amazon product URL

        Returns:
            Dictionary with product data
        """
        result = {
            "url": url,
            "title": None,
            "asin": None,
            "price": None,
            "currency": "USD",
            "in_stock": True,
            "image_url": None,
            "rating": None,
            "review_count": None,
            "brand": None,
            "description": None,
            "error": None
        }

        try:
            async with async_playwright() as p:
                browser = await self._launch_browser(p)
                page = await browser.new_page()

                # Navigate to product page
                await self._navigate_safely(page, url)

                # Check for CAPTCHA
                if await self._detect_captcha(page):
                    result["error"] = "CAPTCHA detected"
                    await browser.close()
                    return result

                # Extract ASIN from URL
                asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
                if asin_match:
                    result["asin"] = asin_match.group(1)

                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Extract data using multiple selectors (Amazon has different layouts)
                result["title"] = self._extract_title(soup)
                result["price"], result["currency"] = self._extract_price(soup)
                result["in_stock"] = self._extract_stock_status(soup)
                result["image_url"] = self._extract_image(soup, url)
                result["rating"], result["review_count"] = self._extract_reviews(soup)
                result["brand"] = self._extract_brand(soup)
                result["description"] = self._extract_description(soup)

                await browser.close()

        except Exception as e:
            result["error"] = str(e)

        return result


    async def _launch_browser(self, playwright):
        """Launch browser with anti-detection settings"""
        return await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )


    async def _navigate_safely(self, page, url):
        """Navigate with human-like behavior to avoid detection"""
        # Set random user agent
        user_agent = random.choice(self.user_agents)
        await page.set_extra_http_headers({
            'User-Agent': user_agent,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Add random delay before navigation
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Navigate
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # Random scroll (looks more human)
        await page.evaluate('window.scrollBy(0, Math.random() * 500)')
        await asyncio.sleep(random.uniform(0.5, 1.5))


    async def _detect_captcha(self, page) -> bool:
        """Check if Amazon is showing a CAPTCHA"""
        content = await page.content()
        captcha_indicators = [
            'Enter the characters you see below',
            'Type the characters you see in this image',
            'api-services-support@amazon.com',
            'Sorry, we just need to make sure you\'re not a robot'
        ]

        for indicator in captcha_indicators:
            if indicator.lower() in content.lower():
                return True
        return False


    def _extract_search_result(self, card) -> Optional[Dict]:
        """Extract data from a search result card"""
        try:
            # ASIN
            asin = card.get('data-asin')
            if not asin:
                return None

            # Title
            title_elem = card.select_one('h2 a span')
            title = title_elem.text.strip() if title_elem else None

            # URL
            url_elem = card.select_one('h2 a')
            url = urljoin(self.base_url, url_elem['href']) if url_elem else None

            # Price
            price_whole = card.select_one('.a-price-whole')
            price_fraction = card.select_one('.a-price-fraction')
            price = None
            if price_whole:
                price_text = price_whole.text.strip().replace(',', '')
                if price_fraction:
                    price_text += '.' + price_fraction.text.strip()
                try:
                    price = float(price_text)
                except:
                    pass

            # Image
            image_elem = card.select_one('img.s-image')
            image_url = image_elem['src'] if image_elem else None

            # Rating
            rating_elem = card.select_one('.a-icon-star-small span.a-icon-alt')
            rating = None
            if rating_elem:
                rating_match = re.search(r'(\d+\.?\d*)', rating_elem.text)
                if rating_match:
                    rating = float(rating_match.group(1))

            # Review count
            review_elem = card.select_one('[aria-label*="stars"]')
            review_count = None
            if review_elem:
                review_match = re.search(r'([\d,]+)', review_elem.get('aria-label', ''))
                if review_match:
                    review_count = int(review_match.group(1).replace(',', ''))

            return {
                "title": title,
                "asin": asin,
                "price": price,
                "currency": "USD",
                "url": url,
                "image_url": image_url,
                "rating": rating,
                "review_count": review_count
            }

        except Exception as e:
            return None


    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title with multiple fallbacks"""
        selectors = [
            '#productTitle',
            '#title',
            'span#productTitle',
            'h1.a-size-large'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.text.strip()
        return None


    def _extract_price(self, soup: BeautifulSoup) -> tuple[Optional[float], str]:
        """Extract price with multiple fallbacks"""
        # Try whole + fraction
        price_whole = soup.select_one('.a-price-whole')
        price_fraction = soup.select_one('.a-price-fraction')

        if price_whole:
            price_text = price_whole.text.strip().replace(',', '').replace('.', '')
            if price_fraction:
                price_text += '.' + price_fraction.text.strip()
            try:
                return float(price_text), "USD"
            except:
                pass

        # Try other selectors
        price_selectors = [
            '.a-price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '.a-color-price'
        ]

        for selector in price_selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.text.strip().replace('$', '').replace(',', '')
                try:
                    return float(price_text), "USD"
                except:
                    pass

        return None, "USD"


    def _extract_stock_status(self, soup: BeautifulSoup) -> bool:
        """Determine if product is in stock"""
        # Out of stock indicators
        out_of_stock_selectors = [
            '#availability .a-color-price',
            '#availability .a-color-state',
            '.a-color-price'
        ]

        for selector in out_of_stock_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.text.lower()
                if any(word in text for word in ['unavailable', 'out of stock', 'currently unavailable']):
                    return False

        # In stock indicator
        availability = soup.select_one('#availability span')
        if availability:
            text = availability.text.lower()
            if 'in stock' in text:
                return True

        # Default to in stock if no clear indication
        return True


    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract main product image"""
        # Try main image container
        img = soup.select_one('#landingImage')
        if not img:
            img = soup.select_one('#imgBlkFront')
        if not img:
            img = soup.select_one('.a-dynamic-image')

        if img:
            # Get the highest resolution image URL
            data_old = img.get('data-old-hires')
            if data_old:
                return data_old

            src = img.get('src')
            if src:
                return src

        return None


    def _extract_reviews(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[int]]:
        """Extract rating and review count"""
        rating = None
        review_count = None

        # Rating
        rating_elem = soup.select_one('#acrPopover')
        if rating_elem:
            rating_text = rating_elem.get('title', '')
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                rating = float(rating_match.group(1))

        # Review count
        review_elem = soup.select_one('#acrCustomerReviewText')
        if review_elem:
            review_text = review_elem.text
            review_match = re.search(r'([\d,]+)', review_text)
            if review_match:
                review_count = int(review_match.group(1).replace(',', ''))

        return rating, review_count


    def _extract_brand(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product brand"""
        # Try brand link
        brand_elem = soup.select_one('#bylineInfo')
        if brand_elem:
            brand_text = brand_elem.text.strip()
            # Remove "Visit the X Store" or "Brand: X"
            brand_text = re.sub(r'Visit the |Store| Brand:', '', brand_text).strip()
            return brand_text

        return None


    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product description (first 500 chars)"""
        # Try feature bullets
        features = soup.select('#feature-bullets ul li span.a-list-item')
        if features:
            description = ' '.join([f.text.strip() for f in features[:3]])
            return description[:500]

        # Try product description
        desc_elem = soup.select_one('#productDescription')
        if desc_elem:
            return desc_elem.text.strip()[:500]

        return None


# Convenience functions
async def search_amazon(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search Amazon for products.

    Usage:
        results = await search_amazon("Sony headphones", max_results=5)
    """
    scraper = AmazonScraper()
    return await scraper.search_products(query, max_results)


async def scrape_amazon_product(url: str) -> Dict:
    """
    Scrape an Amazon product page.

    Usage:
        data = await scrape_amazon_product("https://www.amazon.com/dp/B0BSHF7WHW")
    """
    scraper = AmazonScraper()
    return await scraper.scrape_product(url)
