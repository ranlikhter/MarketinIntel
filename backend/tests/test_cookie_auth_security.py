"""
Security regression tests for browser cookie authentication.
"""

import asyncio
import inspect

from fastapi import Request

from api.auth_cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from api.dependencies import get_current_token_payload
from api.routes import auth as auth_routes
from api.routes import events as events_routes
from database.models import User
from services.auth_service import create_access_token, create_refresh_token


def _create_user(db, email: str = "cookie.user@example.com") -> User:
    user = User(
        email=email,
        hashed_password="stored-hash",
        full_name="Cookie User",
        auth_provider="local",
        password_login_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _set_cookie_headers(response) -> str:
    return " ".join(response.headers.get_list("set-cookie"))


class TestCookieAuthSecurity:
    def test_login_sets_http_only_auth_cookies(self, client, db, monkeypatch):
        user = _create_user(db)
        monkeypatch.setattr(
            auth_routes,
            "verify_password",
            lambda plain_password, _hashed_password: plain_password == "CookiePass123!",
        )

        response = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "CookiePass123!"},
        )

        assert response.status_code == 200, response.text
        cookies = _set_cookie_headers(response).lower()
        assert ACCESS_COOKIE_NAME in cookies
        assert REFRESH_COOKIE_NAME in cookies
        assert "httponly" in cookies
        assert "samesite=lax" in cookies

    def test_me_accepts_secure_access_cookie(self, client, db):
        user = _create_user(db, email="me.cookie@example.com")
        client.cookies.set(
            ACCESS_COOKIE_NAME,
            create_access_token({"sub": str(user.id)}),
        )

        response = client.get("/api/auth/me")

        assert response.status_code == 200, response.text
        assert response.json()["email"] == user.email

    def test_refresh_accepts_secure_refresh_cookie(self, client, db):
        user = _create_user(db, email="refresh.cookie@example.com")
        client.cookies.set(
            REFRESH_COOKIE_NAME,
            create_refresh_token({"sub": str(user.id)}),
        )

        response = client.post("/api/auth/refresh")

        assert response.status_code == 200, response.text
        assert response.json()["token_type"] == "bearer"
        cookies = _set_cookie_headers(response).lower()
        assert ACCESS_COOKIE_NAME in cookies
        assert "httponly" in cookies

    def test_events_stream_uses_cookie_auth_without_url_token(self, db):
        user = _create_user(db, email="events.cookie@example.com")
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/events",
                "query_string": b"",
                "headers": [
                    (
                        b"cookie",
                        f"{ACCESS_COOKIE_NAME}={create_access_token({'sub': str(user.id)})}".encode(),
                    )
                ],
            }
        )

        payload = asyncio.run(get_current_token_payload(request=request, credentials=None))
        parameters = inspect.signature(events_routes.price_event_stream).parameters

        assert payload["sub"] == str(user.id)
        assert "token" not in parameters

    def test_events_stream_requires_authenticated_cookie_or_header(self, client):
        response = client.get("/api/events?token=fake-jwt")

        assert response.status_code == 401
