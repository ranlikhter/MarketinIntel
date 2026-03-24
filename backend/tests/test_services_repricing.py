"""
Unit Tests — RepricingService

Tests all 5 repricing strategies and helper methods in isolation,
using in-memory SQLite via the shared conftest fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch
from database.models import User, ProductMonitored, CompetitorMatch
from services.repricing_service import RepricingService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(db, email="reprice@example.com"):
    user = User(email=email, hashed_password="x", full_name="Repricer")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_product(db, user, title="Widget", our_price=50.0, sku="W1"):
    p = ProductMonitored(
        user_id=user.id,
        title=title,
        our_price=our_price,
        sku=sku,
        cost_price=20.0,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_match(db, product, price=40.0, stock_status="In Stock"):
    m = CompetitorMatch(
        product_id=product.id,
        user_id=product.user_id,
        title=product.title,
        price=price,
        stock_status=stock_status,
        source="amazon",
        url="https://amazon.com/dp/test",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ── Tests: match_lowest ───────────────────────────────────────────────────────

class TestMatchLowest:

    def test_returns_suggestion_for_product_with_competitor(self, db):
        user = make_user(db, "ml1@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=35.00)
        svc = RepricingService(db, user)
        result = svc.match_lowest_competitor([prod.id])
        assert result["action"] == "match_lowest"
        assert result["products_processed"] == 1
        assert result["suggestions"][0]["suggested_price"] == 35.00

    def test_applies_margin_amount(self, db):
        user = make_user(db, "ml2@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=40.00)
        svc = RepricingService(db, user)
        result = svc.match_lowest_competitor([prod.id], margin_amount=2.0)
        assert result["suggestions"][0]["suggested_price"] == 38.00

    def test_applies_margin_pct(self, db):
        user = make_user(db, "ml3@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=100.00)
        svc = RepricingService(db, user)
        result = svc.match_lowest_competitor([prod.id], margin_pct=10.0)
        assert result["suggestions"][0]["suggested_price"] == 90.00

    def test_skips_product_with_no_competitors(self, db):
        user = make_user(db, "ml4@x.com")
        prod = make_product(db, user)
        svc = RepricingService(db, user)
        result = svc.match_lowest_competitor([prod.id])
        assert result["products_processed"] == 0
        assert result["suggestions"] == []

    def test_never_goes_below_zero(self, db):
        user = make_user(db, "ml5@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=0.50)
        svc = RepricingService(db, user)
        result = svc.match_lowest_competitor([prod.id], margin_amount=5.00)
        assert result["suggestions"][0]["suggested_price"] == 0.01

    def test_ignores_other_users_products(self, db):
        user1 = make_user(db, "ml_u1@x.com")
        user2 = make_user(db, "ml_u2@x.com")
        prod = make_product(db, user2)
        make_match(db, prod, price=30.00)
        svc = RepricingService(db, user1)
        result = svc.match_lowest_competitor([prod.id])
        assert result["products_processed"] == 0

    def test_multiple_products(self, db):
        user = make_user(db, "ml6@x.com")
        p1 = make_product(db, user, title="A", sku="A1")
        p2 = make_product(db, user, title="B", sku="B1")
        make_match(db, p1, price=20.00)
        make_match(db, p2, price=30.00)
        svc = RepricingService(db, user)
        result = svc.match_lowest_competitor([p1.id, p2.id])
        assert result["products_processed"] == 2
        prices = {s["product_id"]: s["suggested_price"] for s in result["suggestions"]}
        assert prices[p1.id] == 20.00
        assert prices[p2.id] == 30.00


# ── Tests: undercut ───────────────────────────────────────────────────────────

class TestUndercut:

    def test_default_undercut_50_cents(self, db):
        user = make_user(db, "uc1@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=50.00)
        svc = RepricingService(db, user)
        result = svc.undercut_all_competitors([prod.id])
        assert result["suggestions"][0]["suggested_price"] == 49.50

    def test_undercut_by_fixed_amount(self, db):
        user = make_user(db, "uc2@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=100.00)
        svc = RepricingService(db, user)
        result = svc.undercut_all_competitors([prod.id], undercut_amount=5.00)
        assert result["suggestions"][0]["suggested_price"] == 95.00

    def test_undercut_by_percentage(self, db):
        user = make_user(db, "uc3@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=200.00)
        svc = RepricingService(db, user)
        result = svc.undercut_all_competitors([prod.id], undercut_pct=5.0)
        assert result["suggestions"][0]["suggested_price"] == 190.00

    def test_undercut_never_negative(self, db):
        user = make_user(db, "uc4@x.com")
        prod = make_product(db, user)
        make_match(db, prod, price=0.10)
        svc = RepricingService(db, user)
        result = svc.undercut_all_competitors([prod.id], undercut_amount=10.00)
        assert result["suggestions"][0]["suggested_price"] == 0.01


# ── Tests: margin_based ───────────────────────────────────────────────────────

class TestMarginBased:

    def test_calculates_margin_from_cost(self, db):
        user = make_user(db, "mb1@x.com")
        prod = make_product(db, user, our_price=50.0)
        prod.cost_price = 20.0
        db.commit()
        make_match(db, prod, price=45.00)
        svc = RepricingService(db, user)
        result = svc.margin_based_pricing([prod.id], target_margin_pct=30.0)
        assert result["products_processed"] == 1
        s = result["suggestions"][0]
        # At 30% margin on $20 cost: price = 20 / (1 - 0.30) ≈ 28.57
        assert s["suggested_price"] > 20.0

    def test_skips_products_without_cost(self, db):
        user = make_user(db, "mb2@x.com")
        prod = make_product(db, user)
        prod.cost_price = None
        db.commit()
        svc = RepricingService(db, user)
        result = svc.margin_based_pricing([prod.id], target_margin_pct=20.0)
        assert result["products_processed"] == 0


# ── Tests: MAP protection ─────────────────────────────────────────────────────

class TestMapProtected:

    def test_suggests_map_price(self, db):
        user = make_user(db, "map1@x.com")
        prod = make_product(db, user, our_price=80.0)
        make_match(db, prod, price=60.0)
        svc = RepricingService(db, user)
        result = svc.map_protected_pricing([prod.id], map_price=75.0)
        assert result["products_processed"] == 1
        assert result["suggestions"][0]["suggested_price"] >= 75.0

    def test_raises_when_below_map(self, db):
        user = make_user(db, "map2@x.com")
        prod = make_product(db, user, our_price=60.0)
        make_match(db, prod, price=55.0)
        svc = RepricingService(db, user)
        result = svc.map_protected_pricing([prod.id], map_price=65.0)
        # Suggested price must be >= MAP
        assert result["suggestions"][0]["suggested_price"] >= 65.0
