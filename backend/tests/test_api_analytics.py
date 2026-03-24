"""
Integration Tests — Analytics API (/api/analytics/*)

Tests trendline, comparison, and alert analytics endpoints
with user isolation and date range validation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User, ProductMonitored, CompetitorMatch, PriceHistory
from datetime import datetime, timedelta


def make_user(db, email="analytics@x.com"):
    u = User(email=email, hashed_password="x")
    db.add(u); db.commit(); db.refresh(u)
    return u


def make_product_with_history(db, user, price=50.0):
    p = ProductMonitored(user_id=user.id, title="Analytics Widget", sku="AW1", our_price=price)
    db.add(p); db.commit(); db.refresh(p)
    m = CompetitorMatch(
        product_id=p.id, user_id=user.id,
        title=p.title, price=45.0, stock_status="In Stock",
        source="amazon", url="https://amazon.com/dp/test",
    )
    db.add(m); db.commit(); db.refresh(m)
    for i in range(10):
        db.add(PriceHistory(
            match_id=m.id, price=45.0 - i * 0.5,
            timestamp=datetime.utcnow() - timedelta(days=i), in_stock=True,
        ))
    db.commit()
    return p, m


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestAnalyticsAuth:

    def test_trendline_requires_auth(self, client):
        resp = client.get("/api/analytics/products/1/trendline")
        assert resp.status_code in (401, 403)


# ── Tests: Trendline ──────────────────────────────────────────────────────────

class TestTrendline:

    def test_trendline_unknown_product_404(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/analytics/products/999999/trendline")
        assert resp.status_code == 404

    def test_trendline_for_own_product(self, client, db):
        user = make_user(db, "an2@x.com")
        product, _ = make_product_with_history(db, user)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get(f"/api/analytics/products/{product.id}/trendline?days=30")
        assert resp.status_code == 200
        app.dependency_overrides.pop(get_current_user, None)

    def test_trendline_other_user_product_404(self, client, db):
        u1 = make_user(db, "an3a@x.com")
        u2 = make_user(db, "an3b@x.com")
        product, _ = make_product_with_history(db, u1)
        app.dependency_overrides[get_current_user] = lambda: u2
        resp = client.get(f"/api/analytics/products/{product.id}/trendline")
        assert resp.status_code == 404
        app.dependency_overrides.pop(get_current_user, None)

    def test_trendline_days_parameter(self, client, db):
        user = make_user(db, "an4@x.com")
        product, _ = make_product_with_history(db, user)
        app.dependency_overrides[get_current_user] = lambda: user
        for days in [7, 30, 90]:
            resp = client.get(f"/api/analytics/products/{product.id}/trendline?days={days}")
            assert resp.status_code == 200
        app.dependency_overrides.pop(get_current_user, None)

    def test_trendline_invalid_days_rejected(self, client, db):
        user = make_user(db, "an5@x.com")
        product, _ = make_product_with_history(db, user)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get(f"/api/analytics/products/{product.id}/trendline?days=0")
        assert resp.status_code == 422
        app.dependency_overrides.pop(get_current_user, None)
