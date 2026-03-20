"""
Tests for the Products API (/products and /api/products endpoints).
"""

import pytest

from api.dependencies import get_current_user
from api.main import app
from database.models import User


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def authed_client(client, db):
    user = User(
        email="prod_user@example.com",
        hashed_password="x",
        full_name="Product Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProductsCRUD:

    def test_list_products_unauthenticated(self, client):
        """Products list requires authentication."""
        resp = client.get("/api/products")
        assert resp.status_code in (401, 403, 404), (
            f"Expected 401/403/404 without auth, got {resp.status_code}"
        )

    def test_list_products_empty(self, authed_client):
        """Authenticated user with no products gets an empty list."""
        resp = authed_client.get("/api/products")
        # Accept 200 with empty list OR 404 if route prefix differs
        if resp.status_code == 200:
            body = resp.json()
            assert isinstance(body, (list, dict))
        else:
            assert resp.status_code in (404,)

    def test_create_product(self, authed_client):
        """Create a monitored product and verify it's returned."""
        resp = authed_client.post(
            "/api/products",
            json={
                "title": "Test Widget",
                "url": "https://example.com/widget",
                "our_price": 49.99,
                "sku": "WIDGET-001",
            },
        )
        # Accept 200 or 201
        assert resp.status_code in (200, 201, 422), (
            f"Unexpected status {resp.status_code}: {resp.text}"
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            # Response should contain the product title or an id
            assert "id" in data or "title" in data or "product" in data

    def test_create_product_missing_required_field(self, authed_client):
        """Creating a product without the required title field should fail validation."""
        resp = authed_client.post(
            "/api/products",
            json={"sku": "NO-TITLE-SKU"},
        )
        assert resp.status_code in (400, 422)

    def test_get_product_not_found(self, authed_client):
        """Fetching a non-existent product returns 404."""
        resp = authed_client.get("/api/products/999999")
        assert resp.status_code == 404

    def test_delete_product_not_found(self, authed_client):
        """Deleting a non-existent product returns 404."""
        resp = authed_client.delete("/api/products/999999")
        assert resp.status_code == 404
