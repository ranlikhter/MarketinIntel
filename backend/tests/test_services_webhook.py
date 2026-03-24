"""
Unit Tests — Webhook Service (URL validation)

Tests Slack and Discord webhook URL normalisation and validation.
"""

import pytest
from services.webhook_service import (
    normalize_slack_webhook_url,
    normalize_discord_webhook_url,
)


# ── Slack ─────────────────────────────────────────────────────────────────────

class TestSlackWebhookValidation:

    VALID = "https://hooks.slack.com/services/T0001/B0001/abcdefghijklmnop"

    def test_valid_slack_webhook(self):
        result = normalize_slack_webhook_url(self.VALID)
        assert result == self.VALID

    def test_slack_must_use_https(self):
        with pytest.raises(ValueError, match="HTTPS"):
            normalize_slack_webhook_url("http://hooks.slack.com/services/T0001/B0001/abc")

    def test_slack_must_use_official_host(self):
        with pytest.raises(ValueError, match="official Slack"):
            normalize_slack_webhook_url("https://hooks.evil.com/services/T0001/B0001/abc")

    def test_slack_must_use_services_path(self):
        with pytest.raises(ValueError, match="/services/"):
            normalize_slack_webhook_url("https://hooks.slack.com/wrong/T0001/B0001/abc")

    def test_slack_rejects_credentials_in_url(self):
        with pytest.raises(ValueError, match="credentials"):
            normalize_slack_webhook_url("https://user:pass@hooks.slack.com/services/T/B/x")

    def test_slack_rejects_query_string(self):
        with pytest.raises(ValueError, match="query"):
            normalize_slack_webhook_url(f"{self.VALID}?foo=bar")

    def test_slack_rejects_fragment(self):
        with pytest.raises(ValueError, match="fragment|query"):
            normalize_slack_webhook_url(f"{self.VALID}#section")

    def test_slack_rejects_non_standard_port(self):
        with pytest.raises(ValueError, match="port"):
            normalize_slack_webhook_url(
                "https://hooks.slack.com:9000/services/T0001/B0001/abc"
            )

    def test_slack_gov_host_accepted(self):
        url = "https://hooks.slack-gov.com/services/T0001/B0001/abc"
        result = normalize_slack_webhook_url(url)
        assert result == url

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            normalize_slack_webhook_url("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            normalize_slack_webhook_url("   ")


# ── Discord ───────────────────────────────────────────────────────────────────

class TestDiscordWebhookValidation:

    VALID = "https://discord.com/api/webhooks/123456789/abcdefghijklmno"

    def test_valid_discord_webhook(self):
        result = normalize_discord_webhook_url(self.VALID)
        assert result == self.VALID

    def test_discord_must_use_https(self):
        with pytest.raises(ValueError, match="HTTPS"):
            normalize_discord_webhook_url(
                "http://discord.com/api/webhooks/123/abc"
            )

    def test_discord_must_use_official_host(self):
        with pytest.raises(ValueError, match="official Discord"):
            normalize_discord_webhook_url("https://evil.com/api/webhooks/123/abc")

    def test_discord_must_use_api_webhooks_path(self):
        with pytest.raises(ValueError, match="/api/webhooks/"):
            normalize_discord_webhook_url("https://discord.com/wrong/webhooks/123/abc")

    def test_discord_rejects_credentials(self):
        with pytest.raises(ValueError, match="credentials"):
            normalize_discord_webhook_url(
                "https://user:pass@discord.com/api/webhooks/123/abc"
            )

    def test_discord_rejects_query_string(self):
        with pytest.raises(ValueError, match="query"):
            normalize_discord_webhook_url(f"{self.VALID}?wait=true")

    def test_ptb_discord_host_accepted(self):
        url = "https://ptb.discord.com/api/webhooks/123456789/abc"
        result = normalize_discord_webhook_url(url)
        assert result == url

    def test_canary_discord_host_accepted(self):
        url = "https://canary.discord.com/api/webhooks/123456789/abc"
        result = normalize_discord_webhook_url(url)
        assert result == url

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            normalize_discord_webhook_url("")
