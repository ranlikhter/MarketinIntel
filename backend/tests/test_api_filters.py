"""
Integration Tests — Filters & Saved Views API (/api/filters/*)

Tests applying filters, saving views, listing, and deleting saved views.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User, ProductMonitored


def make_user(db, email="filter_api@x.com"):
    u = User(email=email, hashed_password="x", full_name="Filter API User")
    db.add(u); db.commit(); db.refresh(u)
    return u


def make_products(db, user, n=5):
    for i in range(n):
        p = ProductMonitored(
            user_id=user.id, title=f"Product {i}",
            brand="Acme" if i % 2 == 0 else "Rival",
            sku=f"FSKU-{i}", our_price=10.0 * (i + 1),
        )
        db.add(p)
    db.commit()


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    make_products(db, user)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestFiltersAuth:

    def test_apply_requires_auth(self, client):
        resp = client.post("/api/filters/apply", json={})
        assert resp.status_code in (401, 403)

    def test_saved_views_requires_auth(self, client):
        resp = client.get("/api/filters/saved-views")
        assert resp.status_code in (401, 403)


# ── Tests: Apply Filters ──────────────────────────────────────────────────────

class TestApplyFilters:

    def test_apply_empty_filter_returns_all(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/filters/apply", json={})
        assert resp.status_code == 200
        data = resp.json()
        products = data if isinstance(data, list) else data.get("products", data.get("items", []))
        assert len(products) >= 5

    def test_apply_brand_filter(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/filters/apply", json={"brand": "Acme"})
        assert resp.status_code == 200
        data = resp.json()
        products = data if isinstance(data, list) else data.get("products", data.get("items", []))
        assert all(p.get("brand", "").lower() == "acme" for p in products)

    def test_apply_price_range_filter(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/filters/apply", json={"price_range": {"min": 20.0, "max": 40.0}})
        assert resp.status_code == 200

    def test_apply_sku_filter(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/filters/apply", json={"sku": "FSKU-0"})
        assert resp.status_code == 200
        data = resp.json()
        products = data if isinstance(data, list) else data.get("products", data.get("items", []))
        assert len(products) >= 1


# ── Tests: Saved Views ────────────────────────────────────────────────────────

class TestSavedViews:

    SAVED_VIEW_PAYLOAD = {
        "name": "Acme Products",
        "filters": {"brand": "Acme"},
        "description": "All Acme brand products",
    }

    def test_list_saved_views_empty(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/filters/saved-views")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_saved_view(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/filters/saved-views", json=self.SAVED_VIEW_PAYLOAD)
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["name"] == "Acme Products"

    def test_saved_view_appears_in_list(self, authed_client):
        client, _ = authed_client
        client.post("/api/filters/saved-views", json=self.SAVED_VIEW_PAYLOAD)
        resp = client.get("/api/filters/saved-views")
        names = [v["name"] for v in resp.json()]
        assert "Acme Products" in names

    def test_delete_saved_view(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/filters/saved-views", json=self.SAVED_VIEW_PAYLOAD)
        view_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/filters/saved-views/{view_id}")
        assert del_resp.status_code in (200, 204)

    def test_saved_view_name_required(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/filters/saved-views", json={"filters": {}})
        assert resp.status_code == 422

    def test_saved_views_isolated_between_users(self, client, db):
        u1 = make_user(db, "fiso1@x.com")
        u2 = make_user(db, "fiso2@x.com")

        app.dependency_overrides[get_current_user] = lambda: u1
        client.post("/api/filters/saved-views", json={"name": "U1 View", "filters": {}})

        app.dependency_overrides[get_current_user] = lambda: u2
        resp = client.get("/api/filters/saved-views")
        names = [v["name"] for v in resp.json()]
        assert "U1 View" not in names

        app.dependency_overrides.pop(get_current_user, None)
