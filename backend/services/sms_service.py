"""
SMS Notification Service

Sends real-time SMS alerts via Twilio's REST API.
Uses only stdlib urllib — no extra packages needed.

Setup (add to .env):
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=your_auth_token
    TWILIO_FROM_NUMBER=+15005550006

Free Twilio trial:  https://twilio.com/try-twilio
Twilio console:     https://console.twilio.com
"""

import os
import logging
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)


def _get_credentials():
    """Return (account_sid, auth_token, from_number) from env, or None if not configured."""
    sid = os.getenv('TWILIO_ACCOUNT_SID', '')
    token = os.getenv('TWILIO_AUTH_TOKEN', '')
    from_num = os.getenv('TWILIO_FROM_NUMBER', '')
    if all([sid, token, from_num]):
        return sid, token, from_num
    return None


def send_sms(to_number: str, message: str) -> bool:
    """
    Send an SMS message via Twilio's REST API.

    Args:
        to_number: Recipient phone number in E.164 format (e.g. '+14155551234')
        message:   Plain-text SMS body (max 1600 chars; split into multiple messages if longer)

    Returns:
        True on success, False on failure or if Twilio is not configured.
    """
    creds = _get_credentials()
    if not creds:
        logger.warning(
            "SMS not configured — set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_FROM_NUMBER in your .env to enable SMS alerts."
        )
        return False

    account_sid, auth_token, from_number = creds

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urllib.parse.urlencode({
        'To': to_number,
        'From': from_number,
        'Body': message[:1600],  # Twilio limit
    }).encode('utf-8')

    # Set up HTTP Basic Auth (account_sid:auth_token)
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, url, account_sid, auth_token)
    handler = urllib.request.HTTPBasicAuthHandler(mgr)
    opener = urllib.request.build_opener(handler)

    try:
        req = urllib.request.Request(url, data=payload, method='POST')
        with opener.open(req, timeout=10) as resp:
            success = resp.status in (200, 201)
            if success:
                logger.info(f"SMS sent to {to_number[:6]}***")
            return success
    except urllib.error.HTTPError as e:
        logger.error(f"Twilio HTTP error {e.code}: {e.reason} sending to {to_number[:6]}***")
        return False
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return False


def format_price_alert(
    product_title: str,
    competitor_name: str,
    new_price: float,
    change_pct: float,
    product_url: str = '',
) -> str:
    """
    Format a compact price alert SMS (fits in a single 160-char message when possible).
    """
    direction = "dropped" if change_pct < 0 else "rose"
    icon = "↓" if change_pct < 0 else "↑"
    short_title = product_title[:40].rstrip()
    if len(product_title) > 40:
        short_title += '…'

    msg = (
        f"MarketIntel {icon} {short_title}\n"
        f"{competitor_name}: ${new_price:.2f} ({change_pct:+.1f}%)\n"
    )
    if product_url:
        msg += product_url
    return msg.strip()


def send_price_alert_sms(
    to_number: str,
    product_title: str,
    competitor_name: str,
    new_price: float,
    change_pct: float,
    product_url: str = '',
) -> bool:
    """Convenience wrapper: format and send a price alert SMS."""
    message = format_price_alert(product_title, competitor_name, new_price, change_pct, product_url)
    return send_sms(to_number, message)
