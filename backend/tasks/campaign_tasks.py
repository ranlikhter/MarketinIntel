"""
Campaign Price Scheduler Tasks

Runs every 60 seconds via Celery beat.  Starts campaigns whose starts_at has
arrived and ends campaigns whose ends_at has passed, reverting prices to their
pre-campaign values.
"""

import logging
from datetime import datetime
from typing import Optional

from celery import Task
from celery_app import celery_app
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import (
    CampaignProductSnapshot,
    MyPriceHistory,
    PriceCampaign,
    ProductMonitored,
)

logger = logging.getLogger(__name__)

_MAX_PRODUCTS_PER_CAMPAIGN = 5_000  # safety cap


# ── Base task (same DatabaseTask pattern as scraping_tasks.py:89) ─────────────

class DatabaseTask(Task):
    _db: Session = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_new_price(current_price: float, rules: list) -> Optional[float]:
    """Apply the first matching rule from the campaign rules list."""
    for rule in rules:
        rule_type = rule.get("type", "")
        value = rule.get("value")
        if value is None:
            continue
        if rule_type == "discount_pct":
            return round(current_price * (1 - float(value) / 100), 2)
        if rule_type == "discount_fixed":
            return round(max(current_price - float(value), 0.01), 2)
        if rule_type == "set_price":
            return round(float(value), 2)
    return None


def _floor_for_product(product: ProductMonitored) -> Optional[float]:
    """Inline floor calculation — avoids importing full RepricingService."""
    cost = getattr(product, "cost_price", None)
    margin = getattr(product, "target_margin_pct", None)
    if cost and margin and 0 < margin < 100:
        return cost / (1 - margin / 100)
    candidates = [p for p in [product.min_price, product.map_price] if p]
    return max(candidates) if candidates else None


def _match_product_filter(product: ProductMonitored, product_filter: Optional[dict]) -> bool:
    """Return True if the product matches the campaign's filter spec."""
    if not product_filter or product_filter.get("all"):
        return True
    if "category" in product_filter:
        cat = (product.category or "").lower()
        if product_filter["category"].lower() not in cat:
            return False
    if "tags" in product_filter:
        product_tags = [t.lower() for t in (product.tags or [])]
        if not any(t.lower() in product_tags for t in product_filter["tags"]):
            return False
    if "skus" in product_filter:
        if (product.sku or "").lower() not in [s.lower() for s in product_filter["skus"]]:
            return False
    return True


def _start_campaign(db: Session, campaign: PriceCampaign, now: datetime) -> None:
    """Apply campaign prices to all matching products and record snapshots."""
    from tasks.notification_tasks import _push_price_to_store
    from services.activity_service import log_activity

    products = (
        db.query(ProductMonitored)
        .filter(
            ProductMonitored.workspace_id == campaign.workspace_id,
            ProductMonitored.my_price.isnot(None),
            ProductMonitored.status == "active",
        )
        .limit(_MAX_PRODUCTS_PER_CAMPAIGN)
        .all()
    )

    affected = 0
    for product in products:
        if not _match_product_filter(product, campaign.product_filter):
            continue

        new_price = _compute_new_price(product.my_price, campaign.rules or [])
        if new_price is None:
            continue

        # Clamp to margin floor — never breach it
        floor = _floor_for_product(product)
        if floor and new_price < floor:
            new_price = round(floor, 2)

        # Skip if price wouldn't change
        if abs(new_price - product.my_price) < 0.001:
            continue

        snapshot = CampaignProductSnapshot(
            campaign_id=campaign.id,
            product_id=product.id,
            price_before=product.my_price,
            price_applied=new_price,
        )
        db.add(snapshot)
        db.flush()  # get snapshot.id

        old_price = product.my_price
        product.my_price = new_price
        db.add(MyPriceHistory(
            product_id=product.id,
            workspace_id=product.workspace_id,
            old_price=old_price,
            new_price=new_price,
            note=f"Campaign: {campaign.name}",
        ))

        try:
            _push_price_to_store(product, new_price, db)
            snapshot.pushed_at = now
        except Exception:
            logger.warning("Store push failed for product %d in campaign %d", product.id, campaign.id)

        affected += 1

    campaign.status = "running"
    campaign.products_affected = affected
    db.commit()

    log_activity(
        db, campaign.user_id, "campaign.started", "campaign",
        f"Campaign '{campaign.name}' started — {affected} products repriced",
        metadata={"campaign_id": campaign.id, "products_affected": affected},
    )
    logger.info("Campaign %d '%s' started (%d products)", campaign.id, campaign.name, affected)


def _end_campaign(db: Session, campaign: PriceCampaign, now: datetime) -> None:
    """Revert all campaign prices to their pre-campaign values."""
    from tasks.notification_tasks import _push_price_to_store
    from services.activity_service import log_activity

    snapshots = (
        db.query(CampaignProductSnapshot)
        .filter(CampaignProductSnapshot.campaign_id == campaign.id)
        .all()
    )

    product_ids = [s.product_id for s in snapshots]
    products = {
        p.id: p
        for p in db.query(ProductMonitored).filter(ProductMonitored.id.in_(product_ids)).all()
    }

    reverted = 0
    for snapshot in snapshots:
        product = products.get(snapshot.product_id)
        if not product:
            continue

        old_price = product.my_price
        product.my_price = snapshot.price_before
        db.add(MyPriceHistory(
            product_id=product.id,
            workspace_id=product.workspace_id,
            old_price=old_price,
            new_price=snapshot.price_before,
            note=f"Campaign ended: {campaign.name}",
        ))

        try:
            _push_price_to_store(product, snapshot.price_before, db)
        except Exception:
            logger.warning("Revert store push failed for product %d in campaign %d", product.id, campaign.id)

        reverted += 1

    campaign.status = "completed"
    db.commit()

    log_activity(
        db, campaign.user_id, "campaign.ended", "campaign",
        f"Campaign '{campaign.name}' ended — {reverted} prices reverted",
        metadata={"campaign_id": campaign.id, "reverted": reverted},
    )
    logger.info("Campaign %d '%s' ended (%d prices reverted)", campaign.id, campaign.name, reverted)


# ── Celery task ───────────────────────────────────────────────────────────────

@celery_app.task(base=DatabaseTask, bind=True, name="tasks.campaign_tasks.run_scheduled_campaigns")
def run_scheduled_campaigns(self):
    """Check every 60 s for campaigns to start or end."""
    now = datetime.utcnow()
    db = self.db

    try:
        due_to_start = (
            db.query(PriceCampaign)
            .filter(PriceCampaign.status == "scheduled", PriceCampaign.starts_at <= now)
            .all()
        )
        for campaign in due_to_start:
            try:
                _start_campaign(db, campaign, now)
            except Exception:
                logger.exception("Failed to start campaign %d", campaign.id)
                db.rollback()

        due_to_end = (
            db.query(PriceCampaign)
            .filter(PriceCampaign.status == "running", PriceCampaign.ends_at <= now)
            .all()
        )
        for campaign in due_to_end:
            try:
                _end_campaign(db, campaign, now)
            except Exception:
                logger.exception("Failed to end campaign %d", campaign.id)
                db.rollback()

    except Exception:
        logger.exception("run_scheduled_campaigns task failed")
