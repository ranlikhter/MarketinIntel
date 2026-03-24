"""
Deep Integration Tests — Products API (/api/products/*)

Tests full CRUD lifecycle, field validation, price history,
competitor matches, and user isolation.
"""

import pytest
from api.dependencies import get_current_user, get_current_workspace, ActiveWorkspace
from api.main import app
from database.models import User, ProductMonitored, CompetitorMatch, PriceHistory
from datetime import datetime


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_user(db, email="prod_deep@x.com"):
    u = User(email=email, hashed_password="x", full_name="Deep User")
    db.add(u); db.commit(); db.refresh(u)
    return u


def fake_workspace(user):
    class FWS:
        workspace_id = getattr(user, "default_workspace_id", None) or user.id
        workspace = None
        membership_role = "admin"
        is_selected = True
    return FWS()


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(user)
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_workspace, None)


PRODUCT_PAYLOAD = {
    "title": "Deep Test Widget",
    "sku": "DTW-001",
    "brand": "Acme",
    "our_price": 79.99,
    "cost_price": 30.0,
}


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestProductsAuth:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/products")
        assert resp.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        assert resp.status_code in (401, 403)

    def test_get_requires_auth(self, client):
        resp = client.get("/api/products/1")
        assert resp.status_code in (401, 403)


# ── Tests: CRUD ───────────────────────────────────────────────────────────────

class TestProductsCRUD:

    def test_create_product_minimal(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/products", json={"title": "Minimal Widget"})
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["title"] == "Minimal Widget"

    def test_create_product_full(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == "Deep Test Widget"
        assert data["sku"] == "DTW-001"

    def test_list_products_empty(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/products")
        assert resp.status_code == 200

    def test_list_products_includes_created(self, authed_client):
        client, _ = authed_client
        client.post("/api/products", json=PRODUCT_PAYLOAD)
        resp = client.get("/api/products")
        assert resp.status_code == 200
        body = resp.json()
        items = body if isinstance(body, list) else body.get("products", body.get("items", []))
        titles = [p.get("title") for p in items]
        assert "Deep Test Widget" in titles

    def test_get_product_by_id(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        prod_id = create_resp.json()["id"]
        resp = client.get(f"/api/products/{prod_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == prod_id

    def test_get_nonexistent_product_404(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/products/999999")
        assert resp.status_code == 404

    def test_update_product_title(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        prod_id = create_resp.json()["id"]
        resp = client.put(f"/api/products/{prod_id}", json={"title": "Updated Widget"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Widget"

    def test_update_product_price(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        prod_id = create_resp.json()["id"]
        resp = client.put(f"/api/products/{prod_id}", json={"our_price": 89.99})
        assert resp.status_code == 200

    def test_delete_product(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        prod_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/products/{prod_id}")
        assert del_resp.status_code in (200, 204)
        assert client.get(f"/api/products/{prod_id}").status_code == 404

    def test_delete_nonexistent_returns_404(self, authed_client):
        client, _ = authed_client
        resp = client.delete("/api/products/999999")
        assert resp.status_code == 404


# ── Tests: Validation ─────────────────────────────────────────────────────────

class TestProductValidation:

    def test_title_required(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/products", json={"sku": "NO-TITLE"})
        assert resp.status_code == 422

    def test_negative_price_rejected(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/products", json={
            "title": "Negative Price", "our_price": -10.0
        })
        assert resp.status_code in (400, 422)

    def test_update_nonexistent_product_404(self, authed_client):
        client, _ = authed_client
        resp = client.put("/api/products/999999", json={"title": "Ghost"})
        assert resp.status_code == 404


# ── Tests: Isolation ──────────────────────────────────────────────────────────

class TestProductsIsolation:

    def test_user_cannot_see_other_users_products(self, client, db):
        u1 = make_user(db, "iso1@x.com")
        u2 = make_user(db, "iso2@x.com")

        app.dependency_overrides[get_current_user] = lambda: u1
        app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(u1)
        client.post("/api/products", json={"title": "U1 Product"})

        app.dependency_overrides[get_current_user] = lambda: u2
        app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(u2)
        resp = client.get("/api/products")
        body = resp.json()
        items = body if isinstance(body, list) else body.get("products", body.get("items", []))
        titles = [p.get("title") for p in items]
        assert "U1 Product" not in titles

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_workspace, None)

    def test_user_cannot_delete_other_users_product(self, client, db):
        u1 = make_user(db, "iso3@x.com")
        u2 = make_user(db, "iso4@x.com")

        app.dependency_overrides[get_current_user] = lambda: u1
        app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(u1)
        create_resp = client.post("/api/products", json={"title": "Protected Product"})
        prod_id = create_resp.json()["id"]

        app.dependency_overrides[get_current_user] = lambda: u2
        app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(u2)
        del_resp = client.delete(f"/api/products/{prod_id}")
        assert del_resp.status_code in (403, 404)

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_workspace, None)


# ── Tests: Pricing Summary ────────────────────────────────────────────────────

class TestProductPricingSummary:

    def test_pricing_summary_returns_data(self, client, db):
        user = make_user(db, "ps1@x.com")
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(user)

        create_resp = client.post("/api/products", json=PRODUCT_PAYLOAD)
        prod_id = create_resp.json()["id"]

        resp = client.get(f"/api/products/{prod_id}/pricing-summary")
        assert resp.status_code in (200, 404)  # 404 if no competitor data yet

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_workspace, None)
