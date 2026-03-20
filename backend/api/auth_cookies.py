"""
Cookie helpers for browser-based authentication sessions.
"""

import os

from fastapi import Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

SAFE_LOCAL_ENVS = {"development", "dev", "local", "test", "testing"}

ACCESS_COOKIE_NAME = os.getenv("AUTH_ACCESS_COOKIE_NAME", "marketintel_access_token")
REFRESH_COOKIE_NAME = os.getenv("AUTH_REFRESH_COOKIE_NAME", "marketintel_refresh_token")


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _cookie_domain() -> str | None:
    value = (os.getenv("AUTH_COOKIE_DOMAIN") or "").strip()
    return value or None


def _cookie_secure() -> bool:
    app_env = (os.getenv("APP_ENV") or "development").strip().lower()
    default_secure = app_env not in SAFE_LOCAL_ENVS
    return _env_flag("AUTH_COOKIE_SECURE", default_secure)


def _cookie_samesite() -> str:
    value = (os.getenv("AUTH_COOKIE_SAMESITE") or "lax").strip().lower()
    if value not in {"lax", "strict", "none"}:
        return "lax"
    return value


def _cookie_settings(max_age: int) -> dict:
    secure = _cookie_secure()
    samesite = _cookie_samesite()

    if samesite == "none":
        secure = True

    settings = {
        "httponly": True,
        "max_age": max_age,
        "path": "/",
        "samesite": samesite,
        "secure": secure,
    }

    domain = _cookie_domain()
    if domain:
        settings["domain"] = domain

    return settings


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        **_cookie_settings(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        **_cookie_settings(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
    )


def set_access_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        **_cookie_settings(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    )


def clear_auth_cookies(response: Response) -> None:
    cookie_options = {"path": "/"}
    domain = _cookie_domain()
    if domain:
        cookie_options["domain"] = domain

    response.delete_cookie(ACCESS_COOKIE_NAME, **cookie_options)
    response.delete_cookie(REFRESH_COOKIE_NAME, **cookie_options)


def get_request_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    cookie_name: str,
) -> str | None:
    if credentials and credentials.scheme and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return request.cookies.get(cookie_name)
