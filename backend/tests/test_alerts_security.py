"""
Security-focused tests for alert execution endpoints.
"""

from database.models import ProductMonitored, PriceAlert, User
from tests.conftest import register_and_login, auth_headers


class TestAlertsSecurity:
    def test_check_alerts_requires_auth(self, client):
        resp = client.post("/api/alerts/check")
        assert resp.status_code in (401, 403)

    def test_test_alert_requires_auth(self, client):
        resp = client.post("/api/alerts/test/1")
        assert resp.status_code in (401, 403)

    def test_check_alerts_is_scoped_to_current_user(self, client, db):
        owner_token = register_and_login(client, email="alerts-owner@example.com")
        other_token = register_and_login(client, email="alerts-other@example.com")

        owner = db.query(User).filter(User.email == "alerts-owner@example.com").first()
        other = db.query(User).filter(User.email == "alerts-other@example.com").first()
        assert owner is not None
        assert other is not None

        owner_product = ProductMonitored(title="Owner Product", user_id=owner.id)
        other_product = ProductMonitored(title="Other Product", user_id=other.id)
        db.add_all([owner_product, other_product])
        db.flush()

        db.add_all([
            PriceAlert(
                user_id=owner.id,
                product_id=owner_product.id,
                alert_type="price_drop",
                threshold_pct=5.0,
                email="alerts-owner@example.com",
                enabled=True,
            ),
            PriceAlert(
                user_id=other.id,
                product_id=other_product.id,
                alert_type="price_drop",
                threshold_pct=5.0,
                email="alerts-other@example.com",
                enabled=True,
            ),
        ])
        db.commit()

        owner_resp = client.post("/api/alerts/check", headers=auth_headers(owner_token))
        assert owner_resp.status_code == 200, owner_resp.text
        assert owner_resp.json()["alerts_checked"] == 1

        other_resp = client.post("/api/alerts/check", headers=auth_headers(other_token))
        assert other_resp.status_code == 200, other_resp.text
        assert other_resp.json()["alerts_checked"] == 1

    def test_test_alert_rejects_foreign_alert(self, client, db):
        register_and_login(client, email="alert-owner@example.com")
        other_token = register_and_login(client, email="alert-other@example.com")

        owner = db.query(User).filter(User.email == "alert-owner@example.com").first()
        assert owner is not None

        product = ProductMonitored(title="Owner Alert Product", user_id=owner.id)
        db.add(product)
        db.flush()

        alert = PriceAlert(
            user_id=owner.id,
            product_id=product.id,
            alert_type="price_drop",
            threshold_pct=5.0,
            email="alert-owner@example.com",
            enabled=True,
        )
        db.add(alert)
        db.commit()

        resp = client.post(f"/api/alerts/test/{alert.id}", headers=auth_headers(other_token))
        assert resp.status_code == 404
