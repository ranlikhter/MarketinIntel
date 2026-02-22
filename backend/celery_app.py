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
        # Scrape all products every 6 hours
        'scrape-all-products-6h': {
            'task': 'tasks.scraping_tasks.scrape_all_products',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
            'options': {'queue': 'scraping'}
        },

        # Update price analytics daily
        'update-analytics-daily': {
            'task': 'tasks.analytics_tasks.update_all_analytics',
            'schedule': crontab(minute=0, hour=2),  # 2 AM daily
            'options': {'queue': 'analytics'}
        },

        # Clean old price history weekly
        'cleanup-old-data-weekly': {
            'task': 'tasks.analytics_tasks.cleanup_old_data',
            'schedule': crontab(minute=0, hour=3, day_of_week=0),  # Sunday 3 AM
            'options': {'queue': 'maintenance'}
        },

        # Send daily digest emails
        'send-daily-digest': {
            'task': 'tasks.notification_tasks.send_daily_digest',
            'schedule': crontab(minute=0, hour=8),  # 8 AM daily
            'options': {'queue': 'notifications'}
        },

        # Sync inventory from connected Shopify / WooCommerce stores every 4 hours
        'sync-store-inventory-4h': {
            'task': 'tasks.inventory_tasks.sync_all_store_inventory',
            'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
            'options': {'queue': 'integrations'}
        },
    }
)

# Task routing
celery_app.conf.task_routes = {
    'tasks.scraping_tasks.*': {'queue': 'scraping'},
    'tasks.analytics_tasks.*': {'queue': 'analytics'},
    'tasks.notification_tasks.*': {'queue': 'notifications'},
    'tasks.inventory_tasks.*': {'queue': 'integrations'},
}

if __name__ == '__main__':
    celery_app.start()
