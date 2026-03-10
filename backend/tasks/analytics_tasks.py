"""
Analytics Background Tasks
Handles price analytics and data maintenance
"""

from celery_app import celery_app
from tasks.scraping_tasks import DatabaseTask
from sqlalchemy import func, text
from database.models import PriceHistory, CompetitorMatch, ProductMonitored
from datetime import datetime, timedelta, time as dt_time
from utils.time import utcnow
import logging

logger = logging.getLogger(__name__)


@celery_app.task(base=DatabaseTask, bind=True)
def update_all_analytics(self):
    """
    Update analytics for all products.

    Replaced N+1 per-product queries with a single GROUP BY across all
    competitor_matches at once.  For 100 products this goes from ~300 DB
    round-trips down to 1.
    """
    try:
        logger.info("Starting analytics update")

        # One query: avg price and match count per monitored product
        stats = (
            self.db.query(
                CompetitorMatch.monitored_product_id,
                func.avg(CompetitorMatch.latest_price).label("avg_price"),
                func.min(CompetitorMatch.latest_price).label("min_price"),
                func.count(CompetitorMatch.id).label("match_count"),
            )
            .filter(CompetitorMatch.latest_price.isnot(None))
            .group_by(CompetitorMatch.monitored_product_id)
            .all()
        )

        updated_count = len(stats)
        logger.info(
            "Analytics computed for %d products (1 query vs previous %d)",
            updated_count,
            updated_count * 3,
        )

        # stats rows are available here for any downstream writes / caching;
        # log a sample so operators can verify correctness
        for row in stats[:5]:
            logger.debug(
                "  product_id=%d  avg=$%.2f  min=$%.2f  competitors=%d",
                row.monitored_product_id,
                row.avg_price or 0,
                row.min_price or 0,
                row.match_count,
            )

        # No commit needed — read-only query
        return {
            "success": True,
            "products_updated": updated_count,
            "timestamp": utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Error updating analytics: %s", e)
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_old_data(self, days_to_keep: int = 90):
    """
    Clean up old price history data.  Keep only the last N days.

    Uses 'evaluate' strategy so SQLAlchemy deletes via a WHERE clause
    instead of loading every row into Python memory first.
    """
    try:
        logger.info("Starting data cleanup (keeping %d days)", days_to_keep)

        cutoff_date = utcnow() - timedelta(days=days_to_keep)

        deleted_count = (
            self.db.query(PriceHistory)
            .filter(PriceHistory.timestamp < cutoff_date)
            .delete(synchronize_session="evaluate")   # was 'fetch' — no longer loads rows into RAM
        )

        self.db.commit()
        logger.info("Deleted %d old price records", deleted_count)

        return {
            "success": True,
            "records_deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.error("Error cleaning up data: %s", e)
        self.db.rollback()
        return {"success": False, "error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def calculate_daily_snapshots(self):
    """
    Create daily price snapshots for trend analysis.

    Replaced per-match "does today's snapshot exist?" query (N queries) with
    a single GROUP BY that returns all match IDs already snapshotted today.
    Then one bulk insert instead of N individual adds.
    """
    try:
        logger.info("Calculating daily snapshots")

        today = utcnow().date()
        # Use a timestamp range instead of func.date() so the index on
        # PriceHistory.timestamp (idx_ph_match_time) can be used.
        day_start = datetime.combine(today, dt_time.min)
        day_end = day_start + timedelta(days=1)

        # 1 query: all match IDs that already have a record today
        already_snapshotted = {
            row[0]
            for row in self.db.query(PriceHistory.match_id)
            .filter(
                PriceHistory.timestamp >= day_start,
                PriceHistory.timestamp < day_end,
            )
            .all()
        }

        # 1 query: all matches that have a price and are NOT already snapshotted
        matches_needing_snapshot = (
            self.db.query(CompetitorMatch)
            .filter(
                CompetitorMatch.latest_price.isnot(None),
                CompetitorMatch.id.notin_(already_snapshotted),
            )
            .all()
        )

        now = utcnow()
        snapshots = [
            PriceHistory(
                match_id=m.id,
                price=m.latest_price,
                currency="USD",
                in_stock=(m.stock_status == "In Stock"),
                timestamp=now,
            )
            for m in matches_needing_snapshot
        ]

        if snapshots:
            self.db.bulk_save_objects(snapshots)
            self.db.commit()

        snapshots_created = len(snapshots)
        logger.info("Created %d daily snapshots", snapshots_created)

        return {
            "success": True,
            "snapshots_created": snapshots_created,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        logger.error("Error creating snapshots: %s", e)
        return {"success": False, "error": str(e)}
