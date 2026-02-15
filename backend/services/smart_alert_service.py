"""
Smart Alert Service
Handles intelligent alert detection and multi-channel notifications
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

from database.models import (
    PriceAlert, ProductMonitored, CompetitorMatch,
    PriceHistory, User
)


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

        # Simplified: In real implementation, compare with user's actual price
        # For now, check if average competitor price is lower
        avg_competitor_price = sum(prices) / len(prices)

        # This is placeholder logic - needs user's actual product price
        # Assuming user's price is stored somewhere or we need to add it
        return False  # TODO: Implement with actual user price comparison

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

        body = f"""
        Alert Triggered: {data['alert_name']}

        Product: {data['product_title']}
        SKU: {data['product_sku'] or 'N/A'}
        Brand: {data['product_brand'] or 'N/A'}

        Competitors: {data['competitor_count']}
        Threshold: {data['threshold_pct']}%

        Triggered at: {data['triggered_at']}

        View details: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/products/{data['product_id']}
        """

        try:
            email_service.send_email(
                to_email=alert.email,
                subject=subject,
                body=body
            )
        except Exception as e:
            print(f"Failed to send email for alert {alert.id}: {e}")

    def _send_sms_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send SMS notification via Twilio"""
        # TODO: Implement Twilio SMS
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=f"{data['alert_name']}: {data['product_title']}",
        #     from_=os.getenv('TWILIO_PHONE_NUMBER'),
        #     to=alert.phone_number
        # )
        pass

    def _send_slack_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send Slack webhook notification"""
        import requests

        payload = {
            "text": f"🚨 *{data['alert_name']}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {data['alert_name']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Product:*\n{data['product_title']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Competitors:*\n{data['competitor_count']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Threshold:*\n{data['threshold_pct']}%"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Details"
                            },
                            "url": f"{os.getenv('FRONTEND_URL')}/products/{data['product_id']}"
                        }
                    ]
                }
            ]
        }

        try:
            requests.post(alert.slack_webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to send Slack notification for alert {alert.id}: {e}")

    def _send_discord_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send Discord webhook notification"""
        import requests

        payload = {
            "embeds": [{
                "title": f"🚨 {data['alert_name']}",
                "description": f"**{data['product_title']}**",
                "color": 15158332,  # Red color
                "fields": [
                    {
                        "name": "SKU",
                        "value": data['product_sku'] or "N/A",
                        "inline": True
                    },
                    {
                        "name": "Competitors",
                        "value": str(data['competitor_count']),
                        "inline": True
                    },
                    {
                        "name": "Threshold",
                        "value": f"{data['threshold_pct']}%",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Triggered at {data['triggered_at']}"
                }
            }]
        }

        try:
            requests.post(alert.discord_webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to send Discord notification for alert {alert.id}: {e}")

    def _send_push_notification(self, alert: PriceAlert, data: Dict[str, Any]):
        """Send push notification (PWA)"""
        # TODO: Implement web push notifications
        # Requires setting up push notification service
        pass

    # Digest Management

    def send_daily_digest(self, user_id: int):
        """Send daily digest of all triggered alerts"""
        # TODO: Implement digest logic
        pass

    def send_weekly_digest(self, user_id: int):
        """Send weekly digest of all triggered alerts"""
        # TODO: Implement digest logic
        pass


# Factory function
def get_smart_alert_service(db: Session) -> SmartAlertService:
    """Get instance of SmartAlertService"""
    return SmartAlertService(db)
