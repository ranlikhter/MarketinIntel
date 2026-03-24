"""
Integration Tests — Competitor Websites API (/api/competitors/*)

Tests CRUD operations, SSRF protection, and user isolation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def authed_client(client, db):
    user = User(email="comp_user@example.com", hashed_password="x", full_name="Comp User")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def second_user_client(client, db):
    user = User(email="comp_user2@example.com", hashed_password="x", full_name="Other User")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


VALID_COMPETITOR = {
    "name": "Rival Store",
    "base_url": "https://www.rival-store.com",
    "website_type": "custom",
    "price_selector": ".price",
    "title_selector": "h1.product-title",
}


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestCompetitorsAuth:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/competitors/")
        assert resp.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        assert resp.status_code in (401, 403)


# ── Tests: CRUD ───────────────────────────────────────────────────────────────

class TestCompetitorsCRUD:

    def test_create_competitor(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Rival Store"
        assert data["base_url"] == "https://www.rival-store.com"
        assert data["is_active"] is True

    def test_list_competitors_empty(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/competitors/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_includes_created_competitor(self, authed_client):
        client, _ = authed_client
        client.post("/api/competitors/", json=VALID_COMPETITOR)
        resp = client.get("/api/competitors/")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Rival Store" in names

    def test_get_competitor_by_id(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        comp_id = create_resp.json()["id"]
        resp = client.get(f"/api/competitors/{comp_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == comp_id

    def test_get_nonexistent_returns_404(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/competitors/999999")
        assert resp.status_code == 404

    def test_update_competitor(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        comp_id = create_resp.json()["id"]
        resp = client.put(f"/api/competitors/{comp_id}", json={"name": "Updated Rival"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Rival"

    def test_toggle_competitor_active(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        comp_id = create_resp.json()["id"]
        resp = client.put(f"/api/competitors/{comp_id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_delete_competitor(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        comp_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/competitors/{comp_id}")
        assert del_resp.status_code in (200, 204)
        get_resp = client.get(f"/api/competitors/{comp_id}")
        assert get_resp.status_code == 404


# ── Tests: SSRF Protection ────────────────────────────────────────────────────

class TestCompetitorsSSRF:

    PRIVATE_URLS = [
        "http://localhost/admin",
        "http://127.0.0.1:8000",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://169.254.169.254/meta-data",
        "file:///etc/passwd",
    ]

    def test_blocks_private_urls(self, authed_client):
        client, _ = authed_client
        for url in self.PRIVATE_URLS:
            payload = {**VALID_COMPETITOR, "base_url": url}
            resp = client.post("/api/competitors/", json=payload)
            assert resp.status_code in (400, 422), (
                f"Expected SSRF block for {url}, got {resp.status_code}"
            )


# ── Tests: User Isolation ─────────────────────────────────────────────────────

class TestCompetitorsIsolation:

    def test_user_cannot_see_other_users_competitors(self, client, db):
        # User 1 creates a competitor
        user1 = User(email="isol1@x.com", hashed_password="x")
        user2 = User(email="isol2@x.com", hashed_password="x")
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        app.dependency_overrides[get_current_user] = lambda: user1
        resp1 = client.post("/api/competitors/", json=VALID_COMPETITOR)
        assert resp1.status_code == 201

        # User 2 lists competitors — should see none from user 1
        app.dependency_overrides[get_current_user] = lambda: user2
        resp2 = client.get("/api/competitors/")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 0

        app.dependency_overrides.pop(get_current_user, None)

    def test_user_cannot_delete_other_users_competitor(self, client, db):
        user1 = User(email="del_isol1@x.com", hashed_password="x")
        user2 = User(email="del_isol2@x.com", hashed_password="x")
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        app.dependency_overrides[get_current_user] = lambda: user1
        create_resp = client.post("/api/competitors/", json=VALID_COMPETITOR)
        comp_id = create_resp.json()["id"]

        app.dependency_overrides[get_current_user] = lambda: user2
        del_resp = client.delete(f"/api/competitors/{comp_id}")
        assert del_resp.status_code in (403, 404)

        app.dependency_overrides.pop(get_current_user, None)
