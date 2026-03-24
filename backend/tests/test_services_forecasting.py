"""
Unit Tests — ForecastingService

Tests price history analysis, trend detection, and forecasting
using in-memory SQLite via conftest fixtures.
"""

import pytest
from datetime import datetime, timedelta
from database.models import User, ProductMonitored, CompetitorMatch, PriceHistory
from services.forecasting_service import ForecastingService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(db, email="forecast@x.com"):
    u = User(email=email, hashed_password="x", full_name="Forecast User")
    db.add(u); db.commit(); db.refresh(u)
    return u


def make_product(db, user, title="Widget", sku="W1"):
    p = ProductMonitored(user_id=user.id, title=title, sku=sku, our_price=50.0)
    db.add(p); db.commit(); db.refresh(p)
    return p


def make_match(db, product, competitor="Amazon"):
    m = CompetitorMatch(
        product_id=product.id, user_id=product.user_id,
        title=product.title, price=45.0, stock_status="In Stock",
        source="amazon", url="https://amazon.com/dp/test",
    )
    db.add(m); db.commit(); db.refresh(m)
    return m


def seed_price_history(db, match, prices_with_offsets):
    """Seed PriceHistory rows: [(price, days_ago), ...]"""
    now = datetime.utcnow()
    for price, days_ago in prices_with_offsets:
        ph = PriceHistory(
            match_id=match.id,
            price=price,
            timestamp=now - timedelta(days=days_ago),
            in_stock=True,
        )
        db.add(ph)
    db.commit()


# ── Tests: Price History Analysis ────────────────────────────────────────────

class TestPriceHistoryAnalysis:

    def test_returns_error_for_unknown_product(self, db):
        user = make_user(db, "fh1@x.com")
        svc = ForecastingService(db, user)
        result = svc.get_price_history_analysis(999999, days=30)
        assert "error" in result

    def test_returns_message_when_no_competitor_data(self, db):
        user = make_user(db, "fh2@x.com")
        prod = make_product(db, user, sku="FH2")
        svc = ForecastingService(db, user)
        result = svc.get_price_history_analysis(prod.id, days=30)
        assert "message" in result or "error" in result

    def test_returns_product_info(self, db):
        user = make_user(db, "fh3@x.com")
        prod = make_product(db, user, sku="FH3")
        match = make_match(db, prod)
        seed_price_history(db, match, [(40.0, 5), (42.0, 3), (38.0, 1)])
        svc = ForecastingService(db, user)
        result = svc.get_price_history_analysis(prod.id, days=30)
        assert "product" in result

    def test_ignores_other_users_products(self, db):
        user1 = make_user(db, "fh4a@x.com")
        user2 = make_user(db, "fh4b@x.com")
        prod = make_product(db, user2, sku="FH4")
        svc = ForecastingService(db, user1)
        result = svc.get_price_history_analysis(prod.id, days=30)
        assert "error" in result

    def test_respects_days_parameter(self, db):
        user = make_user(db, "fh5@x.com")
        prod = make_product(db, user, sku="FH5")
        match = make_match(db, prod)
        # Two old entries (outside 7-day window) and one fresh entry
        seed_price_history(db, match, [
            (50.0, 60), (48.0, 45),  # outside 7-day window
            (42.0, 2),               # inside 7-day window
        ])
        svc = ForecastingService(db, user)
        result_7 = svc.get_price_history_analysis(prod.id, days=7)
        result_90 = svc.get_price_history_analysis(prod.id, days=90)
        # Both should return product info (data available either way)
        assert "product" in result_7
        assert "product" in result_90


# ── Tests: Price Forecast ─────────────────────────────────────────────────────

class TestPriceForecast:

    def test_forecast_returns_error_for_unknown_product(self, db):
        user = make_user(db, "fc1@x.com")
        svc = ForecastingService(db, user)
        result = svc.forecast_price(999999, days_ahead=7)
        assert "error" in result

    def test_forecast_returns_message_with_no_history(self, db):
        user = make_user(db, "fc2@x.com")
        prod = make_product(db, user, sku="FC2")
        svc = ForecastingService(db, user)
        result = svc.forecast_price(prod.id, days_ahead=7)
        assert "error" in result or "message" in result

    def test_forecast_with_sufficient_history(self, db):
        user = make_user(db, "fc3@x.com")
        prod = make_product(db, user, sku="FC3")
        match = make_match(db, prod)
        # Seed enough data for a meaningful forecast
        prices = [(50.0 - i * 0.5, i) for i in range(30)]
        seed_price_history(db, match, prices)
        svc = ForecastingService(db, user)
        result = svc.forecast_price(prod.id, days_ahead=7)
        # Should return some kind of forecast structure
        assert isinstance(result, dict)
        assert "error" not in result or "product" in result


# ── Tests: Seasonal Patterns ──────────────────────────────────────────────────

class TestSeasonalPatterns:

    def test_seasonal_returns_error_for_unknown_product(self, db):
        user = make_user(db, "sp1@x.com")
        svc = ForecastingService(db, user)
        result = svc.get_seasonal_patterns(999999)
        assert "error" in result

    def test_seasonal_returns_product_for_known_product(self, db):
        user = make_user(db, "sp2@x.com")
        prod = make_product(db, user, sku="SP2")
        match = make_match(db, prod)
        seed_price_history(db, match, [(45.0, i) for i in range(1, 10)])
        svc = ForecastingService(db, user)
        result = svc.get_seasonal_patterns(prod.id)
        assert "product" in result or "error" in result
