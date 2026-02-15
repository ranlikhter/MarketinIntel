"""
Integration API endpoints for importing products
Supports XML, WooCommerce, and Shopify imports
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import tempfile
import os

from database.connection import get_db
from database.models import ProductMonitored
from integrations.xml_parser import XMLProductParser
from integrations.woocommerce_integration import WooCommerceIntegration
from integrations.shopify_integration import ShopifyIntegration

router = APIRouter(prefix="/integrations", tags=["integrations"])


# Pydantic models
class WooCommerceConnection(BaseModel):
    store_url: str
    consumer_key: str
    consumer_secret: str
    import_limit: Optional[int] = 100


class ShopifyConnection(BaseModel):
    shop_url: str
    access_token: str
    import_limit: Optional[int] = 100


class ImportResult(BaseModel):
    success: bool
    products_imported: int
    products_skipped: int
    errors: List[str] = []


# XML Import
@router.post("/import/xml", response_model=ImportResult)
async def import_from_xml(
    file: UploadFile = File(...),
    format_type: str = Form('auto'),
    db: Session = Depends(get_db)
):
    """
    Import products from XML file

    - **file**: XML file containing products
    - **format_type**: Format type ('auto', 'google_shopping', 'woocommerce', 'custom')
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Parse XML
        parser = XMLProductParser()
        products = parser.parse_file(tmp_file_path, format_type)

        # Clean up temp file
        os.unlink(tmp_file_path)

        # Validate products
        valid_products = parser.validate_products(products)

        # Import to database
        imported_count = 0
        skipped_count = 0
        errors = []

        for product in valid_products:
            try:
                # Check if product already exists (by SKU or title)
                existing = None
                if product.get('sku'):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.sku == product['sku']
                    ).first()

                if not existing and product.get('title'):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.title == product['title']
                    ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Create new product
                new_product = ProductMonitored(
                    title=product['title'],
                    brand=product.get('brand'),
                    sku=product.get('sku'),
                    image_url=product.get('image_url')
                )

                db.add(new_product)
                imported_count += 1

            except Exception as e:
                errors.append(f"Error importing {product.get('title', 'Unknown')}: {str(e)}")

        db.commit()

        return ImportResult(
            success=True,
            products_imported=imported_count,
            products_skipped=skipped_count,
            errors=errors
        )

    except Exception as e:
        return ImportResult(
            success=False,
            products_imported=0,
            products_skipped=0,
            errors=[str(e)]
        )


# WooCommerce Import
@router.post("/import/woocommerce", response_model=ImportResult)
async def import_from_woocommerce(
    connection: WooCommerceConnection,
    db: Session = Depends(get_db)
):
    """
    Import products from WooCommerce store

    - **store_url**: WooCommerce store URL
    - **consumer_key**: API consumer key
    - **consumer_secret**: API consumer secret
    - **import_limit**: Max products to import (default: 100)
    """
    try:
        # Initialize WooCommerce connection
        wc = WooCommerceIntegration(
            store_url=connection.store_url,
            consumer_key=connection.consumer_key,
            consumer_secret=connection.consumer_secret
        )

        # Test connection
        test_result = wc.test_connection()
        if not test_result['success']:
            raise HTTPException(status_code=400, detail=f"Connection failed: {test_result.get('error')}")

        # Fetch products
        products = wc.get_all_products(max_products=connection.import_limit or 100)

        # Import to database
        imported_count = 0
        skipped_count = 0
        errors = []

        for product in products:
            try:
                # Check if product already exists
                existing = None
                if product.get('sku'):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.sku == product['sku']
                    ).first()

                if not existing and product.get('title'):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.title == product['title']
                    ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Create new product
                new_product = ProductMonitored(
                    title=product['title'],
                    brand=product.get('brand'),
                    sku=product.get('sku'),
                    image_url=product.get('image_url')
                )

                db.add(new_product)
                imported_count += 1

            except Exception as e:
                errors.append(f"Error importing {product.get('title', 'Unknown')}: {str(e)}")

        db.commit()

        return ImportResult(
            success=True,
            products_imported=imported_count,
            products_skipped=skipped_count,
            errors=errors
        )

    except HTTPException:
        raise
    except Exception as e:
        return ImportResult(
            success=False,
            products_imported=0,
            products_skipped=0,
            errors=[str(e)]
        )


