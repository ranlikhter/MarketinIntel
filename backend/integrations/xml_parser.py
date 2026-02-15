"""
XML Product Feed Parser
Supports various XML formats including Google Shopping Feed, custom formats
"""

import xmltodict
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class XMLProductParser:
    """Parse XML product feeds and convert to standard format"""

    def __init__(self):
        self.supported_formats = ['google_shopping', 'custom', 'woocommerce']

    def parse_file(self, file_path: str, format_type: str = 'auto') -> List[Dict]:
        """
        Parse XML file and return list of products

        Args:
            file_path: Path to XML file
            format_type: Format type ('google_shopping', 'custom', 'woocommerce', 'auto')

        Returns:
            List of product dictionaries
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()

            return self.parse_string(xml_content, format_type)

        except Exception as e:
            logger.error(f"Failed to parse XML file: {e}")
            raise

    def parse_string(self, xml_string: str, format_type: str = 'auto') -> List[Dict]:
        """
        Parse XML string and return list of products

        Args:
            xml_string: XML content as string
            format_type: Format type ('google_shopping', 'custom', 'woocommerce', 'auto')

        Returns:
            List of product dictionaries
        """
        try:
            # Parse XML to dict
            data = xmltodict.parse(xml_string)

            # Auto-detect format
            if format_type == 'auto':
                format_type = self._detect_format(data)
                logger.info(f"Auto-detected XML format: {format_type}")

            # Parse based on format
            if format_type == 'google_shopping':
                return self._parse_google_shopping(data)
            elif format_type == 'woocommerce':
                return self._parse_woocommerce(data)
            else:
                return self._parse_custom(data)

        except Exception as e:
            logger.error(f"Failed to parse XML string: {e}")
            raise

    def _detect_format(self, data: Dict) -> str:
        """Auto-detect XML format based on structure"""

        # Check for Google Shopping Feed
        if 'rss' in data and 'channel' in data['rss']:
            if 'item' in data['rss']['channel']:
                # Check for g:id or g:title (Google Shopping namespace)
                items = data['rss']['channel']['item']
                if not isinstance(items, list):
                    items = [items]
                if items and any(key.startswith('g:') for key in items[0].keys()):
                    return 'google_shopping'

        # Check for WooCommerce format
        if 'products' in data or 'product' in data:
            return 'woocommerce'

        # Default to custom
        return 'custom'

    def _parse_google_shopping(self, data: Dict) -> List[Dict]:
        """Parse Google Shopping Feed format"""
        products = []

        try:
            items = data['rss']['channel']['item']
            if not isinstance(items, list):
                items = [items]

            for item in items:
                product = {
                    'title': item.get('title') or item.get('g:title', ''),
                    'brand': item.get('g:brand', ''),
                    'sku': item.get('g:id') or item.get('g:mpn', ''),
                    'image_url': item.get('g:image_link', ''),
                    'description': item.get('description') or item.get('g:description', ''),
                    'price': self._extract_price(item.get('g:price', '')),
                    'link': item.get('link') or item.get('g:link', ''),
                    'category': item.get('g:product_type', ''),
                    'gtin': item.get('g:gtin', ''),
                }

                # Only add if has title
                if product['title']:
                    products.append(product)

        except Exception as e:
            logger.error(f"Error parsing Google Shopping feed: {e}")
            raise

        logger.info(f"Parsed {len(products)} products from Google Shopping feed")
        return products

    def _parse_woocommerce(self, data: Dict) -> List[Dict]:
        """Parse WooCommerce export format"""
        products = []

        try:
            # WooCommerce can have multiple root elements
            if 'products' in data:
                items = data['products'].get('product', [])
            elif 'product' in data:
                items = data['product']
            else:
                items = []

            if not isinstance(items, list):
                items = [items]

            for item in items:
                product = {
                    'title': item.get('name') or item.get('title', ''),
                    'brand': item.get('brand', ''),
                    'sku': item.get('sku', ''),
                    'image_url': self._extract_image_url(item),
                    'description': item.get('description') or item.get('short_description', ''),
                    'price': self._extract_price(item.get('price') or item.get('regular_price', '')),
                    'link': item.get('permalink', ''),
                    'category': item.get('categories', ''),
                }

                if product['title']:
                    products.append(product)

        except Exception as e:
            logger.error(f"Error parsing WooCommerce feed: {e}")
            raise

        logger.info(f"Parsed {len(products)} products from WooCommerce feed")
        return products

    def _parse_custom(self, data: Dict) -> List[Dict]:
        """Parse custom XML format - flexible parser"""
        products = []

        try:
            # Try to find products array in various locations
            items = None

            # Common root elements
            for root_key in ['products', 'product', 'items', 'item', 'catalog', 'feed']:
                if root_key in data:
                    potential_items = data[root_key]

                    # If it's a dict with a nested array
                    if isinstance(potential_items, dict):
                        for nested_key in ['product', 'item', 'entry']:
                            if nested_key in potential_items:
                                items = potential_items[nested_key]
                                break
                    else:
                        items = potential_items

                    if items:
                        break

            if not items:
                logger.warning("Could not find products in XML structure")
                return []

            if not isinstance(items, list):
                items = [items]

            for item in items:
                # Flexible field mapping - try common field names
                product = {
                    'title': self._find_field(item, ['title', 'name', 'product_name', 'productName']),
                    'brand': self._find_field(item, ['brand', 'manufacturer', 'vendor']),
                    'sku': self._find_field(item, ['sku', 'id', 'product_id', 'productId', 'code']),
                    'image_url': self._find_field(item, ['image', 'image_url', 'imageUrl', 'img', 'picture']),
                    'description': self._find_field(item, ['description', 'desc', 'details']),
                    'price': self._extract_price(self._find_field(item, ['price', 'cost', 'amount'])),
                    'link': self._find_field(item, ['link', 'url', 'product_url', 'productUrl']),
                    'category': self._find_field(item, ['category', 'categories', 'type']),
                }

                if product['title']:
                    products.append(product)

        except Exception as e:
            logger.error(f"Error parsing custom XML feed: {e}")
            raise

        logger.info(f"Parsed {len(products)} products from custom XML feed")
        return products

    def _find_field(self, item: Dict, field_names: List[str]) -> str:
        """Find field value by trying multiple possible field names"""
        for field in field_names:
            if field in item:
                value = item[field]
                # Handle nested text nodes
                if isinstance(value, dict) and '#text' in value:
                    return str(value['#text'])
                return str(value) if value else ''
        return ''

    def _extract_price(self, price_str: str) -> Optional[float]:
        """Extract numeric price from string"""
        if not price_str:
            return None

        try:
            # Remove currency symbols and spaces
            price_str = str(price_str).replace('$', '').replace('€', '').replace('£', '').replace(',', '').strip()
            return float(price_str)
        except:
            return None

    def _extract_image_url(self, item: Dict) -> str:
        """Extract image URL from various possible locations"""
        # Try direct image field
        if 'image' in item:
            img = item['image']
            if isinstance(img, str):
                return img
            elif isinstance(img, dict):
                # Could be nested with src, url, etc.
                return img.get('src') or img.get('url') or img.get('#text', '')
            elif isinstance(img, list) and len(img) > 0:
                # Take first image
                first_img = img[0]
                if isinstance(first_img, str):
                    return first_img
                elif isinstance(first_img, dict):
                    return first_img.get('src') or first_img.get('url', '')

        # Try images array
        if 'images' in item and isinstance(item['images'], list) and len(item['images']) > 0:
            return item['images'][0] if isinstance(item['images'][0], str) else ''

        return ''

    def validate_products(self, products: List[Dict]) -> List[Dict]:
        """Validate and clean product data"""
        valid_products = []

        for product in products:
            # Title is required
            if not product.get('title'):
                logger.warning(f"Skipping product without title: {product}")
                continue

            # Clean up fields
            cleaned = {
                'title': product['title'][:500] if product.get('title') else '',  # Limit length
                'brand': product.get('brand', '')[:200] or None,
                'sku': product.get('sku', '')[:100] or None,
                'image_url': product.get('image_url', '')[:500] or None,
            }

            valid_products.append(cleaned)

        logger.info(f"Validated {len(valid_products)} out of {len(products)} products")
        return valid_products


# Example usage
if __name__ == "__main__":
    parser = XMLProductParser()

    # Test with sample XML
    sample_xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <products>
        <product>
            <title>Sony WH-1000XM5 Headphones</title>
            <brand>Sony</brand>
            <sku>WH1000XM5</sku>
            <price>399.99</price>
            <image>https://example.com/image.jpg</image>
        </product>
    </products>
    """

    products = parser.parse_string(sample_xml)
    print(f"Parsed {len(products)} products:")
    for p in products:
        print(f"  - {p['title']} ({p['brand']}) - ${p['price']}")
