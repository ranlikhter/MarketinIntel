"""
Integration Tests — API Keys (/api/auth/api-keys/*)

Tests key generation, listing, revocation, rotation, and security.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def authed_client(client, db):
    user = User(email="apikey_user@example.com", hashed_password="x", full_name="Key User")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestApiKeyAuth:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/auth/api-keys")
        assert resp.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        resp = client.post("/api/auth/api-keys", json={"name": "My Key"})
        assert resp.status_code in (401, 403)


# ── Tests: Key Lifecycle ──────────────────────────────────────────────────────

class TestApiKeyLifecycle:

    def test_create_api_key(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/auth/api-keys", json={"name": "Zapier Integration"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "Zapier Integration"
        # Full key returned only at creation
        assert "full_key" in data
        assert data["full_key"].startswith("mi_")

    def test_full_key_not_returned_on_list(self, authed_client):
        client, _ = authed_client
        client.post("/api/auth/api-keys", json={"name": "List Test"})
        resp = client.get("/api/auth/api-keys")
        assert resp.status_code == 200
        for key in resp.json():
            assert "full_key" not in key

    def test_key_appears_in_list(self, authed_client):
        client, _ = authed_client
        client.post("/api/auth/api-keys", json={"name": "Listed Key"})
        resp = client.get("/api/auth/api-keys")
        names = [k["name"] for k in resp.json()]
        assert "Listed Key" in names

    def test_key_prefix_is_set(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/auth/api-keys", json={"name": "Prefix Test"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "key_prefix" in data
        assert len(data["key_prefix"]) > 0

    def test_revoke_api_key(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/auth/api-keys", json={"name": "To Revoke"})
        key_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/auth/api-keys/{key_id}")
        assert del_resp.status_code in (200, 204)

    def test_revoked_key_not_in_active_list(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/auth/api-keys", json={"name": "Revoked Key"})
        key_id = create_resp.json()["id"]
        client.delete(f"/api/auth/api-keys/{key_id}")
        resp = client.get("/api/auth/api-keys")
        active_names = [k["name"] for k in resp.json() if k.get("is_active")]
        assert "Revoked Key" not in active_names

    def test_rotate_api_key(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/auth/api-keys", json={"name": "Rotate Me"})
        key_id = create_resp.json()["id"]
        old_key = create_resp.json()["full_key"]

        rotate_resp = client.post(f"/api/auth/api-keys/{key_id}/rotate")
        assert rotate_resp.status_code in (200, 201)
        new_key = rotate_resp.json().get("full_key")
        if new_key:
            assert new_key != old_key
            assert new_key.startswith("mi_")

    def test_revoke_nonexistent_key_returns_404(self, authed_client):
        client, _ = authed_client
        resp = client.delete("/api/auth/api-keys/999999")
        assert resp.status_code == 404

    def test_create_multiple_keys(self, authed_client):
        client, _ = authed_client
        for i in range(3):
            resp = client.post("/api/auth/api-keys", json={"name": f"Key {i}"})
            assert resp.status_code in (200, 201)
        list_resp = client.get("/api/auth/api-keys")
        assert len(list_resp.json()) >= 3

    def test_name_required_for_creation(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/auth/api-keys", json={})
        assert resp.status_code == 422


# ── Tests: Key Isolation ──────────────────────────────────────────────────────

class TestApiKeyIsolation:

    def test_users_cannot_see_each_others_keys(self, client, db):
        user1 = User(email="key_isol1@x.com", hashed_password="x")
        user2 = User(email="key_isol2@x.com", hashed_password="x")
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        app.dependency_overrides[get_current_user] = lambda: user1
        client.post("/api/auth/api-keys", json={"name": "User1 Key"})

        app.dependency_overrides[get_current_user] = lambda: user2
        resp = client.get("/api/auth/api-keys")
        assert resp.status_code == 200
        names = [k["name"] for k in resp.json()]
        assert "User1 Key" not in names

        app.dependency_overrides.pop(get_current_user, None)

    def test_user_cannot_revoke_other_users_key(self, client, db):
        user1 = User(email="revoke_isol1@x.com", hashed_password="x")
        user2 = User(email="revoke_isol2@x.com", hashed_password="x")
        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        app.dependency_overrides[get_current_user] = lambda: user1
        create_resp = client.post("/api/auth/api-keys", json={"name": "Protected Key"})
        key_id = create_resp.json()["id"]

        app.dependency_overrides[get_current_user] = lambda: user2
        del_resp = client.delete(f"/api/auth/api-keys/{key_id}")
        assert del_resp.status_code in (403, 404)

        app.dependency_overrides.pop(get_current_user, None)
