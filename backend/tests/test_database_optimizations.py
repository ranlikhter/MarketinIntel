from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import event

from api.dependencies import get_current_user
from api.main import app
from database.models import (
    CompetitorMatch,
    CompetitorWebsite,
    PriceAlert,
    PriceHistory,
    ProductMonitored,
    User,
)
from services.insights_service import InsightsService
from services.product_catalog_service import get_home_catalog_summary, get_product_summaries

@contextmanager
def count_select_queries(db):
    statements: list[str] = []
    connection = db.connection()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(connection, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", before_cursor_execute)


def seed_catalog(db, *, user: User, product_count: int = 3, matches_per_product: int = 4) -> None:
    now = datetime.utcnow()

    websites = [
        CompetitorWebsite(name="Amazon", base_url="https://amazon.example"),
        CompetitorWebsite(name="Walmart", base_url="https://walmart.example"),
    ]
    db.add_all(websites)
    db.flush()

    for product_idx in range(product_count):
        product = ProductMonitored(
            user_id=user.id,
            title=f"Product {product_idx + 1}",
            sku=f"SKU-{product_idx + 1}",
            brand="BrandCo",
            my_price=100 + (product_idx * 5),
            cost_price=70,
        )
        db.add(product)
        db.flush()

        db.add(
            PriceAlert(
                user_id=user.id,
                product_id=product.id,
                alert_type="price_drop",
                threshold_pct=5,
                email=user.email,
                enabled=True,
            )
        )

        for match_idx in range(matches_per_product):
            latest_price = 92 + product_idx + match_idx
            match = CompetitorMatch(
                monitored_product_id=product.id,
                competitor_name=f"Competitor {match_idx + 1}",
                competitor_url=f"https://competitor-{product_idx}-{match_idx}.example/item",
                competitor_product_title=f"Product {product_idx + 1} Variant {match_idx + 1}",
                competitor_website_id=websites[match_idx % len(websites)].id,
                latest_price=latest_price,
                stock_status="In Stock" if match_idx != 0 else "Out of Stock",
                created_at=now - timedelta(days=match_idx + 1),
                last_scraped_at=now - timedelta(hours=match_idx * 6),
                match_score=96,
            )
            db.add(match)
            db.flush()

            db.add_all(
                [
                    PriceHistory(
                        match_id=match.id,
                        price=105 + product_idx + match_idx,
                        in_stock=True,
                        timestamp=now - timedelta(days=8),
                    ),
                    PriceHistory(
                        match_id=match.id,
                        price=98 + product_idx + match_idx,
                        in_stock=True,
                        timestamp=now - timedelta(days=3),
                    ),
                    PriceHistory(
                        match_id=match.id,
                        price=latest_price,
                        in_stock=(match_idx != 0),
                        shipping_cost=4.99,
                        total_price=latest_price + 4.99,
                        discount_pct=8,
                        was_price=latest_price + 10,
                        promotion_label="Spring sale",
                        timestamp=now - timedelta(hours=match_idx + 1),
                    ),
                ]
            )

    db.commit()


class TestDatabaseOptimizations:
    def test_product_summaries_use_fixed_query_count(self, db):
        user = User(email="perf-products@example.com", hashed_password="x", full_name="Perf User")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=4, matches_per_product=3)
        db.refresh(user)

        with count_select_queries(db) as statements:
            summaries = get_product_summaries(db, user_id=user.id, limit=50, offset=0)

        assert len(summaries) == 4
        assert len(statements) <= 4

    def test_home_summary_uses_small_query_plan(self, db):
        user = User(email="perf-home@example.com", hashed_password="x", full_name="Perf Home")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=3, matches_per_product=2)
        db.refresh(user)

        with count_select_queries(db) as statements:
            summary = get_home_catalog_summary(db, user_id=user.id, recent_limit=6)

        assert summary["total_products"] == 3
        assert summary["total_matches"] == 6
        assert len(summary["recent_products"]) == 3
        assert len(statements) <= 7

    def test_insights_dashboard_reuses_single_catalog_snapshot(self, db):
        user = User(email="perf-insights@example.com", hashed_password="x", full_name="Perf Insights")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=3, matches_per_product=4)
        db.refresh(user)

        service = InsightsService(db, user)

        with count_select_queries(db) as statements:
            payload = service.get_dashboard_insights()

        assert payload["key_metrics"]["total_products"] == 3
        assert "priorities" in payload
        assert "opportunities" in payload
        assert "threats" in payload
        assert len(statements) <= 6

    def test_products_summary_endpoint_returns_user_scoped_counts(self, client, db):
        user = User(
            email="summary-user@example.com",
            hashed_password="x",
            full_name="Summary User",
        )
        other_user = User(
            email="other-user@example.com",
            hashed_password="x",
            full_name="Other User",
        )
        db.add_all([user, other_user])
        db.commit()
        db.refresh(user)
        db.refresh(other_user)

        seed_catalog(db, user=user, product_count=2, matches_per_product=2)
        seed_catalog(db, user=other_user, product_count=1, matches_per_product=1)

        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = client.get("/api/products/summary")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        data = response.json()
        assert data["total_products"] == 2
        assert data["total_matches"] == 4
        assert len(data["recent_products"]) == 2
