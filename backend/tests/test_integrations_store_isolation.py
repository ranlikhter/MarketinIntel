"""
Security and tenant-isolation tests for store import endpoints.
"""

from tests.conftest import register_and_login, auth_headers
from database.models import ProductMonitored, User
from api.routes import integrations as integrations_routes
from services.auth_service import create_access_token


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


class _ShouldNotConstructWooIntegration:
    def __init__(self, *args, **kwargs):
        raise AssertionError("WooCommerceIntegration should not be constructed for blocked URLs")


class _ShouldNotConstructShopifyIntegration:
    def __init__(self, *args, **kwargs):
        raise AssertionError("ShopifyIntegration should not be constructed for blocked URLs")


def _issue_token_for_user(db, email: str) -> str:
    user = User(email=email, hashed_password="not-used")
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token({"sub": str(user.id)})


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


class TestIntegrationSecurity:
    def test_woocommerce_test_connection_requires_authentication(self, client):
        resp = client.post(
            "/api/integrations/test/woocommerce",
            json={
                "store_url": "https://demo-woo.example.com",
                "consumer_key": "ck_test",
                "consumer_secret": "cs_test",
            },
        )
        assert resp.status_code in (401, 403)

    def test_shopify_test_connection_requires_authentication(self, client):
        resp = client.post(
            "/api/integrations/test/shopify",
            json={
                "shop_url": "demo-store.myshopify.com",
                "access_token": "shpat_test",
            },
        )
        assert resp.status_code in (401, 403)

    def test_woocommerce_test_rejects_private_target_before_network_call(self, client, db, monkeypatch):
        token = _issue_token_for_user(db, "security-woo@example.com")
        monkeypatch.setattr(integrations_routes, "WooCommerceIntegration", _ShouldNotConstructWooIntegration)

        resp = client.post(
            "/api/integrations/test/woocommerce",
            json={
                "store_url": "http://127.0.0.1:8000",
                "consumer_key": "ck_test",
                "consumer_secret": "cs_test",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 400, resp.text
        assert "https" in resp.text or "public" in resp.text or "internal" in resp.text

    def test_shopify_test_rejects_non_shopify_host_before_network_call(self, client, db, monkeypatch):
        token = _issue_token_for_user(db, "security-shopify@example.com")
        monkeypatch.setattr(integrations_routes, "ShopifyIntegration", _ShouldNotConstructShopifyIntegration)

        resp = client.post(
            "/api/integrations/test/shopify",
            json={
                "shop_url": "127.0.0.1",
                "access_token": "shpat_test",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 400, resp.text
        assert "myshopify.com" in resp.text or "shop slug" in resp.text or "public" in resp.text

    def test_store_connection_rejects_private_woocommerce_url(self, client, db):
        token = _issue_token_for_user(db, "store-conn@example.com")

        resp = client.post(
            "/api/integrations/store-connections",
            json={
                "platform": "woocommerce",
                "store_url": "http://127.0.0.1:8000",
                "api_key": "ck_test",
                "api_secret": "cs_test",
                "sync_inventory": True,
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 400, resp.text
        assert "https" in resp.text or "public" in resp.text or "internal" in resp.text
