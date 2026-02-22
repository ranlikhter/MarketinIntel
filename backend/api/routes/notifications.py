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


# ── Endpoints ──────────────────────────────────────────────────────────────────

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
    user.notification_prefs = prefs.dict()
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
