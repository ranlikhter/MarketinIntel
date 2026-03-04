"""
Celery Application Configuration
Handles background tasks and scheduled scraping
"""

from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Create Celery app
celery_app = Celery(
    'marketintel',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'tasks.scraping_tasks',
        'tasks.analytics_tasks',
        'tasks.notification_tasks',
        'tasks.inventory_tasks',
        'tasks.smart_alert_tasks',
        'tasks.discovery_tasks',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,

    # Beat schedule for periodic tasks
    beat_schedule={
        # ── Smart alerts (most time-sensitive) ──────────────────────────────
        # Check all alert conditions every 5 minutes
        'check-smart-alerts-5min': {
            'task': 'check_smart_alerts',
            'schedule': 300.0,  # Every 5 minutes
            'options': {'queue': 'alerts'}
        },

        # ── Price alert notifications ────────────────────────────────────────
        # Check raw price-change thresholds every hour
        'check-price-alerts-1h': {
            'task': 'tasks.notification_tasks.check_price_alerts',
            'schedule': crontab(minute=0),  # Every hour on the hour
            'options': {'queue': 'notifications'}
        },

        # ── Scraping ─────────────────────────────────────────────────────────
        # Full scrape of all products every 6 hours
        'scrape-all-products-6h': {
            'task': 'tasks.scraping_tasks.scrape_all_products',
            'schedule': crontab(minute=0, hour='*/6'),
            'options': {'queue': 'scraping'}
        },

        # Priority scrape (stale products) every hour
        'scrape-priority-products-1h': {
            'task': 'tasks.scraping_tasks.scrape_products_by_priority',
            'schedule': crontab(minute=30),  # Every hour at :30
            'options': {'queue': 'scraping'}
        },

        # Retry failed scrapes once per day
        'retry-failed-scrapes-daily': {
            'task': 'tasks.scraping_tasks.retry_failed_scrapes',
            'schedule': crontab(minute=0, hour=5),  # 5 AM daily
            'options': {'queue': 'scraping'}
        },

        # ── Analytics ────────────────────────────────────────────────────────
        # Aggregate daily price snapshots at midnight
        'calculate-daily-snapshots': {
            'task': 'tasks.analytics_tasks.calculate_daily_snapshots',
            'schedule': crontab(minute=0, hour=0),  # Midnight daily
            'options': {'queue': 'analytics'}
        },

        # Recalculate trends/averages at 2 AM daily
        'update-analytics-daily': {
            'task': 'tasks.analytics_tasks.update_all_analytics',
            'schedule': crontab(minute=0, hour=2),
            'options': {'queue': 'analytics'}
        },

        # Purge price history older than 90 days every Sunday at 3 AM
        'cleanup-old-data-weekly': {
            'task': 'tasks.analytics_tasks.cleanup_old_data',
            'schedule': crontab(minute=0, hour=3, day_of_week=0),
            'options': {'queue': 'maintenance'}
        },

        # ── Digest emails / Slack ─────────────────────────────────────────────
        # Daily digest at 8 AM (smart_alert_tasks — per-user, respects digest prefs)
        'send-daily-digests-8am': {
            'task': 'send_daily_digests',
            'schedule': crontab(minute=0, hour=8),
            'options': {'queue': 'notifications'}
        },

        # Weekly digest every Monday at 8 AM
        'send-weekly-digests-monday': {
            'task': 'send_weekly_digests',
            'schedule': crontab(minute=0, hour=8, day_of_week=1),
            'options': {'queue': 'notifications'}
        },

        # ── Store integrations ────────────────────────────────────────────────
        # Sync inventory from Shopify / WooCommerce every 4 hours
        'sync-store-inventory-4h': {
            'task': 'tasks.inventory_tasks.sync_all_store_inventory',
            'schedule': crontab(minute=0, hour='*/4'),
            'options': {'queue': 'integrations'}
        },
    }
)

# Task routing
celery_app.conf.task_routes = {
    'tasks.scraping_tasks.*':      {'queue': 'scraping'},
    'tasks.analytics_tasks.*':     {'queue': 'analytics'},
    'tasks.notification_tasks.*':  {'queue': 'notifications'},
    'tasks.inventory_tasks.*':     {'queue': 'integrations'},
    'tasks.smart_alert_tasks.*':   {'queue': 'alerts'},
    'tasks.discovery_tasks.*':     {'queue': 'scraping'},
    'check_smart_alerts':          {'queue': 'alerts'},
    'check_user_smart_alerts':     {'queue': 'alerts'},
    'send_daily_digests':          {'queue': 'notifications'},
    'send_weekly_digests':         {'queue': 'notifications'},
}

if __name__ == '__main__':
    celery_app.start()
