"""
Smart Alert Service
Handles intelligent alert detection and multi-channel notifications
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

import logging

from database.models import (
    PriceAlert, ProductMonitored, CompetitorMatch,
    PriceHistory, User
)

logger = logging.getLogger(__name__)


class SmartAlertService:
    """
    Service for detecting and triggering smart alerts
    Supports 10 different alert types and multi-channel delivery
    """

    ALERT_TYPES = {
        "price_drop": "Price Decrease Alert",
        "price_increase": "Price Increase Alert",
        "any_change": "Price Change Alert",
        "out_of_stock": "Competitor Out of Stock",
        "price_war": "Price War Detected",
        "new_competitor": "New Competitor Found",
        "most_expensive": "You're Most Expensive",
        "competitor_raised": "Competitor Raised Price",
        "back_in_stock": "Competitor Back in Stock",
        "market_trend": "Market Trend Alert",
    }

    def __init__(self, db: Session):
        self.db = db

    def check_all_alerts(self, user_id: Optional[int] = None):
        """
        Check all enabled alerts and trigger if conditions are met
        If user_id provided, only check that user's alerts
        """
        query = self.db.query(PriceAlert).filter(
            PriceAlert.enabled == True
        )

        if user_id:
            query = query.filter(PriceAlert.user_id == user_id)

        alerts = query.all()

        triggered_alerts = []
        for alert in alerts:
            if self._should_trigger_alert(alert):
                self._trigger_alert(alert)
                triggered_alerts.append(alert)

        return triggered_alerts

    def _should_trigger_alert(self, alert: PriceAlert) -> bool:
        """
        Check if alert conditions are met
        Returns True if alert should be triggered
        """
        if not alert.can_trigger():
            return False

        # Delegate to specific check method based on alert type
        check_method = getattr(self, f"_check_{alert.alert_type}", None)
        if not check_method:
            return False

        return check_method(alert)

    # Alert Type Checkers

    def _check_price_drop(self, alert: PriceAlert) -> bool:
        """Check if price dropped by threshold"""
        return self._check_price_change(alert, direction="drop")

    def _check_price_increase(self, alert: PriceAlert) -> bool:
        """Check if price increased by threshold"""
        return self._check_price_change(alert, direction="increase")

    def _check_any_change(self, alert: PriceAlert) -> bool:
        """Check if price changed in any direction"""
        return self._check_price_change(alert, direction="any")

    def _check_price_change(self, alert: PriceAlert, direction: str = "any") -> bool:
        """Generic price change checker"""
        product = alert.product

        for match in product.competitor_matches:
            # Get last 2 prices
            prices = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).limit(2).all()

            if len(prices) < 2:
                continue

            latest = prices[0]
            previous = prices[1]

            if not latest.in_stock or not previous.in_stock:
                continue

            if previous.price == 0:
                continue

            # Calculate change
            change_pct = ((latest.price - previous.price) / previous.price) * 100
            change_amount = latest.price - previous.price

            # Check direction
            if direction == "drop" and change_pct >= 0:
                continue
            if direction == "increase" and change_pct <= 0:
                continue

            # Check thresholds
            if alert.threshold_pct:
                if abs(change_pct) >= alert.threshold_pct:
                    return True

            if alert.threshold_amount:
                if abs(change_amount) >= alert.threshold_amount:
                    return True

        return False

    def _check_out_of_stock(self, alert: PriceAlert) -> bool:
        """Check if any competitor went out of stock"""
        product = alert.product

        for match in product.competitor_matches:
            # Get last 2 stock statuses
            statuses = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).limit(2).all()

            if len(statuses) < 2:
                continue

            latest = statuses[0]
            previous = statuses[1]

            # Went from in-stock to out-of-stock
            if previous.in_stock and not latest.in_stock:
                return True

        return False

    def _check_price_war(self, alert: PriceAlert) -> bool:
        """Check if 3+ competitors dropped prices in last 24h"""
        product = alert.product
        yesterday = datetime.utcnow() - timedelta(hours=24)

        drops = 0
        for match in product.competitor_matches:
            # Get prices in last 24h
            recent_prices = self.db.query(PriceHistory).filter(
                and_(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= yesterday
                )
            ).order_by(PriceHistory.timestamp).all()

            if len(recent_prices) < 2:
                continue

            # Check for any price drop
            for i in range(1, len(recent_prices)):
                if recent_prices[i].price < recent_prices[i-1].price:
                    drops += 1
                    break  # Count only once per competitor

        return drops >= 3

    def _check_new_competitor(self, alert: PriceAlert) -> bool:
        """Check if new competitor was added in last 24h"""
        product = alert.product
        yesterday = datetime.utcnow() - timedelta(hours=24)

        new_matches = [
            m for m in product.competitor_matches
            if m.created_at and m.created_at >= yesterday
        ]

        return len(new_matches) > 0

    def _check_most_expensive(self, alert: PriceAlert) -> bool:
        """Check if user is most expensive among all competitors"""
        product = alert.product

        if not product.competitor_matches:
            return False

        # Get all competitor prices
        prices = []
        for match in product.competitor_matches:
            latest = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).first()

            if latest and latest.in_stock:
                prices.append(latest.price)

        if not prices:
            return False

        # Compare user's own price (my_price) against competitor prices
        if not product.my_price:
            return False

        # User is "most expensive" if every in-stock competitor is cheaper
        return all(p < product.my_price for p in prices)

    def _check_competitor_raised(self, alert: PriceAlert) -> bool:
        """Check if any competitor raised their price (opportunity!)"""
        product = alert.product

        for match in product.competitor_matches:
            # Get last 2 prices
            prices = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).limit(2).all()

            if len(prices) < 2:
                continue

            latest = prices[0]
            previous = prices[1]

            if not latest.in_stock or not previous.in_stock:
                continue

            # Price increased
            if latest.price > previous.price:
                change_pct = ((latest.price - previous.price) / previous.price) * 100

                if alert.threshold_pct and change_pct >= alert.threshold_pct:
                    return True

        return False

    def _check_back_in_stock(self, alert: PriceAlert) -> bool:
        """Check if competitor came back in stock"""
        product = alert.product

        for match in product.competitor_matches:
            # Get last 2 stock statuses
            statuses = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).limit(2).all()

            if len(statuses) < 2:
                continue

            latest = statuses[0]
            previous = statuses[1]

            # Went from out-of-stock to in-stock
            if not previous.in_stock and latest.in_stock:
                return True

        return False

    def _check_market_trend(self, alert: PriceAlert) -> bool:
        """Check if overall market price is trending up/down"""
        product = alert.product
        week_ago = datetime.utcnow() - timedelta(days=7)

        # Get average prices from week ago vs now
        old_prices = []
        new_prices = []

        for match in product.competitor_matches:
            # Get oldest and newest prices in the range
            all_prices = self.db.query(PriceHistory).filter(
                and_(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= week_ago,
                    PriceHistory.in_stock == True
                )
            ).order_by(PriceHistory.timestamp).all()

            if len(all_prices) < 2:
                continue

            old_prices.append(all_prices[0].price)
            new_prices.append(all_prices[-1].price)

        if not old_prices or not new_prices:
            return False

        old_avg = sum(old_prices) / len(old_prices)
        new_avg = sum(new_prices) / len(new_prices)

        if old_avg == 0:
            return False

        # Calculate trend
        trend_pct = ((new_avg - old_avg) / old_avg) * 100

        if alert.threshold_pct and abs(trend_pct) >= alert.threshold_pct:
            return True

        return False

    # Alert Triggering

    def _trigger_alert(self, alert: PriceAlert):
        """
        Trigger an alert - send notifications via all enabled channels
        """
        # Update alert status
        alert.last_triggered_at = datetime.utcnow()
        alert.trigger_count += 1
        self.db.commit()

        # Get alert details for notification
        alert_data = self._get_alert_data(alert)

        # Send notifications via enabled channels
        if alert.notify_email and alert.email:
            self._send_email_notification(alert, alert_data)

        if alert.notify_sms and alert.phone_number:
            self._send_sms_notification(alert, alert_data)

        if alert.notify_slack and alert.slack_webhook_url:
            self._send_slack_notification(alert, alert_data)

        if alert.notify_discord and alert.discord_webhook_url:
            self._send_discord_notification(alert, alert_data)

        if alert.notify_push:
            self._send_push_notification(alert, alert_data)

    def _get_alert_data(self, alert: PriceAlert) -> Dict[str, Any]:
        """Get detailed data for alert notification"""
        product = alert.product

        return {
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "alert_name": self.ALERT_TYPES.get(alert.alert_type, alert.alert_type),
            "product_id": product.id,
            "product_title": product.title,
            "product_sku": product.sku,
            "product_brand": product.brand,
            "competitor_count": len(product.competitor_matches),
            "threshold_pct": alert.threshold_pct,
            "threshold_amount": alert.threshold_amount,
            "triggered_at": alert.last_triggered_at,
        }

    # Notification Senders

    def _send_email_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send email notification"""
        from services.email_service import email_service

        subject = f"🚨 {data['alert_name']}: {data['product_title']}"

        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        product_url = f"{frontend_url}/products/{data['product_id']}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                     color: #1f2937; max-width: 560px; margin: 0 auto; padding: 24px;">
          <div style="background: #2563eb; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <h1 style="color: white; margin: 0; font-size: 20px;">🚨 {data['alert_name']}</h1>
          </div>
          <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 16px;">
            <p style="margin: 0 0 8px; font-size: 16px; font-weight: 600;">{data['product_title']}</p>
            <p style="margin: 0 0 4px; color: #6b7280; font-size: 14px;">SKU: {data['product_sku'] or 'N/A'} &nbsp;·&nbsp; Brand: {data['product_brand'] or 'N/A'}</p>
            <p style="margin: 8px 0 0; color: #6b7280; font-size: 14px;">Competitors tracked: {data['competitor_count']}</p>
          </div>
          <p style="text-align: center; margin: 20px 0;">
            <a href="{product_url}" style="background: #2563eb; color: white; padding: 12px 24px;
               border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;">
              View Product Details →
            </a>
          </p>
          <p style="text-align: center; font-size: 12px; color: #9ca3af;">
            &copy; MarketIntel &mdash; E-commerce Competitive Intelligence
          </p>
        </body>
        </html>
        """

        text_content = (
            f"Alert: {data['alert_name']}\n\n"
            f"Product: {data['product_title']}\n"
            f"SKU: {data['product_sku'] or 'N/A'}\n"
            f"Brand: {data['product_brand'] or 'N/A'}\n"
            f"Competitors: {data['competitor_count']}\n\n"
            f"View details: {product_url}"
        )

        try:
            email_service.send_email(
                to_email=alert.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
        except Exception as e:
            logger.error(f"Failed to send email for alert {alert.id}: {e}")

    def _send_sms_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send SMS notification — uses stdlib-based sms_service (no twilio package needed)"""
        from services.sms_service import send_sms
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        product_url = f"{frontend_url}/products/{data['product_id']}"
        message = (
            f"MarketIntel: {data['alert_name']}\n"
            f"{data['product_title'][:50]}\n"
            f"{product_url}"
        )
        try:
            send_sms(to_number=alert.phone_number, message=message)
        except Exception as e:
            logger.error(f"Failed to send SMS for alert {alert.id}: {e}")

    def _send_slack_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send Slack webhook notification — uses stdlib-based webhook_service"""
        from services.webhook_service import send_slack_alert
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        product_url = f"{frontend_url}/products/{data['product_id']}"
        try:
            send_slack_alert(
                webhook_url=alert.slack_webhook_url,
                product_title=data['product_title'],
                competitor_name=f"{data['competitor_count']} competitors",
                old_price=None,
                new_price=0.0,
                change_pct=0.0,
                product_url=product_url,
            )
        except Exception as e:
            logger.error(f"Failed to send Slack notification for alert {alert.id}: {e}")

    def _send_discord_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send Discord webhook notification — uses stdlib-based webhook_service"""
        from services.webhook_service import send_discord_alert
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        product_url = f"{frontend_url}/products/{data['product_id']}"
        try:
            send_discord_alert(
                webhook_url=alert.discord_webhook_url,
                product_title=data['product_title'],
                competitor_name=f"{data['competitor_count']} competitors",
                old_price=None,
                new_price=0.0,
                change_pct=0.0,
                product_url=product_url,
            )
        except Exception as e:
            logger.error(f"Failed to send Discord notification for alert {alert.id}: {e}")

    def _send_push_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send push notification (PWA) via Web Push / VAPID"""
        vapid_private_key = os.getenv('VAPID_PRIVATE_KEY')
        vapid_public_key = os.getenv('VAPID_PUBLIC_KEY')
        vapid_claims_email = os.getenv('VAPID_CLAIMS_EMAIL', 'alerts@marketintel.com')

        if not all([vapid_private_key, vapid_public_key]):
            logger.warning(f"VAPID keys not configured – skipping push notification for alert {alert.id}")
            return

        # Push subscription endpoint stored on the alert (or user) record would be needed.
        # For now we log the intent; the frontend registers a subscription and stores it in the DB.
        push_subscription = getattr(alert, 'push_subscription', None)
        if not push_subscription:
            logger.warning(f"No push subscription registered for alert {alert.id}")
            return

        try:
            from pywebpush import webpush, WebPushException
            import json
            payload = json.dumps({
                "title": data['alert_name'],
                "body": data['product_title'],
                "url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/products/{data['product_id']}"
            })
            webpush(
                subscription_info=push_subscription,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims={"sub": f"mailto:{vapid_claims_email}"}
            )
        except ImportError:
            logger.warning("pywebpush package not installed – skipping push notification")
        except Exception as e:
            logger.error(f"Failed to send push notification for alert {alert.id}: {e}")

    # Digest Management

    def send_daily_digest(self, user_id: int):
        """Send daily digest of all triggered alerts for a user"""
        self._send_digest(user_id, days=1, label="Daily")

    def send_weekly_digest(self, user_id: int):
        """Send weekly digest of all triggered alerts for a user"""
        self._send_digest(user_id, days=7, label="Weekly")

    def _send_digest(self, user_id: int, days: int, label: str):
        """Build and send a digest email for the given time window"""
        from services.email_service import email_service
        from database.models import User

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            return

        since = datetime.utcnow() - timedelta(days=days)

        # Alerts that triggered within the window
        triggered_alerts = self.db.query(PriceAlert).filter(
            PriceAlert.user_id == user_id,
            PriceAlert.last_triggered_at >= since
        ).all()

        if not triggered_alerts:
            return  # Nothing to report

        # Build top price drops / increases from recent price history
        top_drops = []
        top_increases = []

        for alert in triggered_alerts:
            product = alert.product
            for match in product.competitor_matches:
                prices = self.db.query(PriceHistory).filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= since
                ).order_by(PriceHistory.timestamp).all()

                if len(prices) < 2:
                    continue

                first_price = prices[0].price
                last_price = prices[-1].price
                change_pct = ((last_price - first_price) / first_price) * 100 if first_price else 0

                entry = {
                    "product": product.title,
                    "competitor": match.competitor_name,
                    "new_price": last_price,
                    "change_pct": abs(change_pct),
                }
                if change_pct < -1:
                    top_drops.append(entry)
                elif change_pct > 1:
                    top_increases.append(entry)

        # Sort by magnitude
        top_drops.sort(key=lambda x: x["change_pct"], reverse=True)
        top_increases.sort(key=lambda x: x["change_pct"], reverse=True)

        stats = {
            "products_monitored": self.db.query(ProductMonitored).filter(
                ProductMonitored.user_id == user_id
            ).count(),
            "price_updates": self.db.query(PriceHistory).join(CompetitorMatch).join(
                ProductMonitored
            ).filter(
                ProductMonitored.user_id == user_id,
                PriceHistory.timestamp >= since
            ).count(),
            "competitors_tracked": self.db.query(CompetitorMatch).join(
                ProductMonitored
            ).filter(
                ProductMonitored.user_id == user_id
            ).count(),
        }

        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        try:
            email_service.send_daily_digest(
                to_email=user.email,
                date=f"{label} Digest – {date_str}",
                stats=stats,
                top_price_drops=top_drops[:5],
                top_price_increases=top_increases[:5],
            )
        except Exception as e:
            logger.error(f"Failed to send {label.lower()} digest to user {user_id}: {e}")


# Factory function
def get_smart_alert_service(db: Session) -> SmartAlertService:
    """Get instance of SmartAlertService"""
    return SmartAlertService(db)
