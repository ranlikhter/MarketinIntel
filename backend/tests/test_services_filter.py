"""
Unit Tests — FilterService

Tests brand, SKU, price range, competition level, and search filters.
"""

import pytest
from database.models import User, ProductMonitored, CompetitorMatch
from services.filter_service import FilterService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(db, email="filter@x.com"):
    u = User(email=email, hashed_password="x", full_name="Filter User")
    db.add(u); db.commit(); db.refresh(u)
    return u


def make_product(db, user, title="Widget", brand="Acme", sku="W1", price=50.0):
    p = ProductMonitored(
        user_id=user.id, title=title, brand=brand,
        sku=sku, our_price=price,
    )
    db.add(p); db.commit(); db.refresh(p)
    return p


def make_match(db, product, price=45.0, in_stock=True):
    m = CompetitorMatch(
        product_id=product.id, user_id=product.user_id,
        title=product.title, price=price,
        stock_status="In Stock" if in_stock else "Out of Stock",
        source="amazon", url="https://amazon.com/dp/test",
    )
    db.add(m); db.commit(); db.refresh(m)
    return m


# ── Tests: Brand Filter ───────────────────────────────────────────────────────

class TestBrandFilter:

    def test_filter_by_exact_brand(self, db):
        user = make_user(db, "bf1@x.com")
        make_product(db, user, title="A", brand="Acme", sku="A1")
        make_product(db, user, title="B", brand="Rival", sku="B1")
        svc = FilterService(db, user)
        query = svc.apply_filters({"brand": "Acme"})
        results = query.all()
        assert all(p.brand == "Acme" for p in results)
        assert len(results) == 1

    def test_filter_brand_case_insensitive(self, db):
        user = make_user(db, "bf2@x.com")
        make_product(db, user, title="C", brand="ACME", sku="C1")
        svc = FilterService(db, user)
        query = svc.apply_filters({"brand": "acme"})
        assert len(query.all()) == 1

    def test_filter_brand_partial_match(self, db):
        user = make_user(db, "bf3@x.com")
        make_product(db, user, title="D", brand="Acme Corp", sku="D1")
        svc = FilterService(db, user)
        query = svc.apply_filters({"brand": "Acme"})
        assert len(query.all()) >= 1

    def test_filter_brand_no_match(self, db):
        user = make_user(db, "bf4@x.com")
        make_product(db, user, title="E", brand="Rival", sku="E1")
        svc = FilterService(db, user)
        query = svc.apply_filters({"brand": "NonExistent"})
        assert len(query.all()) == 0


# ── Tests: SKU Filter ─────────────────────────────────────────────────────────

class TestSKUFilter:

    def test_filter_by_exact_sku(self, db):
        user = make_user(db, "sf1@x.com")
        make_product(db, user, title="F", sku="EXACT-SKU-001")
        make_product(db, user, title="G", sku="OTHER-SKU-002")
        svc = FilterService(db, user)
        query = svc.apply_filters({"sku": "EXACT-SKU-001"})
        results = query.all()
        assert len(results) == 1
        assert results[0].sku == "EXACT-SKU-001"

    def test_filter_sku_partial(self, db):
        user = make_user(db, "sf2@x.com")
        make_product(db, user, title="H", sku="ABC-001")
        make_product(db, user, title="I", sku="ABC-002")
        make_product(db, user, title="J", sku="XYZ-003")
        svc = FilterService(db, user)
        query = svc.apply_filters({"sku": "ABC"})
        assert len(query.all()) == 2


# ── Tests: Price Range Filter ─────────────────────────────────────────────────

class TestPriceRangeFilter:

    def test_filter_by_min_price(self, db):
        user = make_user(db, "pr1@x.com")
        make_product(db, user, title="Cheap", sku="CH1", price=10.0)
        make_product(db, user, title="Expensive", sku="EX1", price=100.0)
        svc = FilterService(db, user)
        query = svc.apply_filters({"price_range": {"min": 50.0}})
        results = query.all()
        assert all(p.our_price >= 50.0 for p in results if p.our_price)

    def test_filter_by_max_price(self, db):
        user = make_user(db, "pr2@x.com")
        make_product(db, user, title="Budget", sku="BU1", price=20.0)
        make_product(db, user, title="Premium", sku="PR1", price=200.0)
        svc = FilterService(db, user)
        query = svc.apply_filters({"price_range": {"max": 50.0}})
        results = query.all()
        assert all(p.our_price <= 50.0 for p in results if p.our_price)

    def test_filter_by_price_range(self, db):
        user = make_user(db, "pr3@x.com")
        make_product(db, user, title="Low", sku="LO1", price=5.0)
        make_product(db, user, title="Mid", sku="MI1", price=50.0)
        make_product(db, user, title="High", sku="HI1", price=500.0)
        svc = FilterService(db, user)
        query = svc.apply_filters({"price_range": {"min": 20.0, "max": 100.0}})
        results = query.all()
        prices = [p.our_price for p in results if p.our_price]
        assert all(20.0 <= p <= 100.0 for p in prices)


# ── Tests: Combined Filters ───────────────────────────────────────────────────

class TestCombinedFilters:

    def test_brand_and_price_combined(self, db):
        user = make_user(db, "cf1@x.com")
        make_product(db, user, title="Acme Cheap", brand="Acme", sku="AC1", price=20.0)
        make_product(db, user, title="Acme Expensive", brand="Acme", sku="AC2", price=200.0)
        make_product(db, user, title="Rival Cheap", brand="Rival", sku="RC1", price=20.0)
        svc = FilterService(db, user)
        query = svc.apply_filters({
            "brand": "Acme",
            "price_range": {"max": 50.0},
        })
        results = query.all()
        assert len(results) == 1
        assert results[0].sku == "AC1"

    def test_no_filters_returns_all_user_products(self, db):
        user = make_user(db, "cf2@x.com")
        for i in range(5):
            make_product(db, user, title=f"Prod {i}", sku=f"P{i}")
        svc = FilterService(db, user)
        query = svc.apply_filters({})
        assert len(query.all()) == 5

    def test_filters_scoped_to_user(self, db):
        user1 = make_user(db, "cf3a@x.com")
        user2 = make_user(db, "cf3b@x.com")
        make_product(db, user1, title="U1 Product", brand="Acme", sku="U1P")
        make_product(db, user2, title="U2 Product", brand="Acme", sku="U2P")
        svc = FilterService(db, user1)
        query = svc.apply_filters({"brand": "Acme"})
        results = query.all()
        assert all(p.user_id == user1.id for p in results)
