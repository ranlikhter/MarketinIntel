"""
Web Push Notification Service (VAPID)

Sends browser push notifications using the Web Push protocol.
Requires VAPID keys to be set in environment variables:
    VAPID_PRIVATE_KEY  — base64url-encoded 32-byte EC private key
    VAPID_PUBLIC_KEY   — base64url-encoded uncompressed EC public key (65 bytes)
    VAPID_CLAIMS_EMAIL — contact email included in VAPID claims

Generate a new key pair:
    python -m services.push_service --generate-keys
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from database.models import PushSubscription

logger = logging.getLogger(__name__)


# ── VAPID helpers ──────────────────────────────────────────────────────────────

def get_vapid_public_key() -> Optional[str]:
    """Return the VAPID public key for the browser's applicationServerKey."""
    return os.getenv("VAPID_PUBLIC_KEY")


def _vapid_private_key() -> Optional[str]:
    return os.getenv("VAPID_PRIVATE_KEY")


def _vapid_email() -> str:
    return os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@marketintel.io")


# ── Subscription management ────────────────────────────────────────────────────

def subscribe(
    db: Session,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: Optional[str] = None,
) -> PushSubscription:
    """Upsert a browser push subscription for a user."""
    existing = db.query(PushSubscription).filter_by(endpoint=endpoint).first()
    if existing:
        existing.user_id = user_id
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = user_agent
        existing.is_active = True
        db.commit()
        return existing

    sub = PushSubscription(
        user_id=user_id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent,
        is_active=True,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def unsubscribe(db: Session, user_id: int, endpoint: str) -> bool:
    """Deactivate a push subscription by endpoint URL."""
    sub = (
        db.query(PushSubscription)
        .filter_by(user_id=user_id, endpoint=endpoint)
        .first()
    )
    if not sub:
        return False
    sub.is_active = False
    db.commit()
    return True


# ── Push delivery ──────────────────────────────────────────────────────────────

def send_push_to_user(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    url: str = "/",
    tag: str = "marketintel",
    urgent: bool = False,
) -> dict:
    """
    Send a Web Push notification to all active subscriptions for a user.

    Returns {"sent": N, "failed": N, "skipped": N, "reason": str | None}
    """
    private_key = _vapid_private_key()
    public_key = get_vapid_public_key()
    if not private_key or not public_key:
        return {"sent": 0, "failed": 0, "skipped": 1, "reason": "VAPID keys not configured"}

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return {"sent": 0, "failed": 0, "skipped": 1, "reason": "pywebpush not installed"}

    subscriptions = (
        db.query(PushSubscription)
        .filter_by(user_id=user_id, is_active=True)
        .all()
    )
    if not subscriptions:
        return {"sent": 0, "failed": 0, "skipped": 1, "reason": "no active subscriptions"}

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "tag": tag,
    })

    sent = failed = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={
                    "sub": _vapid_email(),
                    "aud": (sub.endpoint.split("/")[2:3] or [sub.endpoint])[0],
                },
                ttl=86400 if not urgent else 3600,
            )
            sub.last_used_at = datetime.utcnow()
            sent += 1
        except WebPushException as exc:
            # 410 Gone = subscription revoked by the browser
            if exc.response and exc.response.status_code == 410:
                sub.is_active = False
                logger.info("Push subscription revoked (410), deactivated: %s", sub.id)
            else:
                logger.warning("Push send failed for sub %s: %s", sub.id, exc)
            failed += 1
        except Exception as exc:
            logger.error("Unexpected push error for sub %s: %s", sub.id, exc)
            failed += 1

    db.commit()
    return {"sent": sent, "failed": failed, "skipped": 0, "reason": None}


def send_price_alert_push(
    db: Session,
    user_id: int,
    product_id: int,
    product_title: str,
    competitor_name: str,
    new_price: float,
    change_pct: float,
) -> dict:
    """Convenience wrapper for price-change push notifications."""
    direction = "dropped" if change_pct < 0 else "rose"
    return send_push_to_user(
        db=db,
        user_id=user_id,
        title=f"Price {direction}: {product_title[:40]}",
        body=f"{competitor_name} is now ${new_price:.2f} ({change_pct:+.1f}%)",
        url=f"/products/{product_id}",
        tag=f"price-{product_id}",
        urgent=abs(change_pct) >= 10,
    )


# ── CLI key generator ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--generate-keys" in sys.argv:
        try:
            from py_vapid import Vapid
            v = Vapid()
            v.generate_keys()
            print("Add these to your .env:")
            print(f"VAPID_PRIVATE_KEY={v.private_key_urlsafe}")
            print(f"VAPID_PUBLIC_KEY={v.public_key_urlsafe}")
        except ImportError:
            print("Install py-vapid: pip install py-vapid")
