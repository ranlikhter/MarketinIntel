"""
Scheduler API Endpoints
Manage background tasks and scraping schedules
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.connection import get_db
from database.models import ProductMonitored, User
from api.dependencies import get_current_user
from tasks.scraping_tasks import (
    scrape_single_product,
    scrape_all_products,
    scrape_products_by_priority
)
from tasks.analytics_tasks import (
    update_all_analytics,
    cleanup_old_data,
    calculate_daily_snapshots
)
from tasks.notification_tasks import (
    check_price_alerts,
    send_daily_digest
)
from celery.result import AsyncResult
from celery_app import celery_app

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# Pydantic models
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class ScheduleConfig(BaseModel):
    enabled: bool
    interval_hours: int = 6


class BulkScrapeRequest(BaseModel):
    product_ids: Optional[List[int]] = None  # If None, scrape all
    priority: bool = False


# ============================================
# Manual Task Triggers
# ============================================

@router.post("/scrape/product/{product_id}", response_model=TaskResponse)
async def trigger_product_scrape(
    product_id: int,
    website: str = 'amazon.com',
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger scrape for a single product

    - **product_id**: ID of product to scrape
    - **website**: Competitor website (default: amazon.com)
    """
    # Verify product exists and belongs to the requesting user
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Queue scraping task
    task = scrape_single_product.delay(product_id, website)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=f'Scraping task queued for product {product_id}'
    )


@router.post("/scrape/all", response_model=TaskResponse)
async def trigger_bulk_scrape(request: BulkScrapeRequest = BulkScrapeRequest()):
    """
    Trigger bulk scrape for multiple products

    - **product_ids**: List of product IDs (if empty, scrape all)
    - **priority**: Use priority-based scraping
    """
    if request.priority:
        task = scrape_products_by_priority.delay()
        message = 'Priority scraping task queued'
    elif request.product_ids:
        # Queue individual tasks for specified products
        tasks = []
        for pid in request.product_ids:
            t = scrape_single_product.delay(pid)
            tasks.append(t.id)

        return TaskResponse(
            task_id=tasks[0] if tasks else '',
            status='queued',
            message=f'{len(tasks)} scraping tasks queued'
        )
    else:
        task = scrape_all_products.delay()
        message = 'Bulk scraping task queued for all products'

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=message
    )


@router.post("/analytics/update", response_model=TaskResponse)
async def trigger_analytics_update():
    """
    Manually trigger analytics update for all products
    """
    task = update_all_analytics.delay()

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message='Analytics update task queued'
    )


@router.post("/analytics/snapshots", response_model=TaskResponse)
async def trigger_daily_snapshots():
    """
    Create daily price snapshots for trend analysis
    """
    task = calculate_daily_snapshots.delay()

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message='Daily snapshot task queued'
    )


@router.post("/alerts/check", response_model=TaskResponse)
async def trigger_alert_check(threshold_pct: float = 5.0):
    """
    Check for price alerts

    - **threshold_pct**: Percentage change threshold (default: 5%)
    """
    task = check_price_alerts.delay(threshold_pct)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=f'Alert check queued (threshold: {threshold_pct}%)'
    )


@router.post("/notifications/digest", response_model=TaskResponse)
async def trigger_daily_digest():
    """
    Send daily digest email
    """
    task = send_daily_digest.delay()

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message='Daily digest task queued'
    )


# ============================================
# Task Status & Monitoring
# ============================================

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a background task

    - **task_id**: Celery task ID
    """
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        'task_id': task_id,
        'status': task_result.state,
        'result': None,
        'error': None
    }

    if task_result.state == 'SUCCESS':
        response['result'] = task_result.result
    elif task_result.state == 'FAILURE':
        response['error'] = str(task_result.info)

    return TaskStatusResponse(**response)


@router.get("/tasks/active")
async def get_active_tasks():
    """
    Get all currently running tasks
    """
    # Get active tasks from Celery
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()

    if not active_tasks:
        return {
            'active_tasks': [],
            'count': 0
        }

    # Flatten tasks from all workers
    all_tasks = []
    for worker, tasks in active_tasks.items():
        for task in tasks:
            all_tasks.append({
                'task_id': task['id'],
                'name': task['name'],
                'worker': worker,
                'time_start': task.get('time_start'),
            })

    return {
        'active_tasks': all_tasks,
        'count': len(all_tasks)
    }


@router.get("/tasks/scheduled")
async def get_scheduled_tasks():
    """
    Get all scheduled periodic tasks
    """
    inspect = celery_app.control.inspect()
    scheduled = inspect.scheduled()

    if not scheduled:
        return {
            'scheduled_tasks': [],
            'count': 0
        }

    # Flatten tasks
    all_tasks = []
    for worker, tasks in scheduled.items():
        for task in tasks:
            all_tasks.append({
                'task_id': task['request']['id'],
                'name': task['request']['name'],
                'eta': task['eta'],
                'worker': worker
            })

    return {
        'scheduled_tasks': all_tasks,
        'count': len(all_tasks)
    }


@router.get("/queue/stats")
async def get_queue_stats():
    """
    Get queue statistics
    """
    inspect = celery_app.control.inspect()

    stats = {
        'active_tasks': 0,
        'scheduled_tasks': 0,
        'workers': []
    }

    # Count active tasks
    active = inspect.active()
    if active:
        stats['active_tasks'] = sum(len(tasks) for tasks in active.values())
        stats['workers'] = list(active.keys())

    # Count scheduled tasks
    scheduled = inspect.scheduled()
    if scheduled:
        stats['scheduled_tasks'] = sum(len(tasks) for tasks in scheduled.values())

    return stats


# ============================================
# Schedule Management
# ============================================

@router.post("/maintenance/cleanup")
async def trigger_cleanup(days_to_keep: int = 90):
    """
    Clean up old price history data

    - **days_to_keep**: Number of days to retain (default: 90)
    """
    task = cleanup_old_data.delay(days_to_keep)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=f'Cleanup task queued (keeping {days_to_keep} days)'
    )


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Cancel a running task

    - **task_id**: Celery task ID to cancel
    """
    celery_app.control.revoke(task_id, terminate=True)

    return {
        'success': True,
        'task_id': task_id,
        'message': 'Task cancellation requested'
    }
