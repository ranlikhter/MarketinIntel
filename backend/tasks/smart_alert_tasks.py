"""
Smart Alert Celery Tasks
Periodic tasks for checking and triggering smart alerts
"""

from celery_app import celery_app
from database.connection import SessionLocal
from services.smart_alert_service import get_smart_alert_service
from database.models import User
from datetime import datetime


@celery_app.task(name="check_smart_alerts")
def check_smart_alerts():
    """
    Check all enabled smart alerts and trigger notifications
    Runs every 5 minutes
    """
    db = SessionLocal()

    try:
        alert_service = get_smart_alert_service(db)

        # Check all alerts across all users
        triggered = alert_service.check_all_alerts()

        return {
            "status": "success",
            "checked_at": datetime.utcnow().isoformat(),
            "alerts_triggered": len(triggered),
            "alert_ids": [a.id for a in triggered]
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="check_user_smart_alerts")
def check_user_smart_alerts(user_id: int):
    """
    Check smart alerts for a specific user
    Can be triggered on-demand or after product updates
    """
    db = SessionLocal()

    try:
        alert_service = get_smart_alert_service(db)

        # Check only this user's alerts
        triggered = alert_service.check_all_alerts(user_id=user_id)

        return {
            "status": "success",
            "user_id": user_id,
            "checked_at": datetime.utcnow().isoformat(),
            "alerts_triggered": len(triggered)
        }

    except Exception as e:
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="send_daily_digests")
def send_daily_digests():
    """
    Send daily alert digests to all users who opted in
    Runs once per day at 8 AM
    """
    db = SessionLocal()

    try:
        # Get all users with daily digest enabled
        from database.models import PriceAlert

        users_with_daily = db.query(User).join(
            PriceAlert
        ).filter(
            PriceAlert.digest_frequency == "daily",
            PriceAlert.enabled == True
        ).distinct().all()

        alert_service = get_smart_alert_service(db)

        sent_count = 0
        for user in users_with_daily:
            try:
                alert_service.send_daily_digest(user.id)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send daily digest to user {user.id}: {e}")

        return {
            "status": "success",
            "digests_sent": sent_count,
            "total_users": len(users_with_daily)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="send_weekly_digests")
def send_weekly_digests():
    """
    Send weekly alert digests to all users who opted in
    Runs once per week on Monday at 8 AM
    """
    db = SessionLocal()

    try:
        # Get all users with weekly digest enabled
        from database.models import PriceAlert

        users_with_weekly = db.query(User).join(
            PriceAlert
        ).filter(
            PriceAlert.digest_frequency == "weekly",
            PriceAlert.enabled == True
        ).distinct().all()

        alert_service = get_smart_alert_service(db)

        sent_count = 0
        for user in users_with_weekly:
            try:
                alert_service.send_weekly_digest(user.id)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send weekly digest to user {user.id}: {e}")

        return {
            "status": "success",
            "digests_sent": sent_count,
            "total_users": len(users_with_weekly)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


# Celery Beat Schedule Configuration
# Add this to celery_app.py:
"""
from celery.schedules import crontab

app.conf.beat_schedule = {
    'check-smart-alerts-every-5-minutes': {
        'task': 'check_smart_alerts',
        'schedule': 300.0,  # Every 5 minutes
    },
    'send-daily-digests-8am': {
        'task': 'send_daily_digests',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    'send-weekly-digests-monday-8am': {
        'task': 'send_weekly_digests',
        'schedule': crontab(day_of_week=1, hour=8, minute=0),  # Monday at 8 AM
    },
}
"""
