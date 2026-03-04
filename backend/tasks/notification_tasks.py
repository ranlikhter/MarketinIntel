"""
Notification Background Tasks
Handles email alerts and daily digests
"""

import concurrent.futures
import os

from celery_app import celery_app
from tasks.scraping_tasks import DatabaseTask
from database.models import ProductMonitored, CompetitorMatch, PriceHistory, PriceAlert
from services.email_service import email_service
from services.webhook_service import send_slack_alert, send_discord_alert, send_slack_digest
from services.sms_service import send_price_alert_sms
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _fire_notifications(jobs: list):
    """
    Execute a list of (callable, kwargs) notification jobs in parallel using
    a thread pool.  Each job is independent I/O (SMTP / HTTP webhook / SMS)
    so parallelism is safe and effective here.
    """
    if not jobs:
        return

    def _run(job):
        fn, kwargs = job
        try:
            fn(**kwargs)
        except Exception as e:
            logger.error("Notification send failed (%s): %s", fn.__name__, e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(jobs), 10)) as pool:
        concurrent.futures.wait(
            [pool.submit(_run, job) for job in jobs],
            timeout=30,
        )


@celery_app.task(base=DatabaseTask, bind=True)
def check_price_alerts(self, threshold_pct: float = 5.0):
    """
    Check for significant price changes and send alerts.

    Performance overhaul vs. the previous version:
      - Was:  1 query (all products) + N queries (matches per product)
              + M queries (prices per match) + K queries (alert rules per product)
              = O(N×M + K) DB round-trips
      - Now:  4 flat queries (products+matches via joinedload, batch prices,
              batch alert rules), then pure-Python logic
              = 4 DB round-trips regardless of scale
      - Notification I/O (email / Slack / Discord / SMS) now runs in parallel
        via ThreadPoolExecutor instead of sequentially.
    """
    try:
        logger.info("Checking price alerts (threshold: %.1f%%)", threshold_pct)

        yesterday = datetime.utcnow() - timedelta(days=1)

        # ── 1. Load all products with their matches in two queries ────────────
        products = (
            self.db.query(ProductMonitored)
            .options(joinedload(ProductMonitored.competitor_matches))
            .all()
        )

        all_match_ids = [m.id for p in products for m in p.competitor_matches]
        if not all_match_ids:
            return {"success": True, "alerts_found": 0, "alerts": []}

        # ── 2. Batch-load the last 24 h of prices for every match ─────────────
        prices_by_match: dict[int, list] = {}
        for ph in (
            self.db.query(PriceHistory)
            .filter(
                PriceHistory.match_id.in_(all_match_ids),
                PriceHistory.timestamp >= yesterday,
            )
            .order_by(PriceHistory.match_id, PriceHistory.timestamp.desc())
            .all()
        ):
            prices_by_match.setdefault(ph.match_id, []).append(ph)

        # ── 3. Batch-load all enabled alert rules keyed by product_id ─────────
        rules_by_product: dict[int, list] = {}
        for rule in (
            self.db.query(PriceAlert)
            .filter(PriceAlert.enabled == True)  # noqa: E712
            .all()
        ):
            rules_by_product.setdefault(rule.product_id, []).append(rule)

        # ── 4. Evaluate alerts — pure Python, no more DB calls in the loop ────
        alerts = []
        now = datetime.utcnow()
        notifications = []   # (callable, kwargs) pairs for parallel dispatch
        rules_to_update = []

        for product in products:
            product_url = f"{_FRONTEND_URL}/products/{product.id}"
            rules = rules_by_product.get(product.id, [])

            for match in product.competitor_matches:
                recent = prices_by_match.get(match.id, [])
                if len(recent) < 2:
                    continue

                current_price = recent[0].price
                previous_price = recent[-1].price
                if not (current_price and previous_price):
                    continue

                change_pct = (current_price - previous_price) / previous_price * 100
                if abs(change_pct) < threshold_pct:
                    continue

                alerts.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "competitor": match.competitor_name,
                    "previous_price": previous_price,
                    "current_price": current_price,
                    "change_pct": change_pct,
                    "timestamp": now.isoformat(),
                })

                for rule in rules:
                    # Cooldown check (pure Python — no extra query)
                    if rule.last_triggered_at:
                        cooldown_end = rule.last_triggered_at + timedelta(hours=rule.cooldown_hours)
                        if now < cooldown_end:
                            continue

                    # Alert type filter
                    if rule.alert_type == "price_drop" and not (change_pct < 0 and abs(change_pct) >= rule.threshold_pct):
                        continue
                    if rule.alert_type == "price_increase" and not (change_pct > 0 and change_pct >= rule.threshold_pct):
                        continue
                    if rule.alert_type == "any_change" and abs(change_pct) < rule.threshold_pct:
                        continue

                    # Queue notification sends
                    common = dict(
                        product_title=product.title,
                        competitor=match.competitor_name,
                        old_price=previous_price,
                        new_price=current_price,
                        change_pct=change_pct,
                        product_url=product_url,
                    )
                    if rule.notify_email and rule.email:
                        notifications.append((email_service.send_price_alert, {**common, "to_email": rule.email}))
                    if rule.notify_slack and rule.slack_webhook_url:
                        notifications.append((send_slack_alert, {
                            "webhook_url": rule.slack_webhook_url,
                            "competitor_name": match.competitor_name,
                            **{k: v for k, v in common.items() if k != "competitor"},
                        }))
                    if rule.notify_discord and rule.discord_webhook_url:
                        notifications.append((send_discord_alert, {
                            "webhook_url": rule.discord_webhook_url,
                            "competitor_name": match.competitor_name,
                            **{k: v for k, v in common.items() if k != "competitor"},
                        }))
                    if rule.notify_sms and rule.phone_number:
                        notifications.append((send_price_alert_sms, {
                            "to_number": rule.phone_number,
                            "product_title": product.title,
                            "competitor_name": match.competitor_name,
                            "new_price": current_price,
                            "change_pct": change_pct,
                            "product_url": product_url,
                        }))

                    rule.last_triggered_at = now
                    rules_to_update.append(rule)

        # ── 5. Fire all notifications in parallel ─────────────────────────────
        _fire_notifications(notifications)

        # ── 6. Single commit for all rule timestamp updates ───────────────────
        if rules_to_update:
            self.db.commit()

        logger.info("Price alert check: %d alerts, %d notifications dispatched", len(alerts), len(notifications))

        return {
            "success": True,
            "alerts_found": len(alerts),
            "alerts": alerts,
        }

    except Exception as e:
        logger.error("Error checking price alerts: %s", e)
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_daily_digest(self):
    """
    Send daily digest email with price summary.
    """
    try:
        logger.info("Generating daily digest")

        yesterday = datetime.utcnow() - timedelta(days=1)

        # Count products scraped (distinct) — single query with COUNT DISTINCT
        scraped_count = (
            self.db.query(func.count(func.distinct(CompetitorMatch.monitored_product_id)))
            .filter(CompetitorMatch.last_scraped_at >= yesterday)
            .scalar()
        ) or 0

        price_changes = (
            self.db.query(func.count(PriceHistory.id))
            .filter(PriceHistory.timestamp >= yesterday)
            .scalar()
        ) or 0

        competitor_count = (
            self.db.query(func.count(func.distinct(CompetitorMatch.competitor_name)))
            .scalar()
        ) or 0

        # Recipients — collected in two queries
        alert_emails = (
            self.db.query(PriceAlert.email)
            .filter(PriceAlert.enabled == True, PriceAlert.email.isnot(None))  # noqa: E712
            .distinct()
            .all()
        )
        if not alert_emails:
            logger.warning("No email recipients found for daily digest")
            return {"success": True, "message": "No recipients configured"}

        slack_webhooks = (
            self.db.query(PriceAlert.slack_webhook_url)
            .filter(
                PriceAlert.enabled == True,  # noqa: E712
                PriceAlert.notify_slack == True,  # noqa: E712
                PriceAlert.slack_webhook_url.isnot(None),
                PriceAlert.digest_frequency == "daily",
            )
            .distinct()
            .all()
        )

        digest_data = {
            "date": datetime.utcnow().date().isoformat(),
            "stats": {
                "products_monitored": scraped_count,
                "price_updates": price_changes,
                "competitors_tracked": competitor_count,
            },
        }

        # Build notification jobs and fire in parallel
        jobs = []
        for (email,) in alert_emails:
            jobs.append((email_service.send_daily_digest, {
                "to_email": email,
                "date": digest_data["date"],
                "stats": digest_data["stats"],
                "top_price_drops": [],
                "top_price_increases": [],
            }))
        for (slack_url,) in slack_webhooks:
            jobs.append((send_slack_digest, {
                "webhook_url": slack_url,
                "date": digest_data["date"],
                "stats": digest_data["stats"],
                "top_drops": [],
                "top_increases": [],
            }))

        _fire_notifications(jobs)

        emails_sent = len(alert_emails)
        logger.info("Daily digest sent to %d recipients", emails_sent)

        return {
            "success": True,
            "emails_sent": emails_sent,
            "digest": digest_data,
        }

    except Exception as e:
        logger.error("Error generating daily digest: %s", e)
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_price_drop_alert(self, product_id: int, match_id: int):
    """
    Send immediate alert for a significant price drop.
    Dispatches all channels in parallel.
    """
    try:
        product = self.db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()
        match = self.db.query(CompetitorMatch).filter(CompetitorMatch.id == match_id).first()

        if not product or not match:
            return {"success": False, "error": "Product or match not found"}

        alert_data = {
            "product_title": product.title,
            "competitor": match.competitor_name,
            "current_price": match.latest_price,
            "url": match.competitor_url,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info("Price drop alert for %s: $%s", product.title, match.latest_price)

        product_url = f"{_FRONTEND_URL}/products/{product_id}"
        alert_rules = (
            self.db.query(PriceAlert)
            .filter(
                PriceAlert.product_id == product_id,
                PriceAlert.enabled == True,  # noqa: E712
                PriceAlert.notify_email == True,  # noqa: E712
            )
            .all()
        )

        jobs = [
            (email_service.send_price_alert, {
                "to_email": rule.email,
                "product_title": product.title,
                "competitor": match.competitor_name,
                "old_price": match.latest_price or 0,
                "new_price": match.latest_price or 0,
                "change_pct": 0,
                "product_url": product_url,
            })
            for rule in alert_rules if rule.email
        ]
        _fire_notifications(jobs)

        return {"success": True, "alert_sent": True, "data": alert_data}

    except Exception as e:
        logger.error("Error sending price drop alert: %s", e)
        return {"success": False, "error": str(e)}
