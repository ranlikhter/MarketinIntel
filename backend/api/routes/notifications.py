"""
Notification Preferences API
GET/POST user notification preferences and send test emails
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from database.connection import get_db
from database.models import User
from services.auth_service import verify_token
from services.email_service import email_service
from services.webhook_service import normalize_discord_webhook_url, normalize_slack_webhook_url

router = APIRouter(prefix="/notifications", tags=["Notifications"])
security = HTTPBearer()


# ── Auth helper ────────────────────────────────────────────────────────────────

def _get_user(credentials: HTTPAuthorizationCredentials, db: Session) -> User:
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Models ─────────────────────────────────────────────────────────────────────

class NotificationPrefs(BaseModel):
    defaultEmail: Optional[str] = ''
    digestFrequency: Optional[str] = 'instant'
    enableEmail: Optional[bool] = True
    enableSlack: Optional[bool] = False
    slackWebhook: Optional[str] = ''
    enableDiscord: Optional[bool] = False
    discordWebhook: Optional[str] = ''
    quietHours: Optional[bool] = False
    quietStart: Optional[int] = 22
    quietEnd: Optional[int] = 8


class TestEmailRequest(BaseModel):
    email: EmailStr


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: Optional[str] = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

def _normalize_notification_prefs(prefs: NotificationPrefs) -> dict:
    prefs_dict = prefs.model_dump()

    slack_webhook = (prefs_dict.get("slackWebhook") or "").strip()
    discord_webhook = (prefs_dict.get("discordWebhook") or "").strip()

    if slack_webhook:
        try:
            prefs_dict["slackWebhook"] = normalize_slack_webhook_url(slack_webhook)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        prefs_dict["slackWebhook"] = ""

    if discord_webhook:
        try:
            prefs_dict["discordWebhook"] = normalize_discord_webhook_url(discord_webhook)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        prefs_dict["discordWebhook"] = ""

    if prefs_dict.get("enableSlack") and not prefs_dict["slackWebhook"]:
        raise HTTPException(status_code=400, detail="A valid Slack webhook URL is required when Slack notifications are enabled")

    if prefs_dict.get("enableDiscord") and not prefs_dict["discordWebhook"]:
        raise HTTPException(status_code=400, detail="A valid Discord webhook URL is required when Discord notifications are enabled")

    return prefs_dict


@router.get("/preferences")
async def get_notification_preferences(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get the current user's notification preferences"""
    user = _get_user(credentials, db)
    prefs = user.notification_prefs or {}
    # Fill in user email as default if not set
    if not prefs.get('defaultEmail'):
        prefs = {**prefs, 'defaultEmail': user.email}
    return prefs


