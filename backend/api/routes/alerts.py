"""
Price Alerts API Endpoints
Manage price alert rules and notifications
"""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import ConfigDict, BaseModel, EmailStr
from typing import Literal, Optional, List

ALERT_TYPE = Literal[
    "price_drop", "price_increase", "any_change", "out_of_stock",
    "price_war", "new_competitor", "most_expensive", "competitor_raised",
    "back_in_stock", "market_trend",
]
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import PriceAlert, ProductMonitored, CompetitorMatch, PriceHistory, User
from services.email_service import email_service
from services.activity_service import log_activity
from api.dependencies import get_current_user, check_usage_limit

router = APIRouter(prefix="/alerts", tags=["Price Alerts"])


# Pydantic models
class AlertCreate(BaseModel):
    product_id: int
    alert_type: ALERT_TYPE
    threshold_pct: float = 5.0
    threshold_amount: Optional[float] = None

    # Notification channels
    email: EmailStr
    notify_email: bool = True
    notify_sms: bool = False
    notify_slack: bool = False
    notify_discord: bool = False
    notify_push: bool = False

    # Channel-specific settings
    phone_number: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    # Delivery preferences
    digest_frequency: str = "instant"  # "instant", "daily", "weekly"
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[int] = None  # Hour 0-23
    quiet_hours_end: Optional[int] = None  # Hour 0-23

    # Frequency control
    cooldown_hours: int = 24


class AlertUpdate(BaseModel):
    alert_type: Optional[str] = None
    threshold_pct: Optional[float] = None
    threshold_amount: Optional[float] = None

    # Notification channels
    email: Optional[EmailStr] = None
    notify_email: Optional[bool] = None
    notify_sms: Optional[bool] = None
    notify_slack: Optional[bool] = None
    notify_discord: Optional[bool] = None
    notify_push: Optional[bool] = None

    # Channel-specific settings
    phone_number: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    # Delivery preferences
    digest_frequency: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None

    # Status
    enabled: Optional[bool] = None
    cooldown_hours: Optional[int] = None


class AlertResponse(BaseModel):
    id: int
    product_id: int
    product_title: str
    alert_type: str
    threshold_pct: float
    threshold_amount: Optional[float]

    # Notification channels
    email: str
    notify_email: bool
    notify_sms: bool
    notify_slack: bool
    notify_discord: bool
    notify_push: bool

    # Channel settings
    phone_number: Optional[str]
    slack_webhook_url: Optional[str]
    discord_webhook_url: Optional[str]

    # Delivery preferences
    digest_frequency: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[int]
    quiet_hours_end: Optional[int]

    # Status
    enabled: bool
    cooldown_hours: int
    last_triggered_at: Optional[datetime]
    trigger_count: int
    snoozed_until: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Alert CRUD Operations
# ============================================

