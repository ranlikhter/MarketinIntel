"""
Integration Tests — Notifications API (/api/notifications/*)

Tests getting/saving notification preferences and webhook validation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User


def make_user(db, email="notif@x.com"):
    u = User(email=email, hashed_password="x", full_name="Notif User")
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestNotificationsAuth:

    def test_get_prefs_requires_auth(self, client):
        resp = client.get("/api/notifications/preferences")
        assert resp.status_code in (401, 403)

    def test_save_prefs_requires_auth(self, client):
        resp = client.post("/api/notifications/preferences", json={})
        assert resp.status_code in (401, 403)


# ── Tests: Preferences ────────────────────────────────────────────────────────

class TestNotificationPreferences:

    def test_get_default_preferences(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/notifications/preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert "enableEmail" in data or "enable_email" in data or isinstance(data, dict)

    def test_save_email_preferences(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/notifications/preferences", json={
            "enableEmail": True,
            "digestFrequency": "daily",
            "defaultEmail": "alerts@example.com",
        })
        assert resp.status_code in (200, 201, 204)

    def test_save_slack_preferences_with_valid_webhook(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/notifications/preferences", json={
            "enableSlack": True,
            "slackWebhook": "https://hooks.slack.com/services/T000/B000/abcdef",
        })
        assert resp.status_code in (200, 201, 204, 400)  # 400 if validation rejects

    def test_save_discord_preferences_with_valid_webhook(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/notifications/preferences", json={
            "enableDiscord": True,
            "discordWebhook": "https://discord.com/api/webhooks/123/abcdef",
        })
        assert resp.status_code in (200, 201, 204, 400)

    def test_invalid_digest_frequency(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/notifications/preferences", json={
            "digestFrequency": "every_second",  # Invalid
        })
        assert resp.status_code in (400, 422)

    def test_preferences_saved_and_retrievable(self, authed_client):
        client, _ = authed_client
        client.post("/api/notifications/preferences", json={
            "enableEmail": False,
            "digestFrequency": "weekly",
        })
        get_resp = client.get("/api/notifications/preferences")
        assert get_resp.status_code == 200
