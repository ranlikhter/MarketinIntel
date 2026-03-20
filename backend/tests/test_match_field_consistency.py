"""
Regression tests for CompetitorMatch foreign key field usage.
"""

from database.models import ProductMonitored, CompetitorMatch, PriceAlert, User
from tests.conftest import register_and_login, auth_headers


class TestMatchFieldConsistency:
    def test_ai_pending_review_uses_monitored_product_id(self, client, db):
        token = register_and_login(client, email="pending-review@example.com")
        user = db.query(User).filter(User.email == "pending-review@example.com").first()
        assert user is not None

        product = ProductMonitored(title="Monitor Product", user_id=user.id)
        db.add(product)
        db.flush()

        match = CompetitorMatch(
            monitored_product_id=product.id,
            competitor_name="Amazon",
            competitor_url="https://example.com/product",
            competitor_product_title="Monitor Product Competitor",
            match_score=77.0,
            latest_price=19.99,
        )
        db.add(match)
        db.commit()

        resp = client.get(
            "/api/ai-matching/pending-review?min_score=50&max_score=85",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["success"] is True
        assert data["pending_count"] == 1
        assert data["matches"][0]["product_id"] == product.id

    def test_alert_check_uses_monitored_product_id(self, client, db):
        token = register_and_login(client, email="match-field@example.com")
        user = db.query(User).filter(User.email == "match-field@example.com").first()
        assert user is not None

        product = ProductMonitored(title="Alert Product", user_id=user.id)
        db.add(product)
        db.flush()

        alert = PriceAlert(
            product_id=product.id,
            alert_type="price_drop",
            threshold_pct=5.0,
            email="alerts@example.com",
            enabled=True,
            user_id=user.id,
        )
        db.add(alert)

        match = CompetitorMatch(
            monitored_product_id=product.id,
            competitor_name="Walmart",
            competitor_url="https://example.com/walmart-product",
            competitor_product_title="Alert Product Competitor",
            match_score=80.0,
            latest_price=25.0,
        )
        db.add(match)
        db.commit()

        resp = client.post("/api/alerts/check", headers=auth_headers(token))
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["success"] is True
        assert data["errors"] == 0
