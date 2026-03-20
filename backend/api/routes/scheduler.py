"""
Scheduler API Endpoints
Manage background tasks and scraping schedules
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import time

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, User
from api.dependencies import get_current_user
from tasks.scraping_tasks import (
    scrape_single_product,
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

# In-memory task ownership map so users can only inspect/cancel tasks they queued.
# For multi-worker setups this should be moved to Redis.
_TASK_OWNERS: OrderedDict[str, tuple[int, float]] = OrderedDict()  # task_id -> (user_id, ts)
_TASK_OWNERS_LOCK = threading.Lock()
_TASK_OWNERS_TTL = 7 * 24 * 3600
_TASK_OWNERS_MAX = 20000


def _prune_task_owners(now_ts: float) -> None:
    while _TASK_OWNERS:
        _, (_, ts) = next(iter(_TASK_OWNERS.items()))
        if now_ts - ts > _TASK_OWNERS_TTL:
            _TASK_OWNERS.popitem(last=False)
        else:
            break
    while len(_TASK_OWNERS) > _TASK_OWNERS_MAX:
        _TASK_OWNERS.popitem(last=False)


def _record_task_owner(task_id: str, user_id: int) -> None:
    now_ts = time.time()
    with _TASK_OWNERS_LOCK:
        _prune_task_owners(now_ts)
        _TASK_OWNERS[task_id] = (user_id, now_ts)


def _is_task_owner(task_id: str, user_id: int) -> bool:
    now_ts = time.time()
    with _TASK_OWNERS_LOCK:
        _prune_task_owners(now_ts)
        owner = _TASK_OWNERS.get(task_id)
        return bool(owner and owner[0] == user_id)


def _owned_task_ids(user_id: int) -> set[str]:
    now_ts = time.time()
    with _TASK_OWNERS_LOCK:
        _prune_task_owners(now_ts)
        return {task_id for task_id, (owner_id, _) in _TASK_OWNERS.items() if owner_id == user_id}


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
    _record_task_owner(task.id, current_user.id)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=f'Scraping task queued for product {product_id}'
    )


@router.post("/scrape/all", response_model=TaskResponse)
async def trigger_bulk_scrape(
    request: BulkScrapeRequest = BulkScrapeRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger bulk scrape for multiple products

    - **product_ids**: List of product IDs (if empty, scrape all)
    - **priority**: Use priority-based scraping
    """
    task_ids: list[str] = []

    if request.priority:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        product_ids = [
            row[0]
            for row in (
                db.query(ProductMonitored.id)
                .join(CompetitorMatch, CompetitorMatch.monitored_product_id == ProductMonitored.id)
                .filter(
                    ProductMonitored.user_id == current_user.id,
                    CompetitorMatch.last_scraped_at < cutoff,
                )
                .distinct()
                .limit(50)
                .all()
            )
        ]
    elif request.product_ids:
        owned_ids = {
            row[0]
            for row in (
                db.query(ProductMonitored.id)
                .filter(
                    ProductMonitored.user_id == current_user.id,
                    ProductMonitored.id.in_(request.product_ids),
                )
                .all()
            )
        }
        unauthorized_ids = sorted(set(request.product_ids) - owned_ids)
        if unauthorized_ids:
            raise HTTPException(
                status_code=403,
                detail=f"You can only scrape your own products. Unauthorized IDs: {unauthorized_ids}",
            )
        product_ids = sorted(owned_ids)
    else:
        product_ids = [
            row[0]
            for row in (
                db.query(ProductMonitored.id)
                .filter(ProductMonitored.user_id == current_user.id)
                .all()
            )
        ]

    for pid in product_ids:
        task = scrape_single_product.delay(pid)
        task_ids.append(task.id)
        _record_task_owner(task.id, current_user.id)

    if not task_ids:
        return TaskResponse(
            task_id='',
            status='queued',
            message='No eligible products found to queue',
        )

    return TaskResponse(
        task_id=task_ids[0],
        status='queued',
        message=f'{len(task_ids)} scraping task(s) queued',
    )


@router.post("/analytics/update", response_model=TaskResponse)
async def trigger_analytics_update(current_user: User = Depends(get_current_user)):
    """
    Manually trigger analytics update for all products
    """
    task = update_all_analytics.delay()
    _record_task_owner(task.id, current_user.id)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message='Analytics update task queued'
    )


