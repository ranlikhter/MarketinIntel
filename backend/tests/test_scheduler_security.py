"""
Security-focused tests for scheduler/job-control endpoints.
"""

from types import SimpleNamespace

from tests.conftest import register_and_login, auth_headers
from api.routes import scheduler as scheduler_routes
from database.models import ProductMonitored, User


class _DummyDelayTask:
    """Simple task stub with Celery-like .delay() returning an object with .id."""

    @staticmethod
    def delay(*args, **kwargs):
        task_id = kwargs.get("task_id", "task-stub-1")
        if args:
            task_id = f"task-{args[0]}"
        return SimpleNamespace(id=task_id)


class TestSchedulerAuth:
    def test_scheduler_requires_auth_for_job_control(self, client):
        resp = client.post("/api/scheduler/analytics/update")
        assert resp.status_code in (401, 403)

        resp = client.get("/api/scheduler/queue/stats")
        assert resp.status_code in (401, 403)

    def test_authenticated_user_can_queue_analytics_task(self, client, monkeypatch):
        token = register_and_login(client, email="sched_owner@example.com")
        monkeypatch.setattr(scheduler_routes, "update_all_analytics", _DummyDelayTask)

        resp = client.post(
            "/api/scheduler/analytics/update",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "queued"
        assert body["task_id"] == "task-stub-1"

    def test_task_status_is_scoped_to_task_owner(self, client, monkeypatch):
        owner_token = register_and_login(client, email="owner@example.com")
        other_token = register_and_login(client, email="other@example.com")
        monkeypatch.setattr(scheduler_routes, "update_all_analytics", _DummyDelayTask)

        created = client.post(
            "/api/scheduler/analytics/update",
            headers=auth_headers(owner_token),
        )
        assert created.status_code == 200, created.text
        task_id = created.json()["task_id"]

        other_user_view = client.get(
            f"/api/scheduler/task/{task_id}",
            headers=auth_headers(other_token),
        )
        assert other_user_view.status_code == 404

        owner_view = client.get(
            f"/api/scheduler/task/{task_id}",
            headers=auth_headers(owner_token),
        )
        assert owner_view.status_code == 200, owner_view.text
        assert owner_view.json()["task_id"] == task_id

    def test_bulk_scrape_rejects_foreign_product_ids(self, client, db, monkeypatch):
        token_1 = register_and_login(client, email="bulk1@example.com")
        token_2 = register_and_login(client, email="bulk2@example.com")

        user_1 = db.query(User).filter(User.email == "bulk1@example.com").first()
        user_2 = db.query(User).filter(User.email == "bulk2@example.com").first()
        assert user_1 and user_2

        p1 = ProductMonitored(title="Owned Product", user_id=user_1.id)
        p2 = ProductMonitored(title="Foreign Product", user_id=user_2.id)
        db.add_all([p1, p2])
        db.commit()
        db.refresh(p1)
        db.refresh(p2)

        monkeypatch.setattr(scheduler_routes, "scrape_single_product", _DummyDelayTask)

        resp = client.post(
            "/api/scheduler/scrape/all",
            json={"product_ids": [p1.id, p2.id]},
            headers=auth_headers(token_1),
        )
        assert resp.status_code == 403
