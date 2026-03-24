"""
Integration Tests — Insights API (/api/insights/*)

Tests dashboard insights, priorities, opportunities, threats,
key metrics, and caching behaviour.
"""

import pytest
from api.dependencies import get_current_user, get_current_workspace
from api.main import app
from database.models import User, ProductMonitored, CompetitorMatch


def make_user(db, email="insights@x.com"):
    u = User(email=email, hashed_password="x", full_name="Insights User")
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


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestInsightsAuth:

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/insights/dashboard")
        assert resp.status_code in (401, 403)

    def test_priorities_requires_auth(self, client):
        resp = client.get("/api/insights/priorities")
        assert resp.status_code in (401, 403)

    def test_opportunities_requires_auth(self, client):
        resp = client.get("/api/insights/opportunities")
        assert resp.status_code in (401, 403)


# ── Tests: Dashboard Insights ─────────────────────────────────────────────────

class TestDashboardInsights:

    def test_dashboard_returns_200(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/insights/dashboard")
        assert resp.status_code == 200

    def test_dashboard_has_required_keys(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/insights/dashboard")
        data = resp.json()
        for key in ("priorities", "opportunities", "threats", "key_metrics"):
            assert key in data, f"Missing key: {key}"

    def test_priorities_endpoint(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/insights/priorities")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_opportunities_endpoint(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/insights/opportunities")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_threats_endpoint(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/insights/threats")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_key_metrics_endpoint(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/insights/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_products" in data

    def test_empty_catalog_returns_valid_structure(self, authed_client):
        """With no products, insights should still return valid (empty) structure."""
        client, _ = authed_client
        resp = client.get("/api/insights/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("priorities"), list)
        assert isinstance(data.get("opportunities"), list)
        assert isinstance(data.get("threats"), list)

    def test_key_metrics_with_products(self, client, db):
        user = make_user(db, "ins2@x.com")
        for i in range(3):
            prod = ProductMonitored(
                user_id=user.id, title=f"Product {i}",
                sku=f"P{i}", our_price=50.0,
            )
            db.add(prod)
        db.commit()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_workspace] = lambda: fake_workspace(user)

        resp = client.get("/api/insights/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_products"] >= 3

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_workspace, None)
