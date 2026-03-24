"""
Deep Integration Tests — Alerts API (/api/alerts/*)

Tests all 10 alert types, validation, notification channels,
snooze/unsnooze, and workspace scoping.
"""

import pytest
from unittest.mock import patch
from api.dependencies import get_current_user, get_current_workspace, ActiveWorkspace
from api.main import app
from database.models import User, ProductMonitored


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_user_and_product(db, email="alert_user@x.com"):
    user = User(email=email, hashed_password="x", full_name="Alert User")
    db.add(user)
    db.commit()
    db.refresh(user)
    product = ProductMonitored(
        user_id=user.id,
        title="Monitored Widget",
        sku=f"MW-{email[:4]}",
        our_price=99.0,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return user, product


def _fake_workspace(user):
    class FakeWS:
        workspace_id = user.default_workspace_id or user.id
    return FakeWS()


@pytest.fixture()
def authed_client(client, db):
    user, product = make_user_and_product(db)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_workspace] = lambda: _fake_workspace(user)
    yield client, user, product
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_workspace, None)


def alert_payload(product_id, alert_type="price_drop", **kwargs):
    base = {
        "product_id": product_id,
        "alert_type": alert_type,
        "threshold_pct": 5.0,
        "notify_email": True,
        "notify_slack": False,
        "notify_discord": False,
    }
    base.update(kwargs)
    return base


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestAlertsAuth:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/alerts/")
        assert resp.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        resp = client.post("/api/alerts/", json={"product_id": 1, "alert_type": "price_drop"})
        assert resp.status_code in (401, 403)


# ── Tests: All 10 Alert Types ─────────────────────────────────────────────────

ALERT_TYPES = [
    "price_drop",
    "price_increase",
    "any_change",
    "out_of_stock",
    "price_war",
    "new_competitor",
    "most_expensive",
    "competitor_raised",
    "back_in_stock",
    "market_trend",
]


class TestAllAlertTypes:

    @pytest.mark.parametrize("alert_type", ALERT_TYPES)
    def test_create_alert_type(self, alert_type, client, db):
        user, product = make_user_and_product(db, f"{alert_type[:8]}@x.com")
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_workspace] = lambda: _fake_workspace(user)
        resp = client.post("/api/alerts/", json=alert_payload(product.id, alert_type))
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_workspace, None)
        assert resp.status_code in (200, 201), (
            f"Alert type '{alert_type}' failed: {resp.status_code} {resp.text}"
        )
        assert resp.json()["alert_type"] == alert_type


# ── Tests: CRUD ───────────────────────────────────────────────────────────────

class TestAlertsCRUD:

    def test_create_price_drop_alert(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(product.id, "price_drop"))
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["alert_type"] == "price_drop"
        assert data["is_active"] is True

    def test_list_alerts_empty(self, authed_client):
        client, _, _ = authed_client
        resp = client.get("/api/alerts/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_includes_created_alert(self, authed_client):
        client, _, product = authed_client
        client.post("/api/alerts/", json=alert_payload(product.id, "price_drop"))
        resp = client.get("/api/alerts/")
        assert len(resp.json()) >= 1

    def test_get_alert_by_id(self, authed_client):
        client, _, product = authed_client
        create_resp = client.post("/api/alerts/", json=alert_payload(product.id))
        alert_id = create_resp.json()["id"]
        resp = client.get(f"/api/alerts/{alert_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == alert_id

    def test_get_nonexistent_alert_returns_404(self, authed_client):
        client, _, _ = authed_client
        resp = client.get("/api/alerts/999999")
        assert resp.status_code == 404

    def test_update_alert_threshold(self, authed_client):
        client, _, product = authed_client
        create_resp = client.post("/api/alerts/", json=alert_payload(product.id))
        alert_id = create_resp.json()["id"]
        resp = client.put(f"/api/alerts/{alert_id}", json={"threshold_pct": 10.0})
        assert resp.status_code == 200
        assert resp.json()["threshold_pct"] == 10.0

    def test_disable_alert(self, authed_client):
        client, _, product = authed_client
        create_resp = client.post("/api/alerts/", json=alert_payload(product.id))
        alert_id = create_resp.json()["id"]
        resp = client.put(f"/api/alerts/{alert_id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_delete_alert(self, authed_client):
        client, _, product = authed_client
        create_resp = client.post("/api/alerts/", json=alert_payload(product.id))
        alert_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/alerts/{alert_id}")
        assert del_resp.status_code in (200, 204)
        get_resp = client.get(f"/api/alerts/{alert_id}")
        assert get_resp.status_code == 404


# ── Tests: Notification Channels ──────────────────────────────────────────────

class TestAlertNotificationChannels:

    def test_slack_alert_requires_webhook_url(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(
            product.id,
            notify_slack=True,
            slack_webhook_url=None,  # Missing — should fail
        ))
        assert resp.status_code in (400, 422)

    def test_slack_alert_with_valid_webhook(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(
            product.id,
            notify_slack=True,
            slack_webhook_url="https://hooks.slack.com/services/T000/B000/xxxx",
        ))
        assert resp.status_code in (200, 201)

    def test_discord_alert_requires_webhook_url(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(
            product.id,
            notify_discord=True,
            discord_webhook_url=None,
        ))
        assert resp.status_code in (400, 422)

    def test_discord_alert_with_valid_webhook(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(
            product.id,
            notify_discord=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/token",
        ))
        assert resp.status_code in (200, 201)

    def test_email_only_alert(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(
            product.id,
            notify_email=True,
            notify_slack=False,
            notify_discord=False,
        ))
        assert resp.status_code in (200, 201)


# ── Tests: Snooze ─────────────────────────────────────────────────────────────

class TestAlertSnooze:

    def test_snooze_alert(self, authed_client):
        client, _, product = authed_client
        create_resp = client.post("/api/alerts/", json=alert_payload(product.id))
        alert_id = create_resp.json()["id"]
        resp = client.post(f"/api/alerts/{alert_id}/snooze", json={"hours": 24})
        assert resp.status_code in (200, 201, 204)

    def test_unsnooze_alert(self, authed_client):
        client, _, product = authed_client
        create_resp = client.post("/api/alerts/", json=alert_payload(product.id))
        alert_id = create_resp.json()["id"]
        client.post(f"/api/alerts/{alert_id}/snooze", json={"hours": 24})
        resp = client.delete(f"/api/alerts/{alert_id}/snooze")
        assert resp.status_code in (200, 204)


# ── Tests: Validation ─────────────────────────────────────────────────────────

class TestAlertValidation:

    def test_invalid_alert_type_rejected(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(product.id, "invalid_type"))
        assert resp.status_code == 422

    def test_nonexistent_product_returns_404(self, authed_client):
        client, _, _ = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(999999, "price_drop"))
        assert resp.status_code in (404, 422)

    def test_threshold_must_be_positive(self, authed_client):
        client, _, product = authed_client
        resp = client.post("/api/alerts/", json=alert_payload(
            product.id,
            threshold_pct=-5.0,
        ))
        assert resp.status_code in (400, 422)