@router.post("/analytics/snapshots", response_model=TaskResponse)
async def trigger_daily_snapshots(current_user: User = Depends(get_current_user)):
    """
    Create daily price snapshots for trend analysis
    """
    task = calculate_daily_snapshots.delay()
    _record_task_owner(task.id, current_user.id)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message='Daily snapshot task queued'
    )


@router.post("/alerts/check", response_model=TaskResponse)
async def trigger_alert_check(
    threshold_pct: float = 5.0,
    current_user: User = Depends(get_current_user),
):
    """
    Check for price alerts

    - **threshold_pct**: Percentage change threshold (default: 5%)
    """
    task = check_price_alerts.delay(threshold_pct)
    _record_task_owner(task.id, current_user.id)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=f'Alert check queued (threshold: {threshold_pct}%)'
    )


@router.post("/notifications/digest", response_model=TaskResponse)
async def trigger_daily_digest(current_user: User = Depends(get_current_user)):
    """
    Send daily digest email
    """
    task = send_daily_digest.delay()
    _record_task_owner(task.id, current_user.id)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message='Daily digest task queued'
    )


# ============================================
# Task Status & Monitoring
# ============================================

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get status of a background task

    - **task_id**: Celery task ID
    """
    if not _is_task_owner(task_id, current_user.id):
        raise HTTPException(status_code=404, detail="Task not found")

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
async def get_active_tasks(current_user: User = Depends(get_current_user)):
    """
    Get all currently running tasks
    """
    # Get active tasks from Celery
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()
    owned_ids = _owned_task_ids(current_user.id)

    if not active_tasks:
        return {
            'active_tasks': [],
            'count': 0
        }

    # Flatten tasks from all workers
    all_tasks = []
    for worker, tasks in active_tasks.items():
        for task in tasks:
            if task['id'] not in owned_ids:
                continue
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
async def get_scheduled_tasks(current_user: User = Depends(get_current_user)):
    """
    Get all scheduled periodic tasks
    """
    inspect = celery_app.control.inspect()
    scheduled = inspect.scheduled()
    owned_ids = _owned_task_ids(current_user.id)

    if not scheduled:
        return {
            'scheduled_tasks': [],
            'count': 0
        }

    # Flatten tasks
    all_tasks = []
    for worker, tasks in scheduled.items():
        for task in tasks:
            task_id = task['request']['id']
            if task_id not in owned_ids:
                continue
            all_tasks.append({
                'task_id': task_id,
                'name': task['request']['name'],
                'eta': task['eta'],
                'worker': worker
            })

    return {
        'scheduled_tasks': all_tasks,
        'count': len(all_tasks)
    }


@router.get("/queue/stats")
async def get_queue_stats(current_user: User = Depends(get_current_user)):
    """
    Get queue statistics
    """
    inspect = celery_app.control.inspect()
    owned_ids = _owned_task_ids(current_user.id)

    stats = {
        'active_tasks': 0,
        'scheduled_tasks': 0,
        'workers': []
    }

    # Count active tasks
    active = inspect.active()
    if active:
        stats['active_tasks'] = sum(
            1 for tasks in active.values() for task in tasks if task['id'] in owned_ids
        )
        stats['workers'] = sorted({
            worker for worker, tasks in active.items()
            if any(task['id'] in owned_ids for task in tasks)
        })

    # Count scheduled tasks
    scheduled = inspect.scheduled()
    if scheduled:
        stats['scheduled_tasks'] = sum(
            1
            for tasks in scheduled.values()
            for task in tasks
            if task['request']['id'] in owned_ids
        )

    return stats


# ============================================
# Schedule Management
# ============================================

@router.post("/maintenance/cleanup")
async def trigger_cleanup(
    days_to_keep: int = 90,
    current_user: User = Depends(get_current_user),
):
    """
    Clean up old price history data

    - **days_to_keep**: Number of days to retain (default: 90)
    """
    task = cleanup_old_data.delay(days_to_keep)
    _record_task_owner(task.id, current_user.id)

    return TaskResponse(
        task_id=task.id,
        status='queued',
        message=f'Cleanup task queued (keeping {days_to_keep} days)'
    )


@router.post("/task/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a running task

    - **task_id**: Celery task ID to cancel
    """
    if not _is_task_owner(task_id, current_user.id):
        raise HTTPException(status_code=404, detail="Task not found")

    celery_app.control.revoke(task_id, terminate=True)

    return {
        'success': True,
        'task_id': task_id,
        'message': 'Task cancellation requested'
    }
