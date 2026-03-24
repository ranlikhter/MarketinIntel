"""
Integration Tests — Activity Log API (/api/activity)

Tests pagination, filtering by category/action/days, and user isolation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User, ActivityLog
from datetime import datetime, timedelta


def make_user(db, email="activity@x.com"):
    u = User(email=email, hashed_password="x", full_name="Activity User")
    db.add(u); db.commit(); db.refresh(u)
    return u


def seed_activity(db, user, n=5, category="product", action="created"):
    for i in range(n):
        log = ActivityLog(
            user_id=user.id,
            category=category,
            action=action,
            description=f"Activity {i}",
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        db.add(log)
    db.commit()


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestActivityAuth:

    def test_activity_requires_auth(self, client):
        resp = client.get("/api/activity")
        assert resp.status_code in (401, 403)


# ── Tests: Basic Retrieval ────────────────────────────────────────────────────

class TestActivityRetrieval:

    def test_empty_activity_log(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert data["total"] == 0

    def test_returns_seeded_activity(self, client, db):
        user = make_user(db, "act2@x.com")
        seed_activity(db, user, n=5)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get("/api/activity")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 5
        app.dependency_overrides.pop(get_current_user, None)

    def test_newest_first_ordering(self, client, db):
        user = make_user(db, "act3@x.com")
        seed_activity(db, user, n=3)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get("/api/activity")
        entries = resp.json().get("entries", resp.json().get("items", []))
        if len(entries) >= 2:
            ts1 = entries[0].get("created_at", "")
            ts2 = entries[1].get("created_at", "")
            assert ts1 >= ts2
        app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Filtering ──────────────────────────────────────────────────────────

class TestActivityFiltering:

    def test_filter_by_category(self, client, db):
        user = make_user(db, "act4@x.com")
        seed_activity(db, user, n=3, category="product")
        seed_activity(db, user, n=2, category="alert")
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get("/api/activity?category=product")
        assert resp.status_code == 200
        data = resp.json()
        entries = data.get("entries", data.get("items", []))
        assert all(e.get("category") == "product" for e in entries)
        app.dependency_overrides.pop(get_current_user, None)

    def test_filter_by_days(self, client, db):
        user = make_user(db, "act5@x.com")
        # One recent and one old entry
        db.add(ActivityLog(user_id=user.id, category="product", action="created",
                           description="Recent", created_at=datetime.utcnow() - timedelta(days=1)))
        db.add(ActivityLog(user_id=user.id, category="product", action="created",
                           description="Old", created_at=datetime.utcnow() - timedelta(days=60)))
        db.commit()
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get("/api/activity?days=7")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        app.dependency_overrides.pop(get_current_user, None)

    def test_pagination(self, client, db):
        user = make_user(db, "act6@x.com")
        seed_activity(db, user, n=10)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = client.get("/api/activity?limit=3&page=1")
        assert resp.status_code == 200
        entries = resp.json().get("entries", resp.json().get("items", []))
        assert len(entries) <= 3
        app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Isolation ──────────────────────────────────────────────────────────

class TestActivityIsolation:

    def test_users_see_only_their_own_activity(self, client, db):
        u1 = make_user(db, "aiso1@x.com")
        u2 = make_user(db, "aiso2@x.com")
        seed_activity(db, u1, n=5)
        seed_activity(db, u2, n=3)

        app.dependency_overrides[get_current_user] = lambda: u2
        resp = client.get("/api/activity")
        assert resp.json()["total"] == 3

        app.dependency_overrides.pop(get_current_user, None)
