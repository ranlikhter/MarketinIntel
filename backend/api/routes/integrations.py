"""
Integration API endpoints for importing products
Supports CSV, XML, WooCommerce, and Shopify imports
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import tempfile
import os
import csv
import io
import ipaddress
import re
import socket
import secrets
import hmac
import hashlib
import httpx
from datetime import datetime
from urllib.parse import urlparse, urlencode

from database.connection import get_db
from database.models import ProductMonitored, StoreConnection, User
from integrations.xml_parser import XMLProductParser
from integrations.woocommerce_integration import WooCommerceIntegration
from integrations.shopify_integration import ShopifyIntegration
from api.dependencies import get_current_user
from services.activity_service import log_activity
from services.cache_service import _get_redis_client

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


def _find_existing_product_for_user(db: Session, user_id: int, sku: Optional[str], title: Optional[str]):
    """
    Deduplicate per user so identical SKUs/titles across different users do not collide.
    """
    existing = None
    if sku:
        existing = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == user_id,
            ProductMonitored.sku == sku,
        ).first()

    if not existing and title:
        existing = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == user_id,
            ProductMonitored.title == title,
        ).first()

    return existing


def _require_public_ip(ip_text: str) -> None:
    ip = ipaddress.ip_address(ip_text)
    if not ip.is_global:
        raise HTTPException(
            status_code=400,
            detail="Store URL must not point to localhost, private, or internal network addresses",
        )


def _require_public_hostname(hostname: str) -> None:
    normalized = hostname.rstrip(".").lower()
    if normalized in {"localhost", "host.docker.internal"} or normalized.endswith(".local") or "." not in normalized:
        raise HTTPException(
            status_code=400,
            detail="Store URL must use a public hostname",
        )

    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=400,
            detail="Store URL host could not be resolved",
        ) from exc

    seen = set()
    for info in infos:
        resolved_ip = info[4][0]
        if resolved_ip in seen:
            continue
        seen.add(resolved_ip)
        _require_public_ip(resolved_ip)


def _normalize_woocommerce_store_url(store_url: str) -> str:
    parsed = urlparse(store_url.strip())
    if parsed.scheme != "https":
        raise HTTPException(
            status_code=400,
            detail="WooCommerce store URL must use https",
        )
    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=400,
            detail="Store URL must not include embedded credentials",
        )
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Store URL is invalid")

    try:
        _require_public_ip(parsed.hostname)
    except ValueError:
        _require_public_hostname(parsed.hostname)

    normalized = parsed._replace(query="", fragment="")
    return normalized.geturl().rstrip("/")


def _normalize_shopify_shop_url(shop_url: str) -> str:
    normalized = shop_url.replace("https://", "").replace("http://", "").strip().strip("/")
    if not normalized:
        raise HTTPException(status_code=400, detail="Shopify shop URL is required")
    if any(char in normalized for char in "@/?:#"):
        raise HTTPException(
            status_code=400,
            detail="Shopify shop URL must be a shop hostname only",
        )
    if normalized.endswith(".myshopify.com"):
        pass
    else:
        if "." in normalized or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", normalized, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Shopify shop URL must be a myshopify.com hostname or bare shop slug",
            )
        normalized = f"{normalized}.myshopify.com"

    _require_public_hostname(normalized)
    return normalized


# XML Import
@router.post("/import/xml", response_model=ImportResult)
async def import_from_xml(
    file: UploadFile = File(...),
    format_type: str = Form('auto'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Import products from WooCommerce store

    - **store_url**: WooCommerce store URL
    - **consumer_key**: API consumer key
    - **consumer_secret**: API consumer secret
    - **import_limit**: Max products to import (default: 100)
    """
    try:
        store_url = _normalize_woocommerce_store_url(connection.store_url)

        # Initialize WooCommerce connection
        wc = WooCommerceIntegration(
            store_url=store_url,
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
                existing = _find_existing_product_for_user(
                    db,
                    current_user.id,
                    product.get('sku'),
                    product.get('title'),
                )

                if existing:
                    skipped_count += 1
                    continue

                # Create new product
                new_product = ProductMonitored(
                    user_id=current_user.id,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import products from Shopify store

    - **shop_url**: Shopify store URL (e.g., 'your-store.myshopify.com')
    - **access_token**: Shopify Admin API access token
    - **import_limit**: Max products to import (default: 100)
    """
    try:
        shop_url = _normalize_shopify_shop_url(connection.shop_url)

        # Initialize Shopify connection
        shopify = ShopifyIntegration(
            shop_url=shop_url,
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
                existing = _find_existing_product_for_user(
                    db,
                    current_user.id,
                    product.get('sku'),
                    product.get('title'),
                )

                if existing:
                    skipped_count += 1
                    continue

                # Create new product
                new_product = ProductMonitored(
                    user_id=current_user.id,
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


# ─── Price Push ───────────────────────────────────────────────────────────────

class WooCommercePricePushRequest(BaseModel):
    store_url: str
    consumer_key: str
    consumer_secret: str
    sku: Optional[str] = ''
    title: Optional[str] = ''
    new_price: float


class ShopifyPricePushRequest(BaseModel):
    shop_url: str
    access_token: str
    sku: Optional[str] = ''
    title: Optional[str] = ''
    new_price: float


@router.post("/push-price/woocommerce")
async def push_price_woocommerce(
    request: WooCommercePricePushRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a product's price on a WooCommerce store.
    Matches by SKU first, then title fallback.
    """
    try:
        store_url = _normalize_woocommerce_store_url(request.store_url)

        wc = WooCommerceIntegration(
            store_url=store_url,
            consumer_key=request.consumer_key,
            consumer_secret=request.consumer_secret
        )
        result = wc.update_product_price(
            sku=request.sku or '',
            new_price=request.new_price,
            title=request.title or ''
        )
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Price update failed'))
        log_activity(db, current_user.id, "store.push_price", "integration", f"Pushed price ${request.new_price:.2f} for '{request.title or request.sku}' to WooCommerce", metadata={"platform": "woocommerce", "sku": request.sku, "new_price": request.new_price})
        db.flush()
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push-price/shopify")
async def push_price_shopify(
    request: ShopifyPricePushRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update a product variant's price on a Shopify store.
    Matches variant by SKU first, then first variant of title-matched product.
    """
    try:
        shop_url = _normalize_shopify_shop_url(request.shop_url)

        shopify = ShopifyIntegration(
            shop_url=shop_url,
            access_token=request.access_token
        )
        result = shopify.update_product_price(
            sku=request.sku or '',
            new_price=request.new_price,
            title=request.title or ''
        )
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Price update failed'))
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Test WooCommerce Connection
@router.post("/test/woocommerce")
async def test_woocommerce_connection(
    connection: WooCommerceConnection,
    current_user: User = Depends(get_current_user),
):
    """Test WooCommerce API connection"""
    try:
        store_url = _normalize_woocommerce_store_url(connection.store_url)
        wc = WooCommerceIntegration(
            store_url=store_url,
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
async def test_shopify_connection(
    connection: ShopifyConnection,
    current_user: User = Depends(get_current_user),
):
    """Test Shopify API connection"""
    try:
        shop_url = _normalize_shopify_shop_url(connection.shop_url)
        shopify = ShopifyIntegration(
            shop_url=shop_url,
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


# ─── CSV Import ───────────────────────────────────────────────────────────────

# Accepted column name aliases (case-insensitive)
_CSV_FIELD_MAP = {
    "title": "title", "name": "title", "product_name": "title", "product title": "title",
    "sku": "sku", "product_sku": "sku",
    "brand": "brand", "manufacturer": "brand",
    "my_price": "my_price", "price": "my_price", "selling_price": "my_price", "sale_price": "my_price",
    "cost_price": "cost_price", "cost": "cost_price", "cogs": "cost_price",
    "mpn": "mpn", "manufacturer_part_number": "mpn",
    "upc": "upc_ean", "ean": "upc_ean", "upc_ean": "upc_ean", "barcode": "upc_ean",
    "asin": "asin",
    "category": "category",
    "description": "description",
    "image_url": "image_url", "image": "image_url", "image_link": "image_url",
    "model_number": "model_number", "model": "model_number",
    "keywords": "keywords",
}


@router.post("/import/csv", response_model=ImportResult)
async def import_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import products from a CSV file.

    **Required column:** `title` (also accepted: `name`, `product_name`)

    **Optional columns:** `sku`, `brand`, `my_price`, `cost_price`, `mpn`,
    `upc_ean` (or `upc`/`ean`/`barcode`), `asin`, `category`, `description`,
    `image_url`, `model_number`, `keywords`

    Column names are case-insensitive. Duplicate products (same SKU or title)
    are skipped rather than overwritten.

    Download a sample template from `GET /integrations/sample/csv`.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig")  # strip BOM if present
        reader = csv.DictReader(io.StringIO(text))

        # Normalise header names
        if not reader.fieldnames:
            return ImportResult(success=False, products_imported=0, products_skipped=0,
                                errors=["CSV file appears to be empty"])

        header_map: dict[str, str] = {}
        for col in reader.fieldnames:
            norm = col.strip().lower().replace(" ", "_")
            if norm in _CSV_FIELD_MAP:
                header_map[col] = _CSV_FIELD_MAP[norm]

        if "title" not in header_map.values():
            return ImportResult(
                success=False, products_imported=0, products_skipped=0,
                errors=["CSV must contain a 'title' (or 'name' / 'product_name') column"]
            )

        imported_count = 0
        skipped_count = 0
        errors: List[str] = []

        for row in reader:
            # Map raw CSV row to canonical field names
            mapped: dict = {}
            for raw_col, canonical in header_map.items():
                val = row.get(raw_col, "").strip()
                if val:
                    mapped[canonical] = val

            title = mapped.get("title")
            if not title:
                skipped_count += 1
                continue

            try:
                # Dedup: same SKU or same title
                existing = None
                if mapped.get("sku"):
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.user_id == current_user.id,
                        ProductMonitored.sku == mapped["sku"]
                    ).first()
                if not existing:
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.user_id == current_user.id,
                        ProductMonitored.title == title
                    ).first()
                if existing:
                    skipped_count += 1
                    continue

                def _float(val):
                    try:
                        return float(val) if val else None
                    except ValueError:
                        return None

                new_product = ProductMonitored(
                    user_id=current_user.id,
                    title=title,
                    sku=mapped.get("sku"),
                    brand=mapped.get("brand"),
                    my_price=_float(mapped.get("my_price")),
                    cost_price=_float(mapped.get("cost_price")),
                    mpn=mapped.get("mpn"),
                    upc_ean=mapped.get("upc_ean"),
                    asin=mapped.get("asin"),
                    category=mapped.get("category"),
                    description=mapped.get("description"),
                    image_url=mapped.get("image_url"),
                    model_number=mapped.get("model_number"),
                    keywords=mapped.get("keywords"),
                )
                db.add(new_product)
                imported_count += 1

            except Exception as exc:
                errors.append(f"Row '{title}': {str(exc)}")

        db.commit()
        log_activity(
            db, current_user.id, "import.csv", "product",
            f"Imported {imported_count} products via CSV ({skipped_count} skipped)",
            metadata={"imported": imported_count, "skipped": skipped_count, "errors": len(errors)}
        )

        return ImportResult(
            success=True,
            products_imported=imported_count,
            products_skipped=skipped_count,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as exc:
        return ImportResult(success=False, products_imported=0, products_skipped=0, errors=[str(exc)])


@router.get("/sample/csv")
async def get_sample_csv():
    """
    Download a sample CSV template showing all supported columns.

    Use this as a starting point for bulk product imports.
    """
    from fastapi.responses import Response
    header = "title,sku,brand,my_price,cost_price,mpn,upc_ean,asin,category,description,image_url,keywords"
    row1   = 'Sony WH-1000XM5 Headphones,WH1000XM5,Sony,349.99,180.00,WH1000XM5/B,094922563484,B09XS7JWHH,Electronics > Headphones,Premium noise-canceling wireless headphones,https://example.com/wh1000xm5.jpg,"sony headphones wireless noise canceling"'
    row2   = 'Apple AirPods Pro (2nd Gen),AIRPODS-PRO-2,Apple,249.99,120.00,MQD83LL/A,194253378297,B0BDHWDR12,Electronics > Earbuds,Active noise cancellation wireless earbuds,https://example.com/airpods-pro.jpg,"apple airpods wireless earbuds"'
    csv_content = "\n".join([header, row1, row2])
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=marketintel_import_template.csv"},
    )


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


# ─── Store Connections (persisted credentials for inventory sync) ──────────────

class StoreConnectionCreate(BaseModel):
    platform: str          # "shopify" | "woocommerce"
    store_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    sync_inventory: bool = True


def _fmt_conn(c: StoreConnection) -> dict:
    return {
        "id": c.id,
        "platform": c.platform,
        "store_url": c.store_url,
        "sync_inventory": c.sync_inventory,
        "is_active": c.is_active,
        "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
        "created_at": c.created_at.isoformat(),
    }


@router.get("/store-connections")
def list_store_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all saved store connections for the current user."""
    conns = db.query(StoreConnection).filter(
        StoreConnection.user_id == current_user.id
    ).order_by(StoreConnection.created_at.desc()).all()
    return [_fmt_conn(c) for c in conns]


@router.post("/store-connections", status_code=201)
def save_store_connection(
    body: StoreConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persist store credentials so the server can sync inventory on a schedule."""
    platform = body.platform.lower()
    if platform not in ("shopify", "woocommerce"):
        raise HTTPException(status_code=422, detail="platform must be 'shopify' or 'woocommerce'")

    store_url = (
        _normalize_shopify_shop_url(body.store_url)
        if platform == "shopify"
        else _normalize_woocommerce_store_url(body.store_url)
    )

    conn = StoreConnection(
        user_id=current_user.id,
        platform=platform,
        store_url=store_url,
        api_key=body.api_key,
        api_secret=body.api_secret,
        sync_inventory=body.sync_inventory,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return _fmt_conn(conn)


@router.delete("/store-connections/{conn_id}")
def delete_store_connection(
    conn_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = db.query(StoreConnection).filter(
        StoreConnection.id == conn_id,
        StoreConnection.user_id == current_user.id,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Store connection not found")
    db.delete(conn)
    db.commit()
    return {"success": True}


@router.post("/store-connections/{conn_id}/sync")
def trigger_inventory_sync(
    conn_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger an immediate inventory sync for one store connection."""
    conn = db.query(StoreConnection).filter(
        StoreConnection.id == conn_id,
        StoreConnection.user_id == current_user.id,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Store connection not found")

    try:
        from tasks.inventory_tasks import sync_single_connection
        task = sync_single_connection.delay(conn_id)
        return {"success": True, "task_id": task.id, "message": "Inventory sync queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Shopify OAuth (One-Click Connect) ────────────────────────────────────────

_SHOPIFY_SCOPES = "read_products,write_products,read_inventory,write_inventory"
_OAUTH_STATE_TTL = 600  # 10 minutes


def _get_shopify_app_credentials():
    client_id = os.getenv("SHOPIFY_APP_CLIENT_ID", "")
    client_secret = os.getenv("SHOPIFY_APP_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=501,
            detail="Shopify OAuth app is not configured. Set SHOPIFY_APP_CLIENT_ID and SHOPIFY_APP_CLIENT_SECRET.",
        )
    return client_id, client_secret


def _validate_shopify_hmac(params: dict, client_secret: str) -> bool:
    """Validate the HMAC signature Shopify sends on the OAuth callback."""
    provided_hmac = params.get("hmac", "")
    filtered = {k: v for k, v in params.items() if k != "hmac"}
    sorted_pairs = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    computed = hmac.new(
        client_secret.encode("utf-8"),
        sorted_pairs.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, provided_hmac)


@router.get("/shopify/oauth/start")
def shopify_oauth_start(
    shop: str = Query(..., description="Shopify store domain, e.g. mystore.myshopify.com"),
    current_user: User = Depends(get_current_user),
):
    """
    Step 1 of Shopify OAuth — returns the Shopify authorization URL.
    The frontend redirects the user there to grant access.
    """
    client_id, _ = _get_shopify_app_credentials()

    # Normalise and validate shop domain
    shop = _normalize_shopify_shop_url(shop)

    # Generate a secure random state nonce and store user_id in Redis
    state = secrets.token_urlsafe(32)
    redis = _get_redis_client()
    if redis:
        redis.setex(f"shopify_oauth:{state}", _OAUTH_STATE_TTL, str(current_user.id))

    redirect_uri = f"{os.getenv('APP_URL', 'http://localhost:8000')}/api/integrations/shopify/oauth/callback"
    scopes = os.getenv("SHOPIFY_APP_SCOPES", _SHOPIFY_SCOPES)

    params = urlencode({
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
        "grant_options[]": "per-user",
    })
    auth_url = f"https://{shop}/admin/oauth/authorize?{params}"
    return {"auth_url": auth_url, "shop": shop, "state": state}


@router.get("/shopify/oauth/callback")
async def shopify_oauth_callback(
    code: str = Query(...),
    shop: str = Query(...),
    state: str = Query(...),
    hmac: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """
    Step 2 of Shopify OAuth — Shopify redirects here after the merchant approves.
    Exchanges the auth code for a permanent access token and saves the connection.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    error_redirect = f"{frontend_url}/integrations/shopify-callback?success=false"

    client_id, client_secret = _get_shopify_app_credentials()

    # 1. Validate HMAC signature
    all_params = {"code": code, "shop": shop, "state": state, "hmac": hmac}
    if not _validate_shopify_hmac(all_params, client_secret):
        return RedirectResponse(f"{error_redirect}&error=invalid_hmac")

    # 2. Validate state nonce and retrieve user_id from Redis
    redis = _get_redis_client()
    user_id = None
    if redis:
        stored = redis.get(f"shopify_oauth:{state}")
        if stored:
            user_id = int(stored)
            redis.delete(f"shopify_oauth:{state}")

    if not user_id:
        return RedirectResponse(f"{error_redirect}&error=invalid_state")

    # 3. Normalise shop domain
    try:
        shop = _normalize_shopify_shop_url(shop)
    except HTTPException:
        return RedirectResponse(f"{error_redirect}&error=invalid_shop")

    # 4. Exchange code for permanent access token
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://{shop}/admin/oauth/access_token",
                json={"client_id": client_id, "client_secret": client_secret, "code": code},
            )
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
    except Exception:
        return RedirectResponse(f"{error_redirect}&error=token_exchange_failed")

    if not access_token:
        return RedirectResponse(f"{error_redirect}&error=no_token")

    # 5. Upsert StoreConnection
    existing = db.query(StoreConnection).filter(
        StoreConnection.user_id == user_id,
        StoreConnection.platform == "shopify",
        StoreConnection.store_url == shop,
    ).first()

    if existing:
        existing.api_key = access_token
        existing.is_active = True
    else:
        conn = StoreConnection(
            user_id=user_id,
            platform="shopify",
            store_url=shop,
            api_key=access_token,
            sync_inventory=True,
        )
        db.add(conn)

    db.commit()

    return RedirectResponse(
        f"{frontend_url}/integrations/shopify-callback?success=true&store={shop}"
    )
