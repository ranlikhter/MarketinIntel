"""
Security and tenant-isolation tests for store import endpoints.
"""

from tests.conftest import register_and_login, auth_headers
from database.models import ProductMonitored, User
from api.routes import integrations as integrations_routes


class _DummyShopifyIntegration:
    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url
        self.access_token = access_token

    def test_connection(self):
        return {"success": True}

    def get_all_products(self, max_products: int = 100):
        return [
            {
                "title": "Shared Catalog Item",
                "brand": "BrandX",
                "sku": "SKU-SHARED-001",
                "image_url": "https://example.com/item.jpg",
            }
        ]


class _DummyWooIntegration:
    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        self.store_url = store_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

    def test_connection(self):
        return {"success": True}

    def get_all_products(self, max_products: int = 100):
        return [
            {
                "title": "Woo Item",
                "brand": "WooBrand",
                "sku": "SKU-WOO-001",
                "image_url": "https://example.com/woo.jpg",
            }
        ]


class TestStoreImportIsolation:
    def test_shopify_import_requires_authentication(self, client):
        resp = client.post(
            "/api/integrations/import/shopify",
            json={
                "shop_url": "demo-store.myshopify.com",
                "access_token": "shpat_test",
                "import_limit": 10,
            },
        )
        assert resp.status_code in (401, 403)

    def test_shopify_import_deduplicates_per_user_not_globally(self, client, db, monkeypatch):
        monkeypatch.setattr(integrations_routes, "ShopifyIntegration", _DummyShopifyIntegration)

        token_a = register_and_login(client, email="shop-a@example.com")
        token_b = register_and_login(client, email="shop-b@example.com")

        payload = {
            "shop_url": "demo-store.myshopify.com",
            "access_token": "shpat_test",
            "import_limit": 10,
        }

        r1 = client.post("/api/integrations/import/shopify", json=payload, headers=auth_headers(token_a))
        r2 = client.post("/api/integrations/import/shopify", json=payload, headers=auth_headers(token_b))
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert r1.json()["products_imported"] == 1
        assert r2.json()["products_imported"] == 1

        rows = db.query(ProductMonitored).filter(ProductMonitored.sku == "SKU-SHARED-001").all()
        assert len(rows) == 2
        assert len({row.user_id for row in rows}) == 2

    def test_woocommerce_import_sets_user_id_and_skips_duplicates_for_same_user(self, client, db, monkeypatch):
        monkeypatch.setattr(integrations_routes, "WooCommerceIntegration", _DummyWooIntegration)

        token = register_and_login(client, email="woo-owner@example.com")

        payload = {
            "store_url": "https://demo-woo.example.com",
            "consumer_key": "ck_test",
            "consumer_secret": "cs_test",
            "import_limit": 10,
        }

        first = client.post("/api/integrations/import/woocommerce", json=payload, headers=auth_headers(token))
        second = client.post("/api/integrations/import/woocommerce", json=payload, headers=auth_headers(token))
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert first.json()["products_imported"] == 1
        assert second.json()["products_skipped"] >= 1

        owner = db.query(User).filter(User.email == "woo-owner@example.com").first()
        assert owner is not None

        imported = db.query(ProductMonitored).filter(ProductMonitored.sku == "SKU-WOO-001").all()
        assert len(imported) == 1
        assert imported[0].user_id == owner.id
