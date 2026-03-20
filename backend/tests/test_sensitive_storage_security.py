"""
Security-focused tests for encrypted secret storage and webhook validation.
"""

import json

from sqlalchemy import text

from database.models import PriceAlert, ProductMonitored, StoreConnection, User
from database.secure_types import encrypt_existing_sensitive_values
from services.auth_service import create_access_token
from tests.conftest import auth_headers


def _get_user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user


def _create_user(db, email: str) -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        full_name="Security Test User",
        auth_provider="local",
        password_login_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _token_for_user(user: User) -> str:
    return create_access_token({"sub": str(user.id)})


def _create_product(db, user_id: int, title: str = "Tracked Product") -> ProductMonitored:
    product = ProductMonitored(title=title, user_id=user_id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


class TestSensitiveStorageSecurity:
    def test_store_connection_credentials_are_encrypted_at_rest(self, db):
        email = "store-secret@example.com"
        user = _create_user(db, email)

        connection = StoreConnection(
            user_id=user.id,
            platform="woocommerce",
            store_url="https://example.com",
            api_key="ck_secret_value",
            api_secret="cs_secret_value",
            sync_inventory=True,
        )
        db.add(connection)
        db.commit()
        db.refresh(connection)

        row = db.execute(
            text("SELECT api_key, api_secret FROM store_connections WHERE user_id = :user_id"),
            {"user_id": user.id},
        ).mappings().first()

        assert row is not None
        assert row["api_key"] != "ck_secret_value"
        assert row["api_secret"] != "cs_secret_value"
        assert "enc::" in row["api_key"]
        assert "enc::" in row["api_secret"]

        stored_connection = db.query(StoreConnection).filter(StoreConnection.user_id == user.id).first()
        assert stored_connection is not None
        assert stored_connection.api_key == "ck_secret_value"
        assert stored_connection.api_secret == "cs_secret_value"

    def test_alert_webhooks_are_encrypted_at_rest(self, client, db):
        email = "alert-secret@example.com"
        user = _create_user(db, email)
        token = _token_for_user(user)
        product = _create_product(db, user.id)

        slack_url = "https://hooks.slack.com/services/T000/B000/SLACKSECRET"
        discord_url = "https://discord.com/api/webhooks/123456/DISCORDSECRET"

        response = client.post(
            "/api/alerts/",
            headers=auth_headers(token),
            json={
                "product_id": product.id,
                "alert_type": "price_drop",
                "threshold_pct": 5.0,
                "email": email,
                "notify_slack": True,
                "notify_discord": True,
                "slack_webhook_url": slack_url,
                "discord_webhook_url": discord_url,
            },
        )
        assert response.status_code == 200, response.text

        row = db.execute(
            text(
                "SELECT slack_webhook_url, discord_webhook_url "
                "FROM price_alerts WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        ).mappings().first()

        assert row is not None
        assert row["slack_webhook_url"] != slack_url
        assert row["discord_webhook_url"] != discord_url
        assert "enc::" in row["slack_webhook_url"]
        assert "enc::" in row["discord_webhook_url"]

        alert = db.query(PriceAlert).filter(PriceAlert.user_id == user.id).first()
        assert alert is not None
        assert alert.slack_webhook_url == slack_url
        assert alert.discord_webhook_url == discord_url

    def test_notification_preferences_are_encrypted_at_rest(self, client, db):
        email = "prefs-secret@example.com"
        user = _create_user(db, email)
        token = _token_for_user(user)

        slack_url = "https://hooks.slack.com/services/T000/B000/PREFSSECRET"
        discord_url = "https://discord.com/api/webhooks/654321/PREFSDISCORD"

        response = client.post(
            "/api/notifications/preferences",
            headers=auth_headers(token),
            json={
                "defaultEmail": email,
                "digestFrequency": "instant",
                "enableEmail": True,
                "enableSlack": True,
                "slackWebhook": slack_url,
                "enableDiscord": True,
                "discordWebhook": discord_url,
                "quietHours": False,
                "quietStart": 22,
                "quietEnd": 8,
            },
        )
        assert response.status_code == 200, response.text

        raw_value = db.execute(
            text("SELECT notification_prefs FROM users WHERE email = :email"),
            {"email": email},
        ).scalar_one()
        stored_value = raw_value if isinstance(raw_value, str) else json.dumps(raw_value)

        assert slack_url not in stored_value
        assert discord_url not in stored_value
        assert "enc::" in stored_value

        user = _get_user(db, email)
        assert user.notification_prefs["slackWebhook"] == slack_url
        assert user.notification_prefs["discordWebhook"] == discord_url

    def test_invalid_webhook_hosts_are_rejected_by_routes(self, client, db):
        email = "reject-webhook@example.com"
        user = _create_user(db, email)
        token = _token_for_user(user)
        product = _create_product(db, user.id, title="Webhook Test Product")

        bad_alert = client.post(
            "/api/alerts/",
            headers=auth_headers(token),
            json={
                "product_id": product.id,
                "alert_type": "price_drop",
                "threshold_pct": 5.0,
                "email": email,
                "notify_slack": True,
                "slack_webhook_url": "http://127.0.0.1/internal-hook",
            },
        )
        assert bad_alert.status_code == 400
        assert "Slack webhook" in bad_alert.json()["detail"]

        bad_prefs = client.post(
            "/api/notifications/preferences",
            headers=auth_headers(token),
            json={
                "defaultEmail": email,
                "enableSlack": True,
                "slackWebhook": "https://example.com/not-slack",
            },
        )
        assert bad_prefs.status_code == 400
        assert "Slack webhook" in bad_prefs.json()["detail"]

    def test_encrypt_existing_sensitive_values_rewrites_legacy_plaintext_rows(self, db):
        user = User(
            email="legacy-encryption@example.com",
            hashed_password="hashed",
            full_name="Legacy User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        product = _create_product(db, user.id, title="Legacy Product")

        db.execute(
            text(
                "INSERT INTO store_connections "
                "(user_id, platform, store_url, api_key, api_secret, is_active, sync_inventory) "
                "VALUES (:user_id, :platform, :store_url, :api_key, :api_secret, :is_active, :sync_inventory)"
            ),
            {
                "user_id": user.id,
                "platform": "shopify",
                "store_url": "https://legacy.example.com",
                "api_key": "legacy_plain_api_key",
                "api_secret": "legacy_plain_api_secret",
                "is_active": True,
                "sync_inventory": True,
            },
        )
        db.execute(
            text(
                "INSERT INTO price_alerts "
                "(user_id, product_id, alert_type, threshold_pct, email, notify_email, notify_slack, notify_discord, enabled, cooldown_hours, slack_webhook_url, discord_webhook_url) "
                "VALUES (:user_id, :product_id, :alert_type, :threshold_pct, :email, :notify_email, :notify_slack, :notify_discord, :enabled, :cooldown_hours, :slack_webhook_url, :discord_webhook_url)"
            ),
            {
                "user_id": user.id,
                "product_id": product.id,
                "alert_type": "price_drop",
                "threshold_pct": 5.0,
                "email": user.email,
                "notify_email": True,
                "notify_slack": True,
                "notify_discord": True,
                "enabled": True,
                "cooldown_hours": 24,
                "slack_webhook_url": "https://hooks.slack.com/services/T000/B000/LEGACY",
                "discord_webhook_url": "https://discord.com/api/webhooks/999/LEGACY",
            },
        )
        db.execute(
            text("UPDATE users SET notification_prefs = :prefs WHERE id = :user_id"),
            {
                "user_id": user.id,
                "prefs": json.dumps(
                    {
                        "enableSlack": True,
                        "slackWebhook": "https://hooks.slack.com/services/T000/B000/LEGACYPREFS",
                    }
                ),
            },
        )
        db.commit()

        updated_rows = encrypt_existing_sensitive_values(db.connection())
        db.commit()

        assert updated_rows >= 3
        assert encrypt_existing_sensitive_values(db.connection()) == 0

        store_row = db.execute(
            text("SELECT api_key, api_secret FROM store_connections WHERE user_id = :user_id"),
            {"user_id": user.id},
        ).mappings().first()
        alert_row = db.execute(
            text(
                "SELECT slack_webhook_url, discord_webhook_url "
                "FROM price_alerts WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        ).mappings().first()
        prefs_row = db.execute(
            text("SELECT notification_prefs FROM users WHERE id = :user_id"),
            {"user_id": user.id},
        ).scalar_one()

        assert "enc::" in store_row["api_key"]
        assert "enc::" in store_row["api_secret"]
        assert "enc::" in alert_row["slack_webhook_url"]
        assert "enc::" in alert_row["discord_webhook_url"]
        assert "enc::" in str(prefs_row)

        connection = db.query(StoreConnection).filter(StoreConnection.user_id == user.id).first()
        alert = db.query(PriceAlert).filter(PriceAlert.user_id == user.id).first()
        db.refresh(user)

        assert connection.api_key == "legacy_plain_api_key"
        assert connection.api_secret == "legacy_plain_api_secret"
        assert alert.slack_webhook_url == "https://hooks.slack.com/services/T000/B000/LEGACY"
        assert alert.discord_webhook_url == "https://discord.com/api/webhooks/999/LEGACY"
        assert user.notification_prefs["slackWebhook"] == "https://hooks.slack.com/services/T000/B000/LEGACYPREFS"
