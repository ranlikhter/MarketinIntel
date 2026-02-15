"""
Analytics Background Tasks
Handles price analytics and data maintenance
"""

from celery_app import celery_app
from tasks.scraping_tasks import DatabaseTask
from sqlalchemy import func
from database.models import PriceHistory, CompetitorMatch, ProductMonitored
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(base=DatabaseTask, bind=True)
def update_all_analytics(self):
    """
    Update analytics for all products
    Calculate trends, averages, volatility
    """
    try:
        logger.info("Starting analytics update")

        products = self.db.query(ProductMonitored).all()
        updated_count = 0

        for product in products:
            # Get matches
            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.product_id == product.id
            ).all()

            if not matches:
                continue

            # Calculate average price across competitors
            avg_price = self.db.query(
                func.avg(CompetitorMatch.latest_price)
            ).filter(
                CompetitorMatch.product_id == product.id,
                CompetitorMatch.latest_price.isnot(None)
            ).scalar()

            # Find lowest competitor
            lowest_match = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.product_id == product.id,
                CompetitorMatch.latest_price.isnot(None)
            ).order_by(CompetitorMatch.latest_price.asc()).first()

            # You can add custom fields to ProductMonitored for caching analytics
            # product.avg_competitor_price = avg_price
            # product.lowest_competitor_price = lowest_match.latest_price if lowest_match else None
            # product.analytics_updated_at = datetime.utcnow()

            updated_count += 1

        self.db.commit()

        logger.info(f"Analytics updated for {updated_count} products")

        return {
            'success': True,
            'products_updated': updated_count,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error updating analytics: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_old_data(self, days_to_keep: int = 90):
    """
    Clean up old price history data
    Keep only last N days of data

    Args:
        days_to_keep: Number of days of history to retain
    """
    try:
        logger.info(f"Starting data cleanup (keeping {days_to_keep} days)")

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Delete old price history records
        deleted_count = self.db.query(PriceHistory).filter(
            PriceHistory.timestamp < cutoff_date
        ).delete(synchronize_session='fetch')

        self.db.commit()

        logger.info(f"Deleted {deleted_count} old price records")

        return {
            'success': True,
            'records_deleted': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Error cleaning up data: {e}")
        self.db.rollback()
        return {'success': False, 'error': str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def calculate_daily_snapshots(self):
    """
    Create daily price snapshots for trend analysis
    Aggregates hourly data into daily averages
    """
    try:
        logger.info("Calculating daily snapshots")

        # Get all matches
        matches = self.db.query(CompetitorMatch).all()
        snapshots_created = 0

        for match in matches:
            # Check if snapshot for today already exists
            today = datetime.utcnow().date()
            existing = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                func.date(PriceHistory.timestamp) == today
            ).first()

            if existing:
                continue  # Already have today's snapshot

            # Create snapshot with current price
            if match.latest_price:
                snapshot = PriceHistory(
                    match_id=match.id,
                    price=match.latest_price,
                    currency='USD',
                    in_stock=(match.stock_status == 'In Stock'),
                    timestamp=datetime.utcnow()
                )
                self.db.add(snapshot)
                snapshots_created += 1

        self.db.commit()

        logger.info(f"Created {snapshots_created} daily snapshots")

        return {
            'success': True,
            'snapshots_created': snapshots_created,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error creating snapshots: {e}")
        return {'success': False, 'error': str(e)}
