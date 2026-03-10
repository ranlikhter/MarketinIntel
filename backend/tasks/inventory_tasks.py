"""
Inventory Sync Background Tasks

Periodically fetches the latest product prices + stock levels from
connected Shopify / WooCommerce stores and updates ProductMonitored.

Celery beat schedule (add to celery_app.py conf_beat_schedule):
    "sync-store-inventory": {
        "task": "tasks.inventory_tasks.sync_all_store_inventory",
        "schedule": crontab(minute=0, hour="*/4"),   # every 4 hours
    },
"""

import logging
from datetime import datetime
from utils.time import utcnow

from celery_app import celery_app
from tasks.scraping_tasks import DatabaseTask
from database.models import ProductMonitored, StoreConnection, MyPriceHistory

logger = logging.getLogger(__name__)


@celery_app.task(base=DatabaseTask, bind=True)
def sync_all_store_inventory(self):
    """
    Sync inventory quantity + price for every active StoreConnection.
    Skips connections where sync_inventory=False.
    """
    connections = self.db.query(StoreConnection).filter(
        StoreConnection.is_active == True,
        StoreConnection.sync_inventory == True,
    ).all()

    logger.info(f"[InventorySync] {len(connections)} active store connection(s) found")
    synced_total = 0
    errors = []

    for conn in connections:
        try:
            count = _sync_connection(conn, self.db)
            synced_total += count
            conn.last_synced_at = utcnow()
            self.db.commit()
            logger.info(f"[InventorySync] {conn.platform}:{conn.store_url} → {count} products updated")
        except Exception as e:
            logger.error(f"[InventorySync] Failed for {conn.store_url}: {e}")
            errors.append(str(e))

    return {
        "synced": synced_total,
        "connections": len(connections),
        "errors": errors,
    }


@celery_app.task(base=DatabaseTask, bind=True)
def sync_single_connection(self, connection_id: int):
    """Sync a specific store connection by ID (triggered manually)."""
    conn = self.db.query(StoreConnection).filter(
        StoreConnection.id == connection_id,
    ).first()
    if not conn:
        return {"error": "Store connection not found"}

    try:
        count = _sync_connection(conn, self.db)
        conn.last_synced_at = utcnow()
        self.db.commit()
        return {"success": True, "synced": count}
    except Exception as e:
        logger.error(f"[InventorySync] Manual sync failed for {conn.store_url}: {e}")
        return {"error": str(e)}


def _sync_connection(conn: StoreConnection, db) -> int:
    """
    Pull products from one store and update matching ProductMonitored rows.
    Matches by SKU first, then by title (case-insensitive).
    Returns the number of records updated.
    """
    if conn.platform == "shopify":
        return _sync_shopify(conn, db)
    elif conn.platform == "woocommerce":
        return _sync_woocommerce(conn, db)
    else:
        raise ValueError(f"Unknown platform: {conn.platform}")


def _sync_shopify(conn: StoreConnection, db) -> int:
    from integrations.shopify_integration import ShopifyIntegration
    shop = ShopifyIntegration(
        shop_url=conn.store_url,
        access_token=conn.api_key,
    )
    products = shop.get_all_products(max_products=2000)
    return _apply_updates(products, conn.user_id, db)


def _sync_woocommerce(conn: StoreConnection, db) -> int:
    from integrations.woocommerce_integration import WooCommerceIntegration
    wc = WooCommerceIntegration(
        store_url=conn.store_url,
        consumer_key=conn.api_key or '',
        consumer_secret=conn.api_secret or '',
    )
    products = wc.get_all_products(max_products=2000)
    return _apply_updates(products, conn.user_id, db)


def _apply_updates(store_products: list, user_id: int, db) -> int:
    """
    Match store products to monitored products and update price + inventory.
    """
    count = 0
    # Build lookup maps for this user's products
    sku_map: dict[str, ProductMonitored] = {}
    title_map: dict[str, ProductMonitored] = {}

    monitored = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == user_id
    ).all()

    for p in monitored:
        if p.sku:
            sku_map[p.sku.strip().upper()] = p
        title_map[p.title.strip().lower()] = p

    for sp in store_products:
        sku = (sp.get('sku') or '').strip().upper()
        title = (sp.get('title') or '').strip().lower()
        price = sp.get('price')

        # Try SKU match first, then title
        matched: ProductMonitored | None = None
        if sku:
            matched = sku_map.get(sku)
        if matched is None and title:
            matched = title_map.get(title)

        if matched is None:
            continue

        changed = False
        if price is not None:
            try:
                new_price = float(price)
                if matched.my_price != new_price:
                    history = MyPriceHistory(
                        product_id=matched.id,
                        old_price=matched.my_price,
                        new_price=new_price,
                        note="store sync",
                    )
                    db.add(history)
                    matched.my_price = new_price
                    changed = True
            except (TypeError, ValueError):
                pass

        # inventory_quantity from store (WooCommerce returns stock_quantity)
        qty = sp.get('stock_quantity') or sp.get('inventory_quantity')
        if qty is not None:
            try:
                new_qty = int(qty)
                if matched.inventory_quantity != new_qty:
                    matched.inventory_quantity = new_qty
                    changed = True
            except (TypeError, ValueError):
                pass

        if changed:
            count += 1

    if count:
        db.commit()
    return count
