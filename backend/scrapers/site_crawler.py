"""
Intelligent Full-Site Crawler
Automatically discovers and scrapes all products from competitor websites
"""

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import asyncio
import logging
from typing import List, Dict, Set, Optional
import re

logger = logging.getLogger(__name__)


class SiteCrawler:
    """Intelligent crawler that discovers and scrapes entire competitor websites"""

    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.product_urls: Set[str] = set()
        self.category_urls: Set[str] = set()
        self.max_depth = 3
        self.max_pages = 500
        self.delay = 2  # seconds between requests

    async def crawl_site(
        self,
        base_url: str,
        max_products: int = 100,
        max_depth: int = 3,
        category_only: bool = False
    ) -> Dict:
        """
        Crawl entire site and discover all products

        Args:
            base_url: Starting URL (e.g., https://competitor.com)
            max_products: Maximum products to discover
            max_depth: Maximum crawl depth
            category_only: Only discover categories, don't scrape products

        Returns:
            Dict with discovered URLs and products
        """
        self.max_depth = max_depth
        self.visited_urls.clear()
        self.product_urls.clear()
        self.category_urls.clear()

        logger.info(f"Starting site crawl for: {base_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                # Start crawling from base URL
                await self._crawl_recursive(page, base_url, base_url, depth=0)

                logger.info(f"Crawl complete. Found {len(self.product_urls)} products, {len(self.category_urls)} categories")

                # Extract products if requested
                products = []
                if not category_only and self.product_urls:
                    products = await self._extract_products(
                        page,
                        list(self.product_urls)[:max_products]
                    )

                return {
                    'success': True,
                    'base_url': base_url,
                    'categories_found': len(self.category_urls),
                    'products_found': len(self.product_urls),
                    'products_scraped': len(products),
                    'category_urls': list(self.category_urls),
                    'product_urls': list(self.product_urls)[:max_products],
                    'products': products
                }

            except Exception as e:
                logger.error(f"Site crawl failed: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'categories_found': len(self.category_urls),
                    'products_found': len(self.product_urls)
                }
            finally:
                await browser.close()

    async def _crawl_recursive(
        self,
        page,
        url: str,
        base_url: str,
        depth: int
    ):
        """Recursively crawl pages and discover products/categories"""

        # Stop conditions
        if depth > self.max_depth:
            return
        if len(self.visited_urls) >= self.max_pages:
            return
        if url in self.visited_urls:
            return

        # Only crawl same domain
        if not self._is_same_domain(url, base_url):
            return

        # Skip common non-product pages
        if self._should_skip_url(url):
            return

        self.visited_urls.add(url)
        logger.info(f"Crawling [{depth}]: {url}")

        try:
            # Load page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(self.delay)

            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Detect page type
            page_type = self._detect_page_type(soup, url)

            if page_type == 'product':
                self.product_urls.add(url)
                logger.info(f"  → Product page found")

            elif page_type == 'category':
                self.category_urls.add(url)
                logger.info(f"  → Category page found")

                # Extract links from category page
                links = self._extract_links(soup, url)

                # Crawl product links (don't go deeper on products)
                for link in links:
                    if self._is_product_url(link):
                        if link not in self.visited_urls:
                            self.visited_urls.add(link)
                            self.product_urls.add(link)

                # Crawl category links recursively
                for link in links:
                    if self._is_category_url(link) and link not in self.visited_urls:
                        await self._crawl_recursive(page, link, base_url, depth + 1)

            else:
                # General page - extract all links
                links = self._extract_links(soup, url)
                for link in links[:20]:  # Limit links per page
                    await self._crawl_recursive(page, link, base_url, depth + 1)

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")

    def _detect_page_type(self, soup: BeautifulSoup, url: str) -> str:
        """Detect if page is product, category, or general"""

        url_lower = url.lower()

        # Product page indicators
        product_indicators = [
            # URL patterns
            '/product/', '/item/', '/p/', '/dp/', '/gp/product/',
            # Schema.org
            soup.find('script', type='application/ld+json', string=re.compile('Product', re.I)),
            # Meta tags
            soup.find('meta', property='og:type', content='product'),
            soup.find('meta', property='product:price'),
            # Common selectors
            soup.find(class_=re.compile(r'product[_-]?price', re.I)),
            soup.find(class_=re.compile(r'add[_-]?to[_-]?cart', re.I)),
            soup.find('button', string=re.compile(r'add to (cart|basket)', re.I)),
            soup.find(class_=re.compile(r'product[_-]?details', re.I)),
            # Check if single product
            len(soup.find_all(class_=re.compile(r'product', re.I))) < 5
        ]

        if any(product_indicators) or any(p in url_lower for p in ['/product/', '/item/', '/p/', '/dp/']):
            return 'product'

        # Category page indicators
        category_indicators = [
            # URL patterns
            '/category/', '/collection/', '/shop/', '/catalog/', '/products/',
            # Multiple products
            len(soup.find_all(class_=re.compile(r'product[_-]?(card|item|tile)', re.I))) > 3,
            # Pagination
            soup.find(class_=re.compile(r'pagination', re.I)),
            soup.find('a', string=re.compile(r'next|previous|page \d+', re.I)),
            # Filters
            soup.find(class_=re.compile(r'filter|sort', re.I))
        ]

        if any(category_indicators) or any(c in url_lower for c in ['/category/', '/collection/', '/shop/']):
            return 'category'

        return 'general'

    def _is_product_url(self, url: str) -> bool:
        """Check if URL is likely a product page"""
        url_lower = url.lower()
        product_patterns = [
            '/product/', '/item/', '/p/', '/dp/', '/gp/product/',
            r'/\d+$',  # Ends with ID
            r'/[a-z0-9\-]+\-\d+',  # slug-id pattern
        ]
        return any(p in url_lower or re.search(p, url_lower) for p in product_patterns)

    def _is_category_url(self, url: str) -> bool:
        """Check if URL is likely a category page"""
        url_lower = url.lower()
        category_patterns = [
            '/category/', '/collection/', '/shop/', '/catalog/', '/products/',
            '/c/', '/cat/', '/department/', '/browse/'
        ]
        return any(p in url_lower for p in category_patterns)

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped"""
        url_lower = url.lower()
        skip_patterns = [
            '/cart', '/checkout', '/account', '/login', '/register',
            '/search', '/wishlist', '/compare', '/track',
            '/blog', '/about', '/contact', '/faq', '/help',
            '/terms', '/privacy', '/shipping', '/returns',
            '.jpg', '.png', '.gif', '.pdf', '.zip',
            'javascript:', 'mailto:', 'tel:'
        ]
        return any(p in url_lower for p in skip_patterns)

    def _is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL is from same domain"""
        url_domain = urlparse(url).netloc
        base_domain = urlparse(base_url).netloc
        return url_domain == base_domain or url_domain == '' or url_domain == base_domain.replace('www.', '')

    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract all valid links from page"""
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']

            # Make absolute URL
            absolute_url = urljoin(current_url, href)

            # Remove query params and fragments for deduplication
            parsed = urlparse(absolute_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            # Remove trailing slash
            clean_url = clean_url.rstrip('/')

            if clean_url and not self._should_skip_url(clean_url):
                links.append(clean_url)

        return list(set(links))  # Deduplicate

    async def _extract_products(self, page, product_urls: List[str]) -> List[Dict]:
        """Extract product data from discovered URLs"""
        products = []

        for i, url in enumerate(product_urls):
            logger.info(f"Extracting product {i+1}/{len(product_urls)}: {url}")

            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(self.delay)

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                product = self._parse_product_page(soup, url)
                if product:
                    products.append(product)

            except Exception as e:
                logger.error(f"Error extracting product {url}: {e}")
                continue

        return products

    def _parse_product_page(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Extract product data from product page"""
        try:
            # Try to find title
            title = None
            title_selectors = [
                soup.find('h1'),
                soup.find(class_=re.compile(r'product[_-]?title', re.I)),
                soup.find(itemprop='name'),
                soup.find('meta', property='og:title')
            ]
            for selector in title_selectors:
                if selector:
                    title = selector.get('content') if selector.name == 'meta' else selector.get_text(strip=True)
                    if title:
                        break

            if not title:
                return None

            # Try to find price
            price = None
            price_selectors = [
                soup.find(class_=re.compile(r'price', re.I)),
                soup.find(itemprop='price'),
                soup.find('meta', property='product:price:amount')
            ]
            for selector in price_selectors:
                if selector:
                    price_text = selector.get('content') if selector.name == 'meta' else selector.get_text(strip=True)
                    if price_text:
                        # Extract number
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            try:
                                price = float(price_match.group())
                                break
                            except:
                                pass

            # Try to find image
            image_url = None
            image_selectors = [
                soup.find('meta', property='og:image'),
                soup.find(itemprop='image'),
                soup.find(class_=re.compile(r'product[_-]?image', re.I))
            ]
            for selector in image_selectors:
                if selector:
                    image_url = selector.get('content') or selector.get('src') or selector.get('data-src')
                    if image_url:
                        break

            # Try to find stock status
            stock_status = 'Unknown'
            stock_indicators = soup.find_all(string=re.compile(r'in stock|out of stock|available|unavailable', re.I))
            if stock_indicators:
                stock_text = stock_indicators[0].lower()
                if 'in stock' in stock_text or 'available' in stock_text:
                    stock_status = 'In Stock'
                elif 'out of stock' in stock_text or 'unavailable' in stock_text:
                    stock_status = 'Out of Stock'

            return {
                'title': title,
                'price': price,
                'image_url': image_url,
                'stock_status': stock_status,
                'url': url
            }

        except Exception as e:
            logger.error(f"Error parsing product page: {e}")
            return None

    async def discover_categories(self, base_url: str) -> List[str]:
        """Quick discovery of category pages only"""
        result = await self.crawl_site(
            base_url=base_url,
            max_depth=2,
            category_only=True
        )
        return result.get('category_urls', [])


# Example usage
if __name__ == "__main__":
    async def test_crawler():
        crawler = SiteCrawler()

        # Test on a sample site
        result = await crawler.crawl_site(
            base_url="https://example-store.com",
            max_products=10,
            max_depth=2
        )

        print(f"\nCrawl Results:")
        print(f"Categories found: {result['categories_found']}")
        print(f"Products found: {result['products_found']}")
        print(f"Products scraped: {result['products_scraped']}")

        print(f"\nSample products:")
        for i, product in enumerate(result.get('products', [])[:5]):
            print(f"{i+1}. {product['title']} - ${product.get('price', 'N/A')}")

    asyncio.run(test_crawler())
