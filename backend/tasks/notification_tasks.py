"""
Notification Background Tasks
Handles email alerts and daily digests
"""

import concurrent.futures
import os

from celery_app import celery_app
from tasks.scraping_tasks import DatabaseTask
from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory, PriceAlert,
    NotificationLog, PendingPriceChange, MyPriceHistory,
)
from services.email_service import email_service
from services.webhook_service import send_slack_alert, send_discord_alert, send_slack_digest
from services.sms_service import send_price_alert_sms
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _fire_notifications(jobs: list) -> list:
    """
    Execute a list of notification jobs in parallel.

    Each job is a 2- or 3-tuple:
        (callable, kwargs)                       — no logging metadata
        (callable, kwargs, meta: dict)            — meta has keys:
            channel   str           e.g. "email", "sms", "slack"
            alert_id  Optional[int]
            user_id   Optional[int]

    Returns a list of result dicts (one per job) with keys:
        channel, alert_id, user_id, status ("sent"|"failed"|"timeout"), error
    These can be bulk-inserted into notification_logs by the caller.
    """
    if not jobs:
        return []

    results: list = [None] * len(jobs)

    def _run(idx, job):
        fn = job[0]
        kwargs = job[1]
        meta = job[2] if len(job) > 2 else {}
        try:
            fn(**kwargs)
            results[idx] = {**meta, "status": "sent", "error": None}
        except Exception as e:
            logger.error("Notification send failed (%s): %s", fn.__name__, e)
            results[idx] = {**meta, "status": "failed", "error": str(e)[:500]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(jobs), 10)) as pool:
        futures = {pool.submit(_run, i, job): i for i, job in enumerate(jobs)}
        done, not_done = concurrent.futures.wait(futures, timeout=30)
        for future in not_done:
            idx = futures[future]
            job = jobs[idx]
            meta = job[2] if len(job) > 2 else {}
            results[idx] = {**meta, "status": "timeout", "error": "job timed out after 30s"}
            future.cancel()
            logger.warning("Notification job timed out and was cancelled")

    return [r for r in results if r is not None]


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
                    # Quiet hours check — skip if user configured a do-not-disturb window
                    if rule.is_in_quiet_hours():
                        continue

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

                    # Build per-channel kwargs explicitly — each service has a
                    # slightly different signature (email uses "competitor",
                    # webhooks use "competitor_name").  Explicit dicts are
                    # easier to trace than the filter-and-spread approach.
                    _meta = {"alert_id": rule.id, "user_id": rule.user_id}
                    if rule.notify_email and rule.email:
                        notifications.append((email_service.send_price_alert, {
                            "to_email": rule.email,
                            "product_title": product.title,
                            "competitor": match.competitor_name,
                            "old_price": previous_price,
                            "new_price": current_price,
                            "change_pct": change_pct,
                            "product_url": product_url,
                        }, {**_meta, "channel": "email"}))
                    if rule.notify_slack and rule.slack_webhook_url:
                        notifications.append((send_slack_alert, {
                            "webhook_url": rule.slack_webhook_url,
                            "product_title": product.title,
                            "competitor_name": match.competitor_name,
                            "old_price": previous_price,
                            "new_price": current_price,
                            "change_pct": change_pct,
                            "product_url": product_url,
                        }, {**_meta, "channel": "slack"}))
                    if rule.notify_discord and rule.discord_webhook_url:
                        notifications.append((send_discord_alert, {
                            "webhook_url": rule.discord_webhook_url,
                            "product_title": product.title,
                            "competitor_name": match.competitor_name,
                            "old_price": previous_price,
                            "new_price": current_price,
                            "change_pct": change_pct,
                            "product_url": product_url,
                        }, {**_meta, "channel": "discord"}))
                    if rule.notify_sms and rule.phone_number:
                        notifications.append((send_price_alert_sms, {
                            "to_number": rule.phone_number,
                            "product_title": product.title,
                            "competitor_name": match.competitor_name,
                            "new_price": current_price,
                            "change_pct": change_pct,
                            "product_url": product_url,
                        }, {**_meta, "channel": "sms"}))

                    rule.last_triggered_at = now
                    rules_to_update.append(rule)

        # ── 5. Fire all notifications in parallel ─────────────────────────────
        delivery_results = _fire_notifications(notifications)

        # ── 6. Persist delivery log + rule timestamp updates in one commit ────
        for r in delivery_results:
            self.db.add(NotificationLog(
                alert_id=r.get("alert_id"),
                user_id=r.get("user_id"),
                channel=r.get("channel", "unknown"),
                status=r["status"],
                error_message=r.get("error"),
            ))
        if rules_to_update or delivery_results:
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

        # Fetch the two most recent price history entries to compute the actual change
        recent_history = (
            self.db.query(PriceHistory)
            .filter(PriceHistory.match_id == match_id)
            .order_by(PriceHistory.timestamp.desc())
            .limit(2)
            .all()
        )
        new_price = match.latest_price or 0
        old_price = recent_history[1].price if len(recent_history) >= 2 else new_price
        change_pct = round(((new_price - old_price) / old_price) * 100, 1) if old_price else 0

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
                "old_price": old_price,
                "new_price": new_price,
                "change_pct": change_pct,
                "product_url": product_url,
            })
            for rule in alert_rules if rule.email
        ]
        _fire_notifications(jobs)

        return {"success": True, "alert_sent": True, "data": alert_data}

    except Exception as e:
        logger.error("Error sending price drop alert: %s", e)
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True, name="tasks.notification_tasks.send_pending_approvals")
def send_pending_approvals(self):
    """Notify users of pending price change suggestions and expire stale ones.

    Runs every 30 minutes. Sends email for changes that haven't been notified yet.
    Marks as expired when expires_at has passed.
    """
    now = datetime.utcnow()
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    api_url = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")

    expired = self.db.query(PendingPriceChange).filter(
        PendingPriceChange.status == "pending",
        PendingPriceChange.expires_at < now,
    ).all()
    for change in expired:
        change.status = "expired"
    if expired:
        self.db.commit()

    to_notify = self.db.query(PendingPriceChange).filter(
        PendingPriceChange.status == "pending",
        PendingPriceChange.notified_at.is_(None),
        PendingPriceChange.expires_at > now,
    ).all()

    product_ids = [c.product_id for c in to_notify]
    if not product_ids:
        return {"expired": len(expired), "notified": 0}

    products = {p.id: p for p in self.db.query(ProductMonitored).filter(
        ProductMonitored.id.in_(product_ids)
    ).all()}

    from database.models import User
    user_ids = list({p.user_id for p in products.values() if p.user_id})
    users = {u.id: u for u in self.db.query(User).filter(User.id.in_(user_ids)).all()}

    notified = 0
    for change in to_notify:
        product = products.get(change.product_id)
        if not product:
            continue
        user = users.get(product.user_id)
        if not user or not user.email:
            continue

        base = f"{api_url}/api/repricing/pending/approve-link"
        approve_url = f"{base}?id={change.id}&token={change.approval_token}&action=approve"
        reject_url  = f"{base}?id={change.id}&token={change.approval_token}&action=reject"

        try:
            email_service.send_approval_request(
                to_email=user.email,
                product_title=product.title,
                current_price=change.current_price,
                suggested_price=change.suggested_price,
                reason=change.reason or "Repricing rule triggered",
                margin_pct=change.margin_at_suggested,
                approve_url=approve_url,
                reject_url=reject_url,
            )
            change.notified_at = now
            notified += 1
        except Exception as exc:
            logger.warning("Failed to send approval email for change %s: %s", change.id, exc)

    self.db.commit()
    return {"expired": len(expired), "notified": notified}


