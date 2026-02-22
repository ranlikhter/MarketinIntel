"""
Notification Background Tasks
Handles email alerts and daily digests
"""

import os

from celery_app import celery_app
from tasks.scraping_tasks import DatabaseTask
from database.models import ProductMonitored, CompetitorMatch, PriceHistory, PriceAlert
from services.email_service import email_service
from services.webhook_service import send_slack_alert, send_discord_alert, send_slack_digest
from services.sms_service import send_price_alert_sms
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(base=DatabaseTask, bind=True)
def check_price_alerts(self, threshold_pct: float = 5.0):
    """
    Check for significant price changes and send alerts

    Args:
        threshold_pct: Percentage change threshold to trigger alert
    """
    try:
        logger.info(f"Checking price alerts (threshold: {threshold_pct}%)")

        alerts = []
        products = self.db.query(ProductMonitored).all()

        for product in products:
            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.product_id == product.id
            ).all()

            for match in matches:
                # Get price history for last 24 hours
                yesterday = datetime.utcnow() - timedelta(days=1)

                recent_prices = self.db.query(PriceHistory).filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= yesterday
                ).order_by(PriceHistory.timestamp.desc()).limit(10).all()

                if len(recent_prices) < 2:
                    continue

                # Calculate price change
                current_price = recent_prices[0].price
                previous_price = recent_prices[-1].price

                if previous_price and current_price:
                    change_pct = ((current_price - previous_price) / previous_price) * 100

                    if abs(change_pct) >= threshold_pct:
                        alert_data = {
                            'product_id': product.id,
                            'product_title': product.title,
                            'competitor': match.competitor_name,
                            'previous_price': previous_price,
                            'current_price': current_price,
                            'change_pct': change_pct,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        alerts.append(alert_data)

                        # Get alert rules for this product
                        alert_rules = self.db.query(PriceAlert).filter(
                            PriceAlert.product_id == product.id,
                            PriceAlert.enabled == True
                        ).all()

                        # Send emails for matching rules
                        for rule in alert_rules:
                            # Check cooldown
                            if rule.last_triggered_at:
                                cooldown_end = rule.last_triggered_at + timedelta(hours=rule.cooldown_hours)
                                if datetime.utcnow() < cooldown_end:
                                    continue  # Skip - still in cooldown

                            # Check if this alert should trigger
                            should_trigger = False
                            if rule.alert_type == "price_drop" and change_pct < 0:
                                should_trigger = abs(change_pct) >= rule.threshold_pct
                            elif rule.alert_type == "price_increase" and change_pct > 0:
                                should_trigger = change_pct >= rule.threshold_pct
                            elif rule.alert_type == "any_change":
                                should_trigger = abs(change_pct) >= rule.threshold_pct

                            if should_trigger:
                                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                                product_url = f"{frontend_url}/products/{product.id}"

                                # Send email
                                if rule.notify_email and rule.email:
                                    email_service.send_price_alert(
                                        to_email=rule.email,
                                        product_title=product.title,
                                        competitor=match.competitor_name,
                                        old_price=previous_price,
                                        new_price=current_price,
                                        change_pct=change_pct,
                                        product_url=product_url
                                    )

                                # Send Slack notification
                                if rule.notify_slack and rule.slack_webhook_url:
                                    try:
                                        send_slack_alert(
                                            webhook_url=rule.slack_webhook_url,
                                            product_title=product.title,
                                            competitor_name=match.competitor_name,
                                            old_price=previous_price,
                                            new_price=current_price,
                                            change_pct=change_pct,
                                            product_url=product_url,
                                        )
                                    except Exception as slack_err:
                                        logger.error(f"Slack webhook failed: {slack_err}")

                                # Send Discord notification
                                if rule.notify_discord and rule.discord_webhook_url:
                                    try:
                                        send_discord_alert(
                                            webhook_url=rule.discord_webhook_url,
                                            product_title=product.title,
                                            competitor_name=match.competitor_name,
                                            old_price=previous_price,
                                            new_price=current_price,
                                            change_pct=change_pct,
                                            product_url=product_url,
                                        )
                                    except Exception as discord_err:
                                        logger.error(f"Discord webhook failed: {discord_err}")

                                # Send SMS notification
                                if rule.notify_sms and rule.phone_number:
                                    try:
                                        send_price_alert_sms(
                                            to_number=rule.phone_number,
                                            product_title=product.title,
                                            competitor_name=match.competitor_name,
                                            new_price=current_price,
                                            change_pct=change_pct,
                                            product_url=product_url,
                                        )
                                    except Exception as sms_err:
                                        logger.error(f"SMS alert failed: {sms_err}")

                                # Update last triggered
                                rule.last_triggered_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Found {len(alerts)} price alerts and sent notifications")

        return {
            'success': True,
            'alerts_found': len(alerts),
            'alerts': alerts
        }

    except Exception as e:
        logger.error(f"Error checking price alerts: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_daily_digest(self):
    """
    Send daily digest email with price summary
    """
    try:
        logger.info("Generating daily digest")

        # Get stats for last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Count products scraped
        scraped_count = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.last_scraped_at >= yesterday
        ).distinct(CompetitorMatch.product_id).count()

        # Count price changes
        price_changes = self.db.query(PriceHistory).filter(
            PriceHistory.timestamp >= yesterday
        ).count()

        # Get biggest price drops and increases
        # Query recent price changes
        top_drops = []
        top_increases = []

        # Get all active alerts to find email recipients
        alert_emails = self.db.query(PriceAlert.email).filter(
            PriceAlert.enabled == True
        ).distinct().all()

        if not alert_emails:
            logger.warning("No email recipients found for daily digest")
            return {'success': True, 'message': 'No recipients configured'}

        digest_data = {
            'date': datetime.utcnow().date().isoformat(),
            'stats': {
                'products_monitored': scraped_count,
                'price_updates': price_changes,
                'competitors_tracked': self.db.query(CompetitorMatch.competitor_name).distinct().count()
            }
        }

        # Send digest to each unique email + Slack webhook
        emails_sent = 0
        slack_webhooks_sent = 0
        slack_webhooks = self.db.query(PriceAlert.slack_webhook_url).filter(
            PriceAlert.enabled == True,
            PriceAlert.notify_slack == True,
            PriceAlert.slack_webhook_url != None,
            PriceAlert.digest_frequency == 'daily',
        ).distinct().all()

        for (email,) in alert_emails:
            try:
                email_service.send_daily_digest(
                    to_email=email,
                    date=digest_data['date'],
                    stats=digest_data['stats'],
                    top_price_drops=top_drops,
                    top_price_increases=top_increases
                )
                emails_sent += 1
            except Exception as e:
                logger.error(f"Failed to send digest to {email}: {e}")

        for (slack_url,) in slack_webhooks:
            try:
                send_slack_digest(
                    webhook_url=slack_url,
                    date=digest_data['date'],
                    stats=digest_data['stats'],
                    top_drops=top_drops,
                    top_increases=top_increases,
                )
                slack_webhooks_sent += 1
            except Exception as e:
                logger.error(f"Failed to send Slack digest to {slack_url}: {e}")

        logger.info(f"Daily digest sent to {emails_sent} recipients")

        return {
            'success': True,
            'emails_sent': emails_sent,
            'digest': digest_data
        }

    except Exception as e:
        logger.error(f"Error generating daily digest: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_price_drop_alert(self, product_id: int, match_id: int):
    """
    Send immediate alert for significant price drop

    Args:
        product_id: Product that had price drop
        match_id: Competitor match with the price drop
    """
    try:
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id
        ).first()

        match = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.id == match_id
        ).first()

        if not product or not match:
            return {'success': False, 'error': 'Product or match not found'}

        alert_data = {
            'product_title': product.title,
            'competitor': match.competitor_name,
            'current_price': match.latest_price,
            'url': match.competitor_url,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"Price drop alert for {product.title}: ${match.latest_price}")

        # Send email to all active alert rules for this product
        alert_rules = self.db.query(PriceAlert).filter(
            PriceAlert.product_id == product_id,
            PriceAlert.enabled == True,
            PriceAlert.notify_email == True,
        ).all()

        for rule in alert_rules:
            if not rule.email:
                continue
            try:
                email_service.send_price_alert(
                    to_email=rule.email,
                    product_title=product.title,
                    competitor=match.competitor_name,
                    old_price=match.latest_price or 0,
                    new_price=match.latest_price or 0,
                    change_pct=0,
                    product_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/products/{product_id}"
                )
            except Exception as e:
                logger.error(f"Failed to send email for rule {rule.id}: {e}")

        return {
            'success': True,
            'alert_sent': True,
            'data': alert_data
        }

    except Exception as e:
        logger.error(f"Error sending price drop alert: {e}")
        return {'success': False, 'error': str(e)}
