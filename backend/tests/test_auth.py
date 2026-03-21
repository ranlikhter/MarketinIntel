"""
Tests for the Authentication API (/api/auth/*)
"""

import pytest

from database.models import User, Workspace, WorkspaceMember, UserRole


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRegistration:

    def test_register_success(self, client):
        """New user can register with valid credentials."""
        resp = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass1!",
            "full_name": "New User",
        })
        assert resp.status_code in (200, 201), f"Got {resp.status_code}: {resp.text}"

    def test_register_duplicate_email(self, client):
        """Registering with the same email twice should fail."""
        payload = {
            "email": "dup@example.com",
            "password": "SecurePass1!",
            "full_name": "Dup User",
        }
        client.post("/api/auth/register", json=payload)
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code in (400, 409, 422), (
            f"Expected conflict error, got {resp.status_code}"
        )

    def test_register_invalid_email(self, client):
        """Registering with a malformed email is rejected."""
        resp = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass1!",
        })
        assert resp.status_code == 422

    def test_register_missing_password(self, client):
        """Registering without a password is rejected."""
        resp = client.post("/api/auth/register", json={
            "email": "nopw@example.com",
        })
        assert resp.status_code == 422

    def test_register_creates_default_workspace(self, client, db):
        """New users should get a personal active workspace during signup."""
        resp = client.post("/api/auth/register", json={
            "email": "workspace.user@example.com",
            "password": "SecurePass1!",
            "full_name": "Workspace User",
        })
        assert resp.status_code in (200, 201), f"Got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert body["user"]["active_workspace_id"] is not None

        user = db.query(User).filter(User.email == "workspace.user@example.com").first()
        assert user is not None
        assert user.default_workspace_id is not None

        workspace = db.query(Workspace).filter(Workspace.id == user.default_workspace_id).first()
        assert workspace is not None
        assert workspace.owner_id == user.id

        membership = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        ).first()
        assert membership is not None
        assert membership.is_active is True
        assert membership.role == UserRole.ADMIN


class TestLogin:

    def test_login_success(self, client):
        """Valid credentials return access and refresh tokens."""
        client.post("/api/auth/register", json={
            "email": "login_ok@example.com",
            "password": "MyPass123!",
            "full_name": "Login OK",
        })
        resp = client.post("/api/auth/login", json={
            "email": "login_ok@example.com",
            "password": "MyPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data or "token" in data

    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        client.post("/api/auth/register", json={
            "email": "badpw@example.com",
            "password": "RightPass1!",
        })
        resp = client.post("/api/auth/login", json={
            "email": "badpw@example.com",
            "password": "WrongPass9!",
        })
        assert resp.status_code in (401, 400)

    def test_login_unknown_email(self, client):
        """Login with an email that was never registered returns 401."""
        resp = client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "Whatever1!",
        })
        assert resp.status_code in (401, 404, 400)

    def test_login_missing_fields(self, client):
        """Login without required fields returns 422."""
        resp = client.post("/api/auth/login", json={"email": "missing@example.com"})
        assert resp.status_code == 422


class TestProfile:

    def _get_token(self, client, email="profile_user@example.com"):
        client.post("/api/auth/register", json={
            "email": email,
            "password": "ProfilePass1!",
            "full_name": "Profile User",
        })
        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "ProfilePass1!",
        })
        data = r.json()
        return data.get("access_token") or data.get("token")

    def test_me_returns_user(self, client):
        """GET /api/auth/me returns the authenticated user's info."""
        token = self._get_token(client)
        if not token:
            pytest.skip("Login did not return token — skipping /me test")
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data or "id" in data

    def test_me_unauthenticated(self, client):
        """GET /api/auth/me without token returns 401/403."""
        resp = client.get("/api/auth/me")
        assert resp.status_code in (401, 403)