@router.post("/", response_model=AlertResponse)
async def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new smart alert rule with multi-channel notifications

    Supported alert types:
    - price_drop: Price decreased
    - price_increase: Price increased
    - any_change: Any price change
    - out_of_stock: Competitor out of stock (opportunity!)
    - price_war: Multiple competitors dropped prices
    - new_competitor: New competitor detected
    - most_expensive: You're most expensive
    - competitor_raised: Competitor increased price
    - back_in_stock: Competitor restocked
    - market_trend: Market trending up/down

    Notification channels:
    - Email (default)
    - SMS (requires phone_number)
    - Slack (requires slack_webhook_url)
    - Discord (requires discord_webhook_url)
    - Push (PWA push notifications)
    """
    # Check if user has reached their alerts limit
    check_usage_limit(current_user, "alerts", db)

    # Verify product exists and belongs to current user
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id,
        ProductMonitored.user_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create alert with all new fields
    new_alert = PriceAlert(
        product_id=alert.product_id,
        alert_type=alert.alert_type,
        threshold_pct=alert.threshold_pct,
        threshold_amount=alert.threshold_amount,
        email=alert.email,
        notify_email=alert.notify_email,
        notify_sms=alert.notify_sms,
        notify_slack=alert.notify_slack,
        notify_discord=alert.notify_discord,
        notify_push=alert.notify_push,
        phone_number=alert.phone_number,
        slack_webhook_url=alert.slack_webhook_url,
        discord_webhook_url=alert.discord_webhook_url,
        digest_frequency=alert.digest_frequency,
        quiet_hours_enabled=alert.quiet_hours_enabled,
        quiet_hours_start=alert.quiet_hours_start,
        quiet_hours_end=alert.quiet_hours_end,
        cooldown_hours=alert.cooldown_hours,
        user_id=current_user.id  # Associate alert with user
    )

    db.add(new_alert)
    db.flush()
    product_title = product.title
    log_activity(db, current_user.id, "alert.create", "alert", f"Created price alert for '{product_title}'", entity_type="alert", entity_id=new_alert.id, entity_name=product_title, metadata={"alert_type": new_alert.alert_type, "product_id": new_alert.product_id})
    db.commit()
    db.refresh(new_alert)

    # Add product title for response
    response_dict = {
        **new_alert.__dict__,
        'product_title': product.title
    }

    return AlertResponse(**response_dict)


@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    product_id: Optional[int] = None,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all alert rules for the authenticated user
    Requires authentication. Only returns alerts owned by the current user.

    - **product_id**: Filter by product (optional)
    - **enabled_only**: Only return enabled alerts
    """
    query = db.query(PriceAlert).filter(PriceAlert.user_id == current_user.id)

    if product_id:
        query = query.filter(PriceAlert.product_id == product_id)

    if enabled_only:
        query = query.filter(PriceAlert.enabled == True)

    alerts = query.all()

    # Add product titles
    result = []
    for alert in alerts:
        product = db.query(ProductMonitored).filter(
            ProductMonitored.id == alert.product_id
        ).first()

        result.append(AlertResponse(
            **alert.__dict__,
            product_title=product.title if product else "Unknown"
        ))

    return result


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific alert by ID
    Requires authentication. Only returns alerts owned by the current user.
    """
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()

    return AlertResponse(
        **alert.__dict__,
        product_title=product.title if product else "Unknown"
    )


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing alert
    Requires authentication. Only allows updating alerts owned by the current user.
    """
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update fields
    if update.alert_type is not None:
        alert.alert_type = update.alert_type
    if update.threshold_pct is not None:
        alert.threshold_pct = update.threshold_pct
    if update.threshold_amount is not None:
        alert.threshold_amount = update.threshold_amount
    if update.email is not None:
        alert.email = update.email
    if update.enabled is not None:
        alert.enabled = update.enabled
    if update.cooldown_hours is not None:
        alert.cooldown_hours = update.cooldown_hours

    alert.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(alert)

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()

    return AlertResponse(
        **alert.__dict__,
        product_title=product.title if product else "Unknown"
    )


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an alert
    Requires authentication. Only allows deleting alerts owned by the current user.
    """
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()
    product_title = product.title if product else "Unknown"
    log_activity(db, current_user.id, "alert.delete", "alert", f"Deleted price alert for '{product_title}'", entity_type="alert", entity_id=alert_id, entity_name=product_title)
    db.delete(alert)
    db.commit()

    return {"success": True, "message": "Alert deleted successfully"}


@router.post("/{alert_id}/toggle")
async def toggle_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enable/disable an alert
    Requires authentication. Only allows toggling alerts owned by the current user.
    """
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.enabled = not alert.enabled
    alert.updated_at = datetime.utcnow()

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()
    product_title = product.title if product else "Unknown"
    log_activity(db, current_user.id, "alert.toggle", "alert", f"{'Enabled' if alert.enabled else 'Disabled'} alert for '{product_title}'", entity_type="alert", entity_id=alert.id, entity_name=product_title, metadata={"enabled": alert.enabled})
    db.commit()
    db.refresh(alert)

    return {
        "success": True,
        "enabled": alert.enabled,
        "message": f"Alert {'enabled' if alert.enabled else 'disabled'}"
    }


# ============================================
# Alert Checking & Triggering
# ============================================

