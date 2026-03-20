"""
Security-focused tests for analytics endpoints.
"""

from tests.conftest import register_and_login, auth_headers
from database.models import ProductMonitored, User


class TestAnalyticsSecurity:
    def test_analytics_requires_authentication(self, client):
        resp = client.get("/api/analytics/products/1/trendline")
        assert resp.status_code in (401, 403)

        resp = client.post("/api/analytics/update")
        assert resp.status_code in (401, 403)

        resp = client.post("/api/analytics/snapshots")
        assert resp.status_code in (401, 403)

    def test_user_cannot_read_another_users_product_analytics(self, client, db):
        owner_token = register_and_login(client, email="analytics-owner@example.com")
        other_token = register_and_login(client, email="analytics-other@example.com")

        owner = db.query(User).filter(User.email == "analytics-owner@example.com").first()
        other = db.query(User).filter(User.email == "analytics-other@example.com").first()
        assert owner and other

        owner_product = ProductMonitored(title="Owner Product", user_id=owner.id)
        other_product = ProductMonitored(title="Other Product", user_id=other.id)
        db.add_all([owner_product, other_product])
        db.commit()
        db.refresh(owner_product)
        db.refresh(other_product)

        # Owner can request their own analytics endpoint (may return empty data, but should be authorized).
        own_resp = client.get(
            f"/api/analytics/products/{owner_product.id}/trendline",
            headers=auth_headers(owner_token),
        )
        assert own_resp.status_code == 200, own_resp.text

        # Owner must not access another user's product analytics.
        foreign_resp = client.get(
            f"/api/analytics/products/{other_product.id}/trendline",
            headers=auth_headers(owner_token),
        )
        assert foreign_resp.status_code == 404

        # Symmetry check: other user cannot access owner's product either.
        reverse_resp = client.get(
            f"/api/analytics/products/{owner_product.id}/compare",
            headers=auth_headers(other_token),
        )
        assert reverse_resp.status_code == 404
