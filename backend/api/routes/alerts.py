"""
Price Alerts API Endpoints
Manage price alert rules and notifications
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import PriceAlert, ProductMonitored, CompetitorMatch, PriceHistory
from services.email_service import email_service

router = APIRouter(prefix="/alerts", tags=["Price Alerts"])


# Pydantic models
class AlertCreate(BaseModel):
    product_id: int
    alert_type: str  # "price_drop", "price_increase", "any_change", "out_of_stock"
    threshold_pct: float = 5.0
    threshold_amount: Optional[float] = None
    email: EmailStr
    cooldown_hours: int = 24


class AlertUpdate(BaseModel):
    alert_type: Optional[str] = None
    threshold_pct: Optional[float] = None
    threshold_amount: Optional[float] = None
    email: Optional[EmailStr] = None
    enabled: Optional[bool] = None
    cooldown_hours: Optional[int] = None


class AlertResponse(BaseModel):
    id: int
    product_id: int
    product_title: str
    alert_type: str
    threshold_pct: float
    threshold_amount: Optional[float]
    email: str
    enabled: bool
    cooldown_hours: int
    last_triggered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Alert CRUD Operations
# ============================================

@router.post("/", response_model=AlertResponse)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """
    Create a new price alert rule

    - **product_id**: Product to monitor
    - **alert_type**: "price_drop", "price_increase", "any_change", "out_of_stock"
    - **threshold_pct**: Percentage change threshold (e.g., 5.0 for 5%)
    - **email**: Email address to send alerts to
    """
    # Verify product exists
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create alert
    new_alert = PriceAlert(
        product_id=alert.product_id,
        alert_type=alert.alert_type,
        threshold_pct=alert.threshold_pct,
        threshold_amount=alert.threshold_amount,
        email=alert.email,
        cooldown_hours=alert.cooldown_hours
    )

    db.add(new_alert)
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
    db: Session = Depends(get_db)
):
    """
    Get all alert rules

    - **product_id**: Filter by product (optional)
    - **enabled_only**: Only return enabled alerts
    """
    query = db.query(PriceAlert)

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
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a specific alert by ID"""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

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
    db: Session = Depends(get_db)
):
    """Update an existing alert"""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

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
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert"""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()

    return {"success": True, "message": "Alert deleted successfully"}


@router.post("/{alert_id}/toggle")
async def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    """Enable/disable an alert"""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.enabled = not alert.enabled
    alert.updated_at = datetime.utcnow()

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
async def check_all_alerts(db: Session = Depends(get_db)):
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
                CompetitorMatch.product_id == product.id
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
        product_url=f"http://localhost:3000/products/{product.id}"
    )

    if success:
        # Update last triggered time
        alert.last_triggered_at = datetime.utcnow()
        db.commit()
        return True

    return False


@router.post("/test/{alert_id}")
async def test_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Send a test email for this alert (ignores cooldown and thresholds)
    """
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == alert.product_id
    ).first()

    # Get a recent match to use for test
    match = db.query(CompetitorMatch).filter(
        CompetitorMatch.product_id == product.id
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
        product_url=f"http://localhost:3000/products/{product.id}"
    )

    if success:
        return {"success": True, "message": f"Test alert sent to {alert.email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email")