@router.post("/preferences")
async def save_notification_preferences(
    prefs: NotificationPrefs,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Save the current user's notification preferences"""
    user = _get_user(credentials, db)
    user.notification_prefs = _normalize_notification_prefs(prefs)
    db.commit()
    return {"success": True, "message": "Preferences saved"}


@router.post("/test-email")
async def send_test_email(
    request: TestEmailRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Send a test email to verify notification delivery"""
    user = _get_user(credentials, db)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                 color: #1f2937; max-width: 560px; margin: 0 auto; padding: 24px;">
      <div style="background: #2563eb; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
        <h1 style="color: white; margin: 0; font-size: 22px;">Test Notification</h1>
        <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">MarketIntel email delivery confirmed</p>
      </div>
      <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px;">
        <p style="margin: 0 0 12px;">Hi {user.full_name or 'there'},</p>
        <p style="margin: 0 0 12px;">This is a test email confirming that your notification settings are working correctly.</p>
        <p style="margin: 0 0 12px;">You will receive alerts at this address when:</p>
        <ul style="margin: 0 0 12px; padding-left: 20px; color: #4b5563;">
          <li>Competitor prices drop significantly</li>
          <li>You become the most expensive seller</li>
          <li>New competitors are detected</li>
          <li>Other custom alert conditions are met</li>
        </ul>
        <p style="margin: 0; color: #6b7280; font-size: 13px;">
          You can manage your notification preferences in the
          <a href="{__import__('os').getenv('FRONTEND_URL', 'http://localhost:3000')}/settings?tab=notifications"
             style="color: #2563eb;">MarketIntel Settings</a>.
        </p>
      </div>
      <p style="text-align: center; font-size: 12px; color: #9ca3af; margin-top: 20px;">
        &copy; MarketIntel &mdash; E-commerce Competitive Intelligence
      </p>
    </body>
    </html>
    """

    text_content = (
        f"Hi {user.full_name or 'there'},\n\n"
        "This is a test email confirming your MarketIntel notification settings are working.\n\n"
        "You will receive alerts when competitor prices change.\n\n"
        "-- MarketIntel"
    )

    sent = email_service.send_email(
        to_email=request.email,
        subject="Test Notification from MarketIntel",
        html_content=html_content,
        text_content=text_content
    )

    if sent:
        return {"success": True, "message": f"Test email sent to {request.email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check SMTP configuration.")


# ── Push notification endpoints ─────────────────────────────────────────────────

@router.get("/push/vapid-public-key")
async def get_vapid_public_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Return the VAPID public key so the browser can subscribe."""
    _get_user(credentials, db)
    import services.push_service as push_service
    key = push_service.get_vapid_public_key()
    if not key:
        raise HTTPException(status_code=503, detail="Push notifications not configured (VAPID keys missing)")
    return {"vapid_public_key": key}


@router.post("/push/subscribe")
async def subscribe_push(
    request: PushSubscribeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Save a browser push subscription."""
    user = _get_user(credentials, db)
    import services.push_service as push_service
    sub = push_service.subscribe(
        db=db,
        user_id=user.id,
        endpoint=request.endpoint,
        p256dh=request.p256dh,
        auth=request.auth,
        user_agent=request.user_agent,
    )
    return {"success": True, "subscription_id": sub.id}


@router.delete("/push/unsubscribe")
async def unsubscribe_push(
    request: PushUnsubscribeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Deactivate a browser push subscription."""
    user = _get_user(credentials, db)
    import services.push_service as push_service
    removed = push_service.unsubscribe(db=db, user_id=user.id, endpoint=request.endpoint)
    return {"success": removed}


@router.post("/test-slack")
async def send_test_slack(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Send a test Slack message to verify the configured webhook."""
    user = _get_user(credentials, db)
    prefs = user.notification_prefs or {}
    webhook = (prefs.get("slackWebhook") or "").strip()
    if not webhook:
        raise HTTPException(status_code=400, detail="No Slack webhook configured. Save your webhook URL first.")
    from services.webhook_service import send_slack_alert
    success = send_slack_alert(
        webhook_url=webhook,
        product_title="Test Product — MarketIntel",
        competitor_name="MarketIntel Test",
        old_price=99.99,
        new_price=99.99,
        change_pct=0.0,
        product_url="",
    )
    if not success:
        raise HTTPException(status_code=500, detail="Slack delivery failed — check your webhook URL.")
    return {"success": True, "message": "Test message sent to Slack"}


@router.post("/test-discord")
async def send_test_discord(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Send a test Discord message to verify the configured webhook."""
    user = _get_user(credentials, db)
    prefs = user.notification_prefs or {}
    webhook = (prefs.get("discordWebhook") or "").strip()
    if not webhook:
        raise HTTPException(status_code=400, detail="No Discord webhook configured. Save your webhook URL first.")
    from services.webhook_service import send_discord_alert
    success = send_discord_alert(
        webhook_url=webhook,
        product_title="Test Product — MarketIntel",
        competitor_name="MarketIntel Test",
        old_price=99.99,
        new_price=99.99,
        change_pct=0.0,
        product_url="",
    )
    if not success:
        raise HTTPException(status_code=500, detail="Discord delivery failed — check your webhook URL.")
    return {"success": True, "message": "Test message sent to Discord"}


@router.get("/digest-preview")
async def digest_preview(
    days: int = 7,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    GET /notifications/digest-preview?days=7

    Return the digest data (stats + top price movements) without sending email.
    Used to let users preview what their weekly/daily digest would look like.
    """
    from database.models import PriceHistory, CompetitorMatch, PriceAlert
    from sqlalchemy import func as sqlfunc
    from datetime import timedelta
    from collections import defaultdict

    user = _get_user(credentials, db)
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 30)))

    # Triggered alerts in window
    triggered = db.query(PriceAlert).filter(
        PriceAlert.user_id == user.id,
        PriceAlert.last_triggered_at >= since,
    ).count()

    # Stats
    from database.models import ProductMonitored
    products_count = db.query(sqlfunc.count(ProductMonitored.id)).filter(
        ProductMonitored.user_id == user.id,
    ).scalar() or 0

    competitors_count = (
        db.query(sqlfunc.count(CompetitorMatch.id))
        .join(ProductMonitored)
        .filter(ProductMonitored.user_id == user.id)
        .scalar() or 0
    )

    price_updates = (
        db.query(sqlfunc.count(PriceHistory.id))
        .join(CompetitorMatch)
        .join(ProductMonitored)
        .filter(
            ProductMonitored.user_id == user.id,
            PriceHistory.timestamp >= since,
        )
        .scalar() or 0
    )

    # Top movements (join PriceHistory + CompetitorMatch + ProductMonitored)
    movements_raw = (
        db.query(
            ProductMonitored.title.label("product"),
            CompetitorMatch.competitor_name,
            sqlfunc.min(PriceHistory.price).label("min_price"),
            sqlfunc.max(PriceHistory.price).label("max_price"),
        )
        .join(CompetitorMatch, CompetitorMatch.monitored_product_id == ProductMonitored.id)
        .join(PriceHistory, PriceHistory.match_id == CompetitorMatch.id)
        .filter(
            ProductMonitored.user_id == user.id,
            PriceHistory.timestamp >= since,
        )
        .group_by(ProductMonitored.id, CompetitorMatch.id)
        .having(sqlfunc.count(PriceHistory.id) >= 2)
        .limit(20)
        .all()
    )

    drops, increases = [], []
    for row in movements_raw:
        if row.min_price and row.max_price and row.max_price > 0:
            change_pct = (row.min_price - row.max_price) / row.max_price * 100
            entry = {"product": row.product, "competitor": row.competitor_name,
                     "change_pct": round(abs(change_pct), 1)}
            if change_pct < -1:
                drops.append(entry)
            elif change_pct > 1:
                increases.append({**entry, "change_pct": round(change_pct, 1)})

    drops.sort(key=lambda x: -x["change_pct"])
    increases.sort(key=lambda x: -x["change_pct"])

    return {
        "period_days": days,
        "stats": {
            "products_monitored": products_count,
            "price_updates": price_updates,
            "competitors_tracked": competitors_count,
            "alerts_triggered": triggered,
        },
        "top_price_drops": drops[:5],
        "top_price_increases": increases[:5],
        "has_data": price_updates > 0,
    }


@router.post("/push/test")
async def send_test_push(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Send a test Web Push notification to all of the user's subscribed devices."""
    user = _get_user(credentials, db)
    import services.push_service as push_service
    result = push_service.send_push_to_user(
        db=db,
        user_id=user.id,
        title="MarketIntel Test",
        body="Push notifications are working correctly.",
        url="/settings?tab=notifications",
        tag="test-push",
    )
    if result.get("skipped"):
        raise HTTPException(status_code=400, detail=result.get("reason", "No active push subscriptions"))
    return {"success": True, **result}
