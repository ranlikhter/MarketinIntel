"""
Webhook Notification Service

Sends real-time alerts to Slack and Discord via incoming webhooks.
These are triggered whenever a price alert fires.
"""

import json as _json
import logging
import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_HOSTS = {"hooks.slack.com", "hooks.slack-gov.com"}
DISCORD_WEBHOOK_HOSTS = {"discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"}


def _redact_webhook_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or "unknown-host"
        tail = parsed.path[-12:] if parsed.path else ""
        return f"{host}/...{tail}"
    except Exception:
        return "<invalid-webhook-url>"


def _normalize_webhook_url(url: str, provider: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError(f"{provider.title()} webhook URL is required")

    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    if parsed.scheme.lower() != "https":
        raise ValueError(f"{provider.title()} webhook URLs must use HTTPS")
    if parsed.username or parsed.password:
        raise ValueError(f"{provider.title()} webhook URLs cannot include embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{provider.title()} webhook URLs cannot include query strings or fragments")
    if port not in (None, 443):
        raise ValueError(f"{provider.title()} webhook URLs must use the default HTTPS port")

    if provider == "slack":
        if hostname not in SLACK_WEBHOOK_HOSTS:
            raise ValueError("Slack webhook URLs must use an official Slack webhook host")
        if not parsed.path.startswith("/services/"):
            raise ValueError("Slack webhook URLs must use the /services/ path")
    elif provider == "discord":
        if hostname not in DISCORD_WEBHOOK_HOSTS:
            raise ValueError("Discord webhook URLs must use an official Discord webhook host")
        if not parsed.path.startswith("/api/webhooks/"):
            raise ValueError("Discord webhook URLs must use the /api/webhooks/ path")
    else:
        raise ValueError("Unsupported webhook provider")

    return urlunsplit(("https", hostname, parsed.path, "", ""))


def normalize_slack_webhook_url(url: str) -> str:
    return _normalize_webhook_url(url, "slack")


def normalize_discord_webhook_url(url: str) -> str:
    return _normalize_webhook_url(url, "discord")


def _post_json(url: str, payload: dict) -> bool:
    """POST a JSON payload to a URL. Returns True on success."""
    try:
        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as exc:
        logger.error(f"Webhook HTTP error {exc.code}: {exc.reason} -> {_redact_webhook_url(url)}")
        return False
    except Exception as exc:
        logger.error(f"Webhook error: {exc} -> {_redact_webhook_url(url)}")
        return False


def send_slack_alert(
    webhook_url: str,
    product_title: str,
    competitor_name: str,
    old_price: Optional[float],
    new_price: float,
    change_pct: float,
    product_url: str,
) -> bool:
    """Send a price alert to Slack via an incoming webhook."""
    webhook_url = normalize_slack_webhook_url(webhook_url)
    direction = "dropped" if change_pct < 0 else "increased"
    color = "#ef4444" if change_pct < 0 else "#22c55e"
    change_str = f"{abs(change_pct):.1f}%"

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Price {direction}* on *{competitor_name}*\n"
                                f"*{product_title}*"
                            ),
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Old Price*\n${old_price:.2f}" if old_price else "*Old Price*\n-"},
                            {"type": "mrkdwn", "text": f"*New Price*\n${new_price:.2f}"},
                            {"type": "mrkdwn", "text": f"*Change*\n{'+' if change_pct > 0 else ''}{change_pct:.1f}%"},
                            {"type": "mrkdwn", "text": f"*Competitor*\n{competitor_name}"},
                        ],
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Product"},
                                "url": product_url,
                                "style": "primary",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    success = _post_json(webhook_url, payload)
    if success:
        logger.info(f"Slack alert sent: {product_title} price {direction} {change_str}")
    return success


def send_discord_alert(
    webhook_url: str,
    product_title: str,
    competitor_name: str,
    old_price: Optional[float],
    new_price: float,
    change_pct: float,
    product_url: str,
) -> bool:
    """Send a price alert to Discord via webhook."""
    webhook_url = normalize_discord_webhook_url(webhook_url)
    direction = "dropped" if change_pct < 0 else "increased"
    color = 0xEF4444 if change_pct < 0 else 0x22C55E

    fields = [
        {"name": "Competitor", "value": competitor_name, "inline": True},
        {"name": "New Price", "value": f"${new_price:.2f}", "inline": True},
        {"name": "Change", "value": f"{'+' if change_pct > 0 else ''}{change_pct:.1f}%", "inline": True},
    ]
    if old_price:
        fields.insert(1, {"name": "Old Price", "value": f"${old_price:.2f}", "inline": True})

    payload = {
        "embeds": [
            {
                "title": f"Price {direction} - {product_title}",
                "url": product_url,
                "color": color,
                "fields": fields,
                "footer": {"text": "MarketIntel Price Intelligence"},
            }
        ]
    }

    success = _post_json(webhook_url, payload)
    if success:
        logger.info(f"Discord alert sent: {product_title} price {direction}")
    return success


def send_slack_digest(
    webhook_url: str,
    date: str,
    stats: dict,
    top_drops: list,
    top_increases: list,
) -> bool:
    """Send daily digest summary to Slack."""
    webhook_url = normalize_slack_webhook_url(webhook_url)
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"MarketIntel Daily Digest - {date}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Products Monitored*\n{stats.get('products_monitored', 0)}"},
                {"type": "mrkdwn", "text": f"*Price Updates*\n{stats.get('price_updates', 0)}"},
                {"type": "mrkdwn", "text": f"*Competitors Tracked*\n{stats.get('competitors_tracked', 0)}"},
            ],
        },
    ]

    if top_drops:
        drop_text = "\n".join(
            f"- {item.get('product_title', '')} - {item.get('competitor', '')} "
            f"${item.get('current_price', '')} ({item.get('change_pct', 0):.1f}%)"
            for item in top_drops[:3]
        )
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Top Price Drops*\n{drop_text}"},
            }
        )

    if top_increases:
        increase_text = "\n".join(
            f"- {item.get('product_title', '')} - {item.get('competitor', '')} "
            f"${item.get('current_price', '')} ({item.get('change_pct', 0):.1f}%)"
            for item in top_increases[:3]
        )
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Top Price Increases*\n{increase_text}"},
            }
        )

    payload = {"blocks": blocks}
    return _post_json(webhook_url, payload)
