"""
Webhook Notification Service

Sends real-time alerts to Slack and Discord via incoming webhooks.
These are triggered whenever a price alert fires.

Slack docs:   https://api.slack.com/messaging/webhooks
Discord docs: https://discord.com/developers/docs/resources/webhook
"""

import logging
import urllib.request
import urllib.error
import json as _json
from typing import Optional

logger = logging.getLogger(__name__)


def _post_json(url: str, payload: dict) -> bool:
    """POST a JSON payload to a URL. Returns True on success."""
    try:
        data = _json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        logger.error(f"Webhook HTTP error {e.code}: {e.reason} → {url}")
        return False
    except Exception as e:
        logger.error(f"Webhook error: {e} → {url}")
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
    """
    Send a price alert to a Slack channel via incoming webhook.

    The message uses Slack's Block Kit for rich formatting:
    - Color bar: red for price drop, green for price increase
    - Fields: competitor, old price, new price, change %
    - Action button linking to the product page
    """
    direction = "dropped" if change_pct < 0 else "increased"
    icon = "📉" if change_pct < 0 else "📈"
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
                                f"{icon} *Price {direction}* on *{competitor_name}*\n"
                                f"*{product_title}*"
                            )
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Old Price*\n${old_price:.2f}" if old_price else "*Old Price*\n—"},
                            {"type": "mrkdwn", "text": f"*New Price*\n${new_price:.2f}"},
                            {"type": "mrkdwn", "text": f"*Change*\n{'+' if change_pct > 0 else ''}{change_pct:.1f}%"},
                            {"type": "mrkdwn", "text": f"*Competitor*\n{competitor_name}"},
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Product"},
                                "url": product_url,
                                "style": "primary"
                            }
                        ]
                    }
                ]
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
    """
    Send a price alert to a Discord channel via webhook.

    Uses Discord's embed format with color coding.
    """
    direction = "dropped" if change_pct < 0 else "increased"
    icon = "📉" if change_pct < 0 else "📈"
    color = 0xEF4444 if change_pct < 0 else 0x22C55E  # Discord uses decimal int colors

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
                "title": f"{icon} Price {direction} — {product_title}",
                "url": product_url,
                "color": color,
                "fields": fields,
                "footer": {"text": "MarketIntel · Price Intelligence"}
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
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 MarketIntel Daily Digest — {date}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Products Monitored*\n{stats.get('products_monitored', 0)}"},
                {"type": "mrkdwn", "text": f"*Price Updates*\n{stats.get('price_updates', 0)}"},
                {"type": "mrkdwn", "text": f"*Competitors Tracked*\n{stats.get('competitors_tracked', 0)}"},
            ]
        },
    ]

    if top_drops:
        drop_text = "\n".join(
            f"• {d.get('product_title', '')} — {d.get('competitor', '')} "
            f"${d.get('current_price', '')} ({d.get('change_pct', 0):.1f}%)"
            for d in top_drops[:3]
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*📉 Top Price Drops*\n{drop_text}"}
        })

    payload = {"blocks": blocks}
    return _post_json(webhook_url, payload)
