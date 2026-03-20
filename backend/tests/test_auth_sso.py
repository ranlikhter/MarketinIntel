"""
Tests for Google SSO authentication.
"""

from api.auth_cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from api.routes import auth as auth_routes
from database.models import User
from services.auth_service import create_sso_state_token


async def _fake_google_claims(_token: str):
    return {
        "email": "google.user@example.com",
        "sub": "google-sub-123",
        "full_name": "Google User",
        "avatar_url": "https://example.com/avatar.png",
        "email_verified": True,
    }


async def _linked_google_claims(_token: str):
    return {
        "email": "linked.user@example.com",
        "sub": "google-sub-linked",
        "full_name": "Linked User",
        "avatar_url": "https://example.com/linked.png",
        "email_verified": True,
    }


async def _fake_microsoft_claims(*_args, **_kwargs):
    return {
        "email": "microsoft.user@example.com",
        "sub": "microsoft-sub-123",
        "full_name": "Microsoft User",
        "avatar_url": None,
        "email_verified": True,
    }


def _patch_password_helpers(monkeypatch):
    monkeypatch.setattr(auth_routes, "hash_password", lambda password: f"hashed::{password}")
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda plain_password, hashed_password: hashed_password == f"hashed::{plain_password}",
    )


class TestGoogleSSO:
    def test_google_sso_creates_verified_user(self, client, db, monkeypatch):
        _patch_password_helpers(monkeypatch)
        monkeypatch.setattr(auth_routes, "validate_google_id_token", _fake_google_claims)

        resp = client.post("/api/auth/sso/google", json={"credential": "valid-google-token"})
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["user"]["auth_provider"] == "google"
        assert body["user"]["password_login_enabled"] is False
        assert body["user"]["avatar_url"] == "https://example.com/avatar.png"

        user = db.query(User).filter(User.email == "google.user@example.com").first()
        assert user is not None
        assert user.auth_provider == "google"
        assert user.auth_provider_subject == "google-sub-123"
        assert user.is_verified is True
        assert user.password_login_enabled is False

    def test_google_sso_links_existing_local_account(self, client, db, monkeypatch):
        _patch_password_helpers(monkeypatch)
        client.post("/api/auth/register", json={
            "email": "linked.user@example.com",
            "password": "LinkedPass123!",
            "full_name": "Linked Local User",
        })
        monkeypatch.setattr(auth_routes, "validate_google_id_token", _linked_google_claims)

        resp = client.post("/api/auth/sso/google", json={"credential": "link-google-token"})
        assert resp.status_code == 200, resp.text

        user = db.query(User).filter(User.email == "linked.user@example.com").first()
        assert user is not None
        assert user.auth_provider == "google"
        assert user.auth_provider_subject == "google-sub-linked"
        assert user.password_login_enabled is True

        password_login = client.post("/api/auth/login", json={
            "email": "linked.user@example.com",
            "password": "LinkedPass123!",
        })
        assert password_login.status_code == 200, password_login.text

    def test_password_login_is_blocked_for_google_only_accounts(self, client, monkeypatch):
        _patch_password_helpers(monkeypatch)
        monkeypatch.setattr(auth_routes, "validate_google_id_token", _fake_google_claims)
        client.post("/api/auth/sso/google", json={"credential": "valid-google-token"})

        resp = client.post("/api/auth/login", json={
            "email": "google.user@example.com",
            "password": "AnyPassword123!",
        })
        assert resp.status_code == 400
        assert "Use SSO" in resp.json()["detail"] or "sign-in" in resp.json()["detail"]

    def test_change_password_is_blocked_for_google_only_accounts(self, client, monkeypatch):
        _patch_password_helpers(monkeypatch)
        monkeypatch.setattr(auth_routes, "validate_google_id_token", _fake_google_claims)
        login = client.post("/api/auth/sso/google", json={"credential": "valid-google-token"})
        token = login.json()["access_token"]

        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "old", "new_password": "NewPassword123!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "uses SSO" in resp.json()["detail"]

    def test_microsoft_sso_start_redirects_to_microsoft(self, client, monkeypatch):
        monkeypatch.setenv("MICROSOFT_CLIENT_ID", "ms-client-id")
        monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "ms-client-secret")

        resp = client.get("/api/auth/sso/microsoft/start?return_to=/settings", follow_redirects=False)

        assert resp.status_code in {302, 307}
        location = resp.headers["location"]
        assert "login.microsoftonline.com" in location
        assert "state=" in location
        assert "nonce=" in location

    def test_microsoft_sso_callback_creates_user_and_redirects_to_frontend(self, client, db, monkeypatch):
        _patch_password_helpers(monkeypatch)
        monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
        monkeypatch.setattr(auth_routes, "exchange_microsoft_code_for_claims", _fake_microsoft_claims)

        state = create_sso_state_token("microsoft", "/settings", "nonce-123")
        resp = client.get(
            f"/api/auth/sso/microsoft/callback?code=fake-code&state={state}",
            follow_redirects=False,
        )

        assert resp.status_code in {302, 307}
        location = resp.headers["location"]
        assert location.startswith("http://localhost:3000/auth/sso-complete#")
        assert "redirect=%2Fsettings" in location
        assert "access_token=" not in location
        assert "refresh_token=" not in location

        cookies = " ".join(resp.headers.get_list("set-cookie"))
        assert ACCESS_COOKIE_NAME in cookies
        assert REFRESH_COOKIE_NAME in cookies
        assert "httponly" in cookies.lower()

        user = db.query(User).filter(User.email == "microsoft.user@example.com").first()
        assert user is not None
        assert user.auth_provider == "microsoft"
        assert user.auth_provider_subject == "microsoft-sub-123"
        assert user.password_login_enabled is False