@celery_app.task(base=DatabaseTask, bind=True, name="tasks.notification_tasks.auto_apply_approved")
def auto_apply_approved(self):
    """Apply approved PendingPriceChanges to products and push to stores.

    Runs every 10 minutes. Applies all changes with status='approved', writes
    MyPriceHistory, attempts Shopify/WooCommerce sync if connected.
    """
    now = datetime.utcnow()

    approved = self.db.query(PendingPriceChange).filter(
        PendingPriceChange.status == "approved",
    ).limit(100).all()

    if not approved:
        return {"applied": 0}

    product_ids = [c.product_id for c in approved]
    products = {p.id: p for p in self.db.query(ProductMonitored).filter(
        ProductMonitored.id.in_(product_ids)
    ).all()}

    applied = 0
    for change in approved:
        product = products.get(change.product_id)
        if not product:
            change.status = "error"
            continue
        old_price = product.my_price
        product.my_price = change.suggested_price
        history = MyPriceHistory(
            product_id=product.id,
            workspace_id=product.workspace_id,
            old_price=old_price,
            new_price=change.suggested_price,
            note=f"Auto-applied: {change.reason or 'repricing rule'}",
        )
        self.db.add(history)
        change.status = "applied"
        change.applied_at = now
        applied += 1

        try:
            _push_price_to_store(product, change.suggested_price, self.db)
        except Exception as exc:
            logger.warning("Store sync failed for product %s: %s", product.id, exc)

    self.db.commit()
    return {"applied": applied}


def _push_price_to_store(product: ProductMonitored, new_price: float, db) -> None:
    """Best-effort push of new price to Shopify or WooCommerce if connected."""
    if not product.source_id:
        return
    from database.models import StoreConnection
    connections = db.query(StoreConnection).filter(
        StoreConnection.workspace_id == product.workspace_id,
        StoreConnection.is_active == True,
    ).all()
    for conn in connections:
        try:
            if conn.platform == "shopify":
                from integrations.shopify_integration import ShopifyIntegration
                ShopifyIntegration(conn).update_product_price(product.source_id, new_price)
            elif conn.platform == "woocommerce":
                from integrations.woocommerce_integration import WooCommerceIntegration
                WooCommerceIntegration(conn).update_product_price(product.source_id, new_price)
        except Exception as exc:
            logger.warning("Price push to %s failed: %s", conn.platform, exc)