@router.post("/check")
async def check_all_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check all enabled alerts and send notifications if triggered
    """
    alerts = db.query(PriceAlert).filter(PriceAlert.enabled == True).all()

    triggered = 0
    skipped = 0
    errors = 0

    for alert in alerts:
        try:
            # Check cooldown
            if alert.last_triggered_at:
                cooldown_end = alert.last_triggered_at + timedelta(hours=alert.cooldown_hours)
                if datetime.utcnow() < cooldown_end:
                    skipped += 1
                    continue

            # Get product and matches
            product = db.query(ProductMonitored).filter(
                ProductMonitored.id == alert.product_id
            ).first()

            if not product:
                continue

            matches = db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).all()

            # Check each match for price changes
            for match in matches:
                if await check_single_match(alert, match, product, db):
                    triggered += 1

        except Exception as e:
            print(f"Error checking alert {alert.id}: {e}")
            errors += 1

    return {
        "success": True,
        "alerts_checked": len(alerts),
        "triggered": triggered,
        "skipped": skipped,
        "errors": errors
    }


async def check_single_match(
    alert: PriceAlert,
    match: CompetitorMatch,
    product: ProductMonitored,
    db: Session
) -> bool:
    """
    Check if a single match triggers the alert

    Returns True if alert was triggered and email sent
    """
    # Get recent price history (last 2 data points)
    recent_prices = db.query(PriceHistory).filter(
        PriceHistory.match_id == match.id
    ).order_by(PriceHistory.timestamp.desc()).limit(2).all()

    if len(recent_prices) < 2:
        return False  # Need at least 2 prices to compare

    current = recent_prices[0]
    previous = recent_prices[1]

    # Calculate change
    price_diff = current.price - previous.price
    price_change_pct = (price_diff / previous.price) * 100 if previous.price else 0

    # Check if alert should trigger
    should_trigger = False

    if alert.alert_type == "price_drop":
        should_trigger = price_change_pct <= -alert.threshold_pct
    elif alert.alert_type == "price_increase":
        should_trigger = price_change_pct >= alert.threshold_pct
    elif alert.alert_type == "any_change":
        should_trigger = abs(price_change_pct) >= alert.threshold_pct
    elif alert.alert_type == "out_of_stock":
        should_trigger = not current.in_stock and previous.in_stock

    if not should_trigger:
        return False

    # Send email notification
    success = email_service.send_price_alert(
        to_email=alert.email,
        product_title=product.title,
        competitor=match.competitor_name,
        old_price=previous.price,
        new_price=current.price,
        change_pct=price_change_pct,
        product_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/products/{product.id}"
    )

    if success:
        # Update last triggered time
        alert.last_triggered_at = datetime.utcnow()
        db.commit()
        return True

    return False


@router.post("/test/{alert_id}")
async def test_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a test email for this alert (ignores cooldown and thresholds)
    """
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id,
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()

    # Get a recent match to use for test
    match = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product.id
    ).first()

    if not match or not match.latest_price:
        raise HTTPException(status_code=400, detail="No price data available for test")

    # Send test email
    success = email_service.send_price_alert(
        to_email=alert.email,
        product_title=product.title,
        competitor=match.competitor_name,
        old_price=match.latest_price * 1.1,  # Fake 10% higher previous price
        new_price=match.latest_price,
        change_pct=-10.0,
        product_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/products/{product.id}"
    )

    if success:
        return {"success": True, "message": f"Test alert sent to {alert.email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email")

# ============================================
# Smart Alerts (New Feature #2)
# ============================================