# Shopify Import
@router.post("/import/shopify", response_model=ImportResult)
async def import_from_shopify(
    connection: ShopifyConnection,
    db: Session = Depends(get_db)
):
    """
    Import products from Shopify store

    - **shop_url**: Shopify store URL (e.g., 'your-store.myshopify.com')
    - **access_token**: Shopify Admin API access token
    - **import_limit**: Max products to import (default: 100)
    """
    try:
        # Initialize Shopify connection
        shopify = ShopifyIntegration(
            shop_url=connection.shop_url,
            access_token=connection.access_token
        )

        # Test connection
        test_result = shopify.test_connection()
        if not test_result['success']:
            raise HTTPException(status_code=400, detail=f"Connection failed: {test_result.get('error')}")

        # Fetch products
        products = shopify.get_all_products(max_products=connection.import_limit or 100)

        # Import to database
        imported_count = 0
        skipped_count = 0
        errors = []

        for product in products:
            try:
                # Check if product already exists
                existing = None
                if product.get('sku'):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.sku == product['sku']
                    ).first()

                if not existing and product.get('title'):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.title == product['title']
                    ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Create new product
                new_product = ProductMonitored(
                    title=product['title'],
                    brand=product.get('brand'),
                    sku=product.get('sku'),
                    image_url=product.get('image_url')
                )

                db.add(new_product)
                imported_count += 1

            except Exception as e:
                errors.append(f"Error importing {product.get('title', 'Unknown')}: {str(e)}")

        db.commit()

        return ImportResult(
            success=True,
            products_imported=imported_count,
            products_skipped=skipped_count,
            errors=errors
        )

    except HTTPException:
        raise
    except Exception as e:
        return ImportResult(
            success=False,
            products_imported=0,
            products_skipped=0,
            errors=[str(e)]
        )


# Test WooCommerce Connection
@router.post("/test/woocommerce")
async def test_woocommerce_connection(connection: WooCommerceConnection):
    """Test WooCommerce API connection"""
    try:
        wc = WooCommerceIntegration(
            store_url=connection.store_url,
            consumer_key=connection.consumer_key,
            consumer_secret=connection.consumer_secret
        )

        result = wc.test_connection()

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Connection failed'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Test Shopify Connection
@router.post("/test/shopify")
async def test_shopify_connection(connection: ShopifyConnection):
    """Test Shopify API connection"""
    try:
        shopify = ShopifyIntegration(
            shop_url=connection.shop_url,
            access_token=connection.access_token
        )

        result = shopify.test_connection()

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Connection failed'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get sample XML format
@router.get("/sample/xml")
async def get_sample_xml():
    """Get sample XML format for import"""
    sample = """<?xml version="1.0" encoding="UTF-8"?>
<products>
    <product>
        <title>Sony WH-1000XM5 Headphones</title>
        <brand>Sony</brand>
        <sku>WH1000XM5</sku>
        <price>399.99</price>
        <image>https://example.com/image.jpg</image>
        <description>Premium noise-canceling headphones</description>
        <category>Electronics</category>
    </product>
    <product>
        <title>Apple AirPods Pro</title>
        <brand>Apple</brand>
        <sku>AIRPODS-PRO-2</sku>
        <price>249.99</price>
        <image>https://example.com/airpods.jpg</image>
        <description>Wireless earbuds with active noise cancellation</description>
        <category>Electronics</category>
    </product>
</products>"""

    return {"xml": sample, "format": "custom"}
