"""
WooCommerce API Integration
Connects to WooCommerce stores and imports products
"""

from woocommerce import API
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class WooCommerceIntegration:
    """Integration with WooCommerce REST API"""

    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str, version: str = 'wc/v3'):
        """
        Initialize WooCommerce API connection

        Args:
            store_url: WooCommerce store URL (e.g., 'https://yourstore.com')
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
            version: API version (default: 'wc/v3')
        """
        self.store_url = store_url
        self.wcapi = API(
            url=store_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version=version,
            timeout=30
        )

    def test_connection(self) -> Dict:
        """
        Test the WooCommerce API connection

        Returns:
            Dict with success status and store info
        """
        try:
            # Get store info
            response = self.wcapi.get("system_status")

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'store_url': self.store_url,
                    'version': data.get('environment', {}).get('version', 'Unknown')
                }
            else:
                return {
                    'success': False,
                    'error': f"API returned status {response.status_code}"
                }

        except Exception as e:
            logger.error(f"WooCommerce connection test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_products(
        self,
        per_page: int = 100,
        page: int = 1,
        status: str = 'publish',
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch products from WooCommerce store

        Args:
            per_page: Number of products per page (max 100)
            page: Page number
            status: Product status ('publish', 'draft', 'pending', 'private')
            category: Filter by category ID

        Returns:
            List of product dictionaries
        """
        try:
            params = {
                'per_page': min(per_page, 100),
                'page': page,
                'status': status
            }

            if category:
                params['category'] = category

            response = self.wcapi.get("products", params=params)

            if response.status_code != 200:
                logger.error(f"Failed to fetch products: {response.status_code}")
                return []

            products_data = response.json()
            products = []

            for item in products_data:
                product = self._parse_product(item)
                if product:
                    products.append(product)

            logger.info(f"Fetched {len(products)} products from WooCommerce (page {page})")
            return products

        except Exception as e:
            logger.error(f"Error fetching WooCommerce products: {e}")
            return []

    def get_all_products(
        self,
        status: str = 'publish',
        category: Optional[str] = None,
        max_products: int = 1000
    ) -> List[Dict]:
        """
        Fetch all products from WooCommerce store (paginated)

        Args:
            status: Product status filter
            category: Category filter
            max_products: Maximum products to fetch

        Returns:
            List of all product dictionaries
        """
        all_products = []
        page = 1
        per_page = 100

        while len(all_products) < max_products:
            products = self.get_products(
                per_page=per_page,
                page=page,
                status=status,
                category=category
            )

            if not products:
                break

            all_products.extend(products)

            # If we got less than per_page, we've reached the end
            if len(products) < per_page:
                break

            page += 1

        logger.info(f"Fetched total of {len(all_products)} products from WooCommerce")
        return all_products[:max_products]

    def _parse_product(self, item: Dict) -> Optional[Dict]:
        """Parse WooCommerce product to standard format"""
        try:
            # Get main image
            image_url = ''
            if item.get('images') and len(item['images']) > 0:
                image_url = item['images'][0].get('src', '')

            # Get brand from attributes or meta data
            brand = ''
            if item.get('brands') and len(item['brands']) > 0:
                brand = item['brands'][0].get('name', '')
            else:
                # Try to find brand in attributes
                for attr in item.get('attributes', []):
                    if attr.get('name', '').lower() in ['brand', 'manufacturer']:
                        brand = attr.get('options', [''])[0] if attr.get('options') else ''
                        break

            # Get categories
            categories = ', '.join([cat['name'] for cat in item.get('categories', [])])

            product = {
                'title': item.get('name', ''),
                'brand': brand,
                'sku': item.get('sku', ''),
                'image_url': image_url,
                'description': item.get('description', '') or item.get('short_description', ''),
                'price': float(item.get('price', 0)) if item.get('price') else None,
                'link': item.get('permalink', ''),
                'category': categories,
                'stock_status': item.get('stock_status', 'unknown'),
                'wc_id': item.get('id'),
                'external_id': str(item.get('id'))
            }

            return product if product['title'] else None

        except Exception as e:
            logger.error(f"Error parsing WooCommerce product: {e}")
            return None

    def get_categories(self) -> List[Dict]:
        """
        Fetch all product categories

        Returns:
            List of category dictionaries
        """
        try:
            response = self.wcapi.get("products/categories", params={'per_page': 100})

            if response.status_code != 200:
                logger.error(f"Failed to fetch categories: {response.status_code}")
                return []

            categories = response.json()
            return [
                {
                    'id': cat['id'],
                    'name': cat['name'],
                    'slug': cat['slug'],
                    'parent': cat['parent'],
                    'count': cat['count']
                }
                for cat in categories
            ]

        except Exception as e:
            logger.error(f"Error fetching WooCommerce categories: {e}")
            return []

    def sync_product_status(self, wc_product_id: int) -> Optional[Dict]:
        """
        Get current status of a specific product

        Args:
            wc_product_id: WooCommerce product ID

        Returns:
            Product data or None
        """
        try:
            response = self.wcapi.get(f"products/{wc_product_id}")

            if response.status_code == 200:
                return self._parse_product(response.json())
            else:
                logger.error(f"Failed to fetch product {wc_product_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error syncing WooCommerce product: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Example: Connect to WooCommerce store
    wc = WooCommerceIntegration(
        store_url="https://yourstore.com",
        consumer_key="ck_xxxxx",
        consumer_secret="cs_xxxxx"
    )

    # Test connection
    result = wc.test_connection()
    print(f"Connection test: {result}")

    if result['success']:
        # Get products
        products = wc.get_products(per_page=10)
        print(f"\nFound {len(products)} products:")
        for p in products[:5]:
            print(f"  - {p['title']} ({p['brand']}) - ${p['price']}")

        # Get categories
        categories = wc.get_categories()
        print(f"\nFound {len(categories)} categories:")
        for c in categories[:5]:
            print(f"  - {c['name']} ({c['count']} products)")