@router.get("/types")
async def get_alert_types():
    """
    Get all available smart alert types

    Returns list of all 10 supported alert types with descriptions
    """
    from services.smart_alert_service import SmartAlertService

    return {
        "alert_types": [
            {
                "value": "price_drop",
                "label": "Price Drop",
                "description": "Notify when price decreases",
                "icon": "📉"
            },
            {
                "value": "price_increase",
                "label": "Price Increase",
                "description": "Notify when price increases",
                "icon": "📈"
            },
            {
                "value": "any_change",
                "label": "Any Price Change",
                "description": "Notify on any price movement",
                "icon": "💱"
            },
            {
                "value": "out_of_stock",
                "label": "Competitor Out of Stock",
                "description": "Opportunity! Competitor inventory depleted",
                "icon": "🚫"
            },
            {
                "value": "price_war",
                "label": "Price War Detected",
                "description": "Multiple competitors dropped prices (3+ in 24h)",
                "icon": "⚔️"
            },
            {
                "value": "new_competitor",
                "label": "New Competitor",
                "description": "New seller detected for your product",
                "icon": "🆕"
            },
            {
                "value": "most_expensive",
                "label": "You're Most Expensive",
                "description": "Warning: Your price is highest",
                "icon": "⚠️"
            },
            {
                "value": "competitor_raised",
                "label": "Competitor Raised Price",
                "description": "Opportunity! Competitor became less competitive",
                "icon": "📊"
            },
            {
                "value": "back_in_stock",
                "label": "Back In Stock",
                "description": "Competitor restocked after being out",
                "icon": "✅"
            },
            {
                "value": "market_trend",
                "label": "Market Trend",
                "description": "Overall market prices trending up/down",
                "icon": "📉"
            }
        ]
    }


@router.post("/{alert_id}/check-now")
async def check_alert_now(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger alert check (ignores cooldown)

    Useful for testing alert conditions immediately
    """
    from services.smart_alert_service import get_smart_alert_service

    # Verify alert belongs to current user
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check alert conditions
    alert_service = get_smart_alert_service(db)

    # Temporarily disable cooldown for manual check
    original_cooldown = alert.cooldown_hours
    alert.cooldown_hours = 0

    try:
        triggered = alert_service._should_trigger_alert(alert)

        if triggered:
            alert_service._trigger_alert(alert)
            return {
                "success": True,
                "triggered": True,
                "message": "Alert conditions met and notifications sent"
            }
        else:
            return {
                "success": True,
                "triggered": False,
                "message": "Alert conditions not met at this time"
            }
    finally:
        # Restore original cooldown
        alert.cooldown_hours = original_cooldown
        db.commit()


@router.post("/check-all")
async def check_all_user_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check all alerts for current user

    Useful for triggering a full alert check on-demand
    """
    from tasks.smart_alert_tasks import check_user_smart_alerts

    # Trigger async task to check all user's alerts
    task = check_user_smart_alerts.delay(current_user.id)

    return {
        "success": True,
        "message": "Alert check queued",
        "task_id": task.id
    }


# ============================================================
# Alert Snooze / Unsnooze
# ============================================================

@router.post("/{alert_id}/snooze")
async def snooze_alert(
    alert_id: int,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Temporarily silence an alert without deleting it.

    The alert will resume firing normally once the snooze period expires.

    - **hours**: How long to snooze (default 24 h). Common values: 24, 48, 168 (1 week).
    """
    if hours < 1 or hours > 8760:  # max 1 year
        raise HTTPException(status_code=422, detail="hours must be between 1 and 8760")

    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.snoozed_until = datetime.utcnow() + timedelta(hours=hours)
    alert.updated_at = datetime.utcnow()

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()
    product_title = product.title if product else "Unknown"
    log_activity(
        db, current_user.id, "alert.snooze", "alert",
        f"Snoozed alert for '{product_title}' for {hours}h",
        entity_type="alert", entity_id=alert_id, entity_name=product_title,
        metadata={"hours": hours, "snoozed_until": alert.snoozed_until.isoformat()},
    )
    db.commit()

    return {
        "success": True,
        "alert_id": alert_id,
        "snoozed_until": alert.snoozed_until.isoformat(),
        "message": f"Alert snoozed for {hours} hour(s)",
    }


@router.post("/{alert_id}/unsnooze")
async def unsnooze_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an active snooze and resume the alert immediately.
    """
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.snoozed_until = None
    alert.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "alert_id": alert_id,
        "message": "Alert snooze cancelled — alert is now active",
    }
