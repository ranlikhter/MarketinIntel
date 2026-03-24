"""
Integration Tests — Forecasting API (/api/forecasting/*)

Tests price history analysis, forecasting, seasonal patterns,
and user ownership validation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User, ProductMonitored, CompetitorMatch, PriceHistory
from datetime import datetime, timedelta


def make_user(db, email="forecast_api@x.com"):
    u = User(email=email, hashed_password="x")
    db.add(u); db.commit(); db.refresh(u)
    return u


def make_product(db, user, sku="FC1"):
    p = ProductMonitored(user_id=user.id, title="Forecast Product", sku=sku, our_price=100.0)
    db.add(p); db.commit(); db.refresh(p)
    return p


def seed_history(db, product, n=30):
    m = CompetitorMatch(
        product_id=product.id, user_id=product.user_id,
        title=product.title, price=90.0, stock_status="In Stock",
        source="amazon", url="https://amazon.com/dp/fc",
    )
    db.add(m); db.commit(); db.refresh(m)
    for i in range(n):
        db.add(PriceHistory(
            match_id=m.id, price=90.0 - (i * 0.3),
            timestamp=datetime.utcnow() - timedelta(days=i), in_stock=True,
        ))
    db.commit()
    return m


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestForecastingAuth:

    def test_history_requires_auth(self, client):
        resp = client.get("/api/forecasting/products/1/history")
        assert resp.status_code in (401, 403)

    def test_forecast_requires_auth(self, client):
        resp = client.get("/api/forecasting/products/1/forecast")
        assert resp.status_code in (401, 403)


# ── Tests: Price History ──────────────────────────────────────────────────────

class TestForecastingHistory:

    def test_history_unknown_product_returns_error(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/forecasting/products/999999/history")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "error" in resp.json() or "message" in resp.json()

    def test_history_own_product_returns_200(self, client, db):
        user = make_user(db, "fca2@x.com")
        product = make_product(db, user, sku="FCA2")
        seed_history(db, product)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get(f"/api/forecasting/products/{product.id}/history?days=30")
        assert resp.status_code == 200
        app.dependency_overrides.pop(get_current_user, None)

    def test_history_other_users_product_blocked(self, client, db):
        u1 = make_user(db, "fca3a@x.com")
        u2 = make_user(db, "fca3b@x.com")
        product = make_product(db, u1, sku="FCA3")
        app.dependency_overrides[get_current_user] = lambda: u2
        resp = client.get(f"/api/forecasting/products/{product.id}/history")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "error" in resp.json()
        app.dependency_overrides.pop(get_current_user, None)

    def test_history_days_validation(self, client, db):
        user = make_user(db, "fca4@x.com")
        product = make_product(db, user, sku="FCA4")
        app.dependency_overrides[get_current_user] = lambda: user
        # Too few days
        resp = client.get(f"/api/forecasting/products/{product.id}/history?days=1")
        assert resp.status_code == 422
        # Too many days
        resp = client.get(f"/api/forecasting/products/{product.id}/history?days=999")
        assert resp.status_code == 422
        app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Forecast ───────────────────────────────────────────────────────────

class TestForecastingForecast:

    def test_forecast_unknown_product(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/forecasting/products/999999/forecast")
        assert resp.status_code in (200, 404)

    def test_forecast_own_product_with_history(self, client, db):
        user = make_user(db, "fca5@x.com")
        product = make_product(db, user, sku="FCA5")
        seed_history(db, product, n=30)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get(f"/api/forecasting/products/{product.id}/forecast?days_ahead=7")
        assert resp.status_code == 200
        app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Seasonal Patterns ──────────────────────────────────────────────────

class TestForecastingSeasonal:

    def test_seasonal_own_product(self, client, db):
        user = make_user(db, "fca6@x.com")
        product = make_product(db, user, sku="FCA6")
        seed_history(db, product)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get(f"/api/forecasting/products/{product.id}/seasonal-patterns")
        assert resp.status_code == 200
        app.dependency_overrides.pop(get_current_user, None)
