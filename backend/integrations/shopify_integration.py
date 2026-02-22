"""
Shopify API Integration
Connects to Shopify stores and imports products
"""

import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ShopifyIntegration:
    """Integration with Shopify Admin API"""

    def __init__(self, shop_url: str, access_token: str, api_version: str = '2024-01'):
        """
        Initialize Shopify API connection

        Args:
            shop_url: Shopify store URL (e.g., 'your-store.myshopify.com')
            access_token: Shopify Admin API access token
            api_version: API version (default: '2024-01')
        """
        # Clean shop URL
        self.shop_url = shop_url.replace('https://', '').replace('http://', '').strip('/')
        if not self.shop_url.endswith('.myshopify.com'):
            self.shop_url = f"{self.shop_url}.myshopify.com"

        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{self.shop_url}/admin/api/{api_version}"

        self.headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }

    def test_connection(self) -> Dict:
        """
        Test the Shopify API connection

        Returns:
            Dict with success status and store info
        """
        try:
            response = requests.get(
                f"{self.base_url}/shop.json",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                shop = data.get('shop', {})
                return {
                    'success': True,
                    'store_url': self.shop_url,
                    'store_name': shop.get('name', 'Unknown'),
                    'email': shop.get('email', ''),
                    'currency': shop.get('currency', 'USD')
                }
            else:
                return {
                    'success': False,
                    'error': f"API returned status {response.status_code}: {response.text}"
                }

        except Exception as e:
            logger.error(f"Shopify connection test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_products(
        self,
        limit: int = 250,
        since_id: Optional[int] = None,
        status: str = 'active'
    ) -> List[Dict]:
        """
        Fetch products from Shopify store

        Args:
            limit: Number of products per page (max 250)
            since_id: Restrict results to after the specified ID
            status: Product status ('active', 'archived', 'draft')

        Returns:
            List of product dictionaries
        """
        try:
            params = {
                'limit': min(limit, 250),
                'status': status
            }

            if since_id:
                params['since_id'] = since_id

            response = requests.get(
                f"{self.base_url}/products.json",
                headers=self.headers,
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch products: {response.status_code} - {response.text}")
                return []

            data = response.json()
            products_data = data.get('products', [])
            products = []

            for item in products_data:
                product = self._parse_product(item)
                if product:
                    products.append(product)

            logger.info(f"Fetched {len(products)} products from Shopify")
            return products

        except Exception as e:
            logger.error(f"Error fetching Shopify products: {e}")
            return []

    def get_all_products(
        self,
        status: str = 'active',
        max_products: int = 1000
    ) -> List[Dict]:
        """
        Fetch all products from Shopify store (paginated)

        Args:
            status: Product status filter
            max_products: Maximum products to fetch

        Returns:
            List of all product dictionaries
        """
        all_products = []
        limit = 250
        since_id = None

        while len(all_products) < max_products:
            products = self.get_products(
                limit=limit,
                since_id=since_id,
                status=status
            )

            if not products:
                break

            all_products.extend(products)

            # If we got less than limit, we've reached the end
            if len(products) < limit:
                break

            # Use last product ID for pagination
            since_id = products[-1].get('shopify_id')

            if not since_id:
                break

        logger.info(f"Fetched total of {len(all_products)} products from Shopify")
        return all_products[:max_products]

    def _parse_product(self, item: Dict) -> Optional[Dict]:
        """Parse Shopify product to standard format"""
        try:
            # Get main variant (first variant or default)
            variants = item.get('variants', [])
            main_variant = variants[0] if variants else {}

            # Get main image
            image_url = ''
            if item.get('images') and len(item['images']) > 0:
                image_url = item['images'][0].get('src', '')
            elif item.get('image'):
                image_url = item['image'].get('src', '')

            # Get brand/vendor
            brand = item.get('vendor', '')

            # Get price
            price = None
            if main_variant.get('price'):
                try:
                    price = float(main_variant['price'])
                except:
                    pass

            # Get product type/category
            category = item.get('product_type', '')

            product = {
                'title': item.get('title', ''),
                'brand': brand,
                'sku': main_variant.get('sku', ''),
                'image_url': image_url,
                'description': item.get('body_html', ''),
                'price': price,
                'link': f"https://{self.shop_url}/products/{item.get('handle', '')}",
                'category': category,
                'stock_status': 'In Stock' if main_variant.get('inventory_quantity', 0) > 0 else 'Out of Stock',
                'shopify_id': item.get('id'),
                'external_id': str(item.get('id'))
            }

            return product if product['title'] else None

        except Exception as e:
            logger.error(f"Error parsing Shopify product: {e}")
            return None

    def update_product_price(self, sku: str, new_price: float, title: str = '') -> Dict:
        """
        Update a product variant's price in Shopify by SKU, with title as fallback.

        Args:
            sku: Variant SKU to search for
            new_price: New price to set
            title: Product title used as fallback search term

        Returns:
            Dict with success status, variant_id on success, or error message
        """
        try:
            target_variant_id = None

            # Search products by title (Shopify REST has no direct SKU search)
            search_params = {'limit': 50, 'status': 'active'}
            if title:
                search_params['title'] = title

            response = requests.get(
                f"{self.base_url}/products.json",
                headers=self.headers,
                params=search_params,
                timeout=30
            )

            if response.status_code != 200:
                return {'success': False, 'error': f'Shopify search failed: {response.status_code}'}

            products = response.json().get('products', [])

            # Find variant with matching SKU
            if sku:
                for product in products:
                    for variant in product.get('variants', []):
                        if variant.get('sku', '').strip().lower() == sku.strip().lower():
                            target_variant_id = variant['id']
                            break
                    if target_variant_id:
                        break

            # Fallback: use first variant of first product
            if not target_variant_id and products:
                first_variants = products[0].get('variants', [])
                if first_variants:
                    target_variant_id = first_variants[0]['id']

            if not target_variant_id:
                return {
                    'success': False,
                    'error': 'Product not found in Shopify store (no SKU or title match)'
                }

            # Update the variant price
            update_response = requests.put(
                f"{self.base_url}/variants/{target_variant_id}.json",
                headers=self.headers,
                json={'variant': {'id': target_variant_id, 'price': str(round(new_price, 2))}},
                timeout=30
            )

            if update_response.status_code == 200:
                return {'success': True, 'variant_id': target_variant_id, 'new_price': new_price}
            else:
                return {
                    'success': False,
                    'error': f'Shopify price update failed: {update_response.status_code}'
                }

        except Exception as e:
            logger.error(f"Error updating Shopify variant price: {e}")
            return {'success': False, 'error': str(e)}

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """
        Get a specific product by ID

        Args:
            product_id: Shopify product ID

        Returns:
            Product data or None
        """
        try:
            response = requests.get(
                f"{self.base_url}/products/{product_id}.json",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_product(data.get('product', {}))
            else:
                logger.error(f"Failed to fetch product {product_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching Shopify product: {e}")
            return None

    def get_collections(self) -> List[Dict]:
        """
        Fetch all collections (categories)

        Returns:
            List of collection dictionaries
        """
        try:
            response = requests.get(
                f"{self.base_url}/custom_collections.json",
                headers=self.headers,
                params={'limit': 250},
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch collections: {response.status_code}")
                return []

            data = response.json()
            collections = data.get('custom_collections', [])

            return [
                {
                    'id': col['id'],
                    'title': col['title'],
                    'handle': col['handle'],
                    'body_html': col.get('body_html', ''),
                }
                for col in collections
            ]

        except Exception as e:
            logger.error(f"Error fetching Shopify collections: {e}")
            return []

    def get_products_by_collection(self, collection_id: int) -> List[Dict]:
        """
        Get products in a specific collection

        Args:
            collection_id: Shopify collection ID

        Returns:
            List of products in collection
        """
        try:
            response = requests.get(
                f"{self.base_url}/collections/{collection_id}/products.json",
                headers=self.headers,
                params={'limit': 250},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch collection products: {response.status_code}")
                return []

            data = response.json()
            products_data = data.get('products', [])

            return [self._parse_product(item) for item in products_data if self._parse_product(item)]

        except Exception as e:
            logger.error(f"Error fetching collection products: {e}")
            return []

    def search_products(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search products by query

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching products
        """
        try:
            response = requests.get(
                f"{self.base_url}/products.json",
                headers=self.headers,
                params={
                    'limit': min(limit, 250),
                    'title': query  # Search by title
                },
                timeout=30
            )

            if response.status_code != 200:
                return []

            data = response.json()
            products_data = data.get('products', [])

            return [self._parse_product(item) for item in products_data if self._parse_product(item)]

        except Exception as e:
            logger.error(f"Error searching Shopify products: {e}")
            return []


# Example usage
if __name__ == "__main__":
    # Example: Connect to Shopify store
    shopify = ShopifyIntegration(
        shop_url="your-store.myshopify.com",
        access_token="shpat_xxxxx"
    )

    # Test connection
    result = shopify.test_connection()
    print(f"Connection test: {result}")

    if result['success']:
        # Get products
        products = shopify.get_products(limit=10)
        print(f"\nFound {len(products)} products:")
        for p in products[:5]:
            print(f"  - {p['title']} ({p['brand']}) - ${p['price']}")

        # Get collections
        collections = shopify.get_collections()
        print(f"\nFound {len(collections)} collections:")
        for c in collections[:5]:
            print(f"  - {c['title']}")
