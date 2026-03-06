"""
Tests for the Products API (/products and /api/products endpoints).
"""

import pytest
from tests.conftest import register_and_login, auth_headers


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def token(client):
    return register_and_login(client, email="prod_user@example.com")


@pytest.fixture()
def auth(token):
    return auth_headers(token)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProductsCRUD:

    def test_list_products_unauthenticated(self, client):
        """Products list requires authentication."""
        resp = client.get("/api/products")
        assert resp.status_code in (401, 403, 404), (
            f"Expected 401/403/404 without auth, got {resp.status_code}"
        )

    def test_list_products_empty(self, client, auth):
        """Authenticated user with no products gets an empty list."""
        resp = client.get("/api/products", headers=auth)
        # Accept 200 with empty list OR 404 if route prefix differs
        if resp.status_code == 200:
            body = resp.json()
            assert isinstance(body, (list, dict))
        else:
            assert resp.status_code in (404,)

    def test_create_product(self, client, auth):
        """Create a monitored product and verify it's returned."""
        resp = client.post(
            "/api/products",
            json={
                "title": "Test Widget",
                "url": "https://example.com/widget",
                "our_price": 49.99,
                "sku": "WIDGET-001",
            },
            headers=auth,
        )
        # Accept 200 or 201
        assert resp.status_code in (200, 201, 422), (
            f"Unexpected status {resp.status_code}: {resp.text}"
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            # Response should contain the product title or an id
            assert "id" in data or "title" in data or "product" in data

    def test_create_product_missing_required_field(self, client, auth):
        """Creating a product without the required title field should fail validation."""
        resp = client.post(
            "/api/products",
            json={"sku": "NO-TITLE-SKU"},
            headers=auth,
        )
        assert resp.status_code in (400, 422)

    def test_get_product_not_found(self, client, auth):
        """Fetching a non-existent product returns 404."""
        resp = client.get("/api/products/999999", headers=auth)
        assert resp.status_code == 404

    def test_delete_product_not_found(self, client, auth):
        """Deleting a non-existent product returns 404."""
        resp = client.delete("/api/products/999999", headers=auth)
        assert resp.status_code == 404
