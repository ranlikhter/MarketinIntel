"""
Sentry Observability Service

Initialises the Sentry SDK for:
  - FastAPI  (HTTP request tracing, unhandled exception capture)
  - Celery   (task tracing, worker errors)
  - SQLAlchemy (slow query detection)
  - Redis    (cache call tracing)
  - HTTPX    (outbound HTTP request tracing)

Call init_sentry() once at application startup — idempotent, safe to call
multiple times (subsequent calls are no-ops when DSN is not set).

Usage:
    from services.sentry_service import init_sentry
    init_sentry()
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SENTRY_INITIALISED = False


def init_sentry() -> None:
    """
    Initialise Sentry if SENTRY_DSN is present in the environment.
    No-op when DSN is missing (e.g. local dev without Sentry configured).
    """
    global _SENTRY_INITIALISED
    if _SENTRY_INITIALISED:
        return

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry: SENTRY_DSN not set — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env == "production"

        sentry_sdk.init(
            dsn=dsn,
            environment=app_env,
            release=os.getenv("APP_VERSION", "unknown"),

            # ── Performance ───────────────────────────────────────────────
            # Capture 20% of requests for tracing in production,
            # 100% in development/staging so every request is visible.
            traces_sample_rate=0.2 if is_production else 1.0,

            # ── Integrations ──────────────────────────────────────────────
            integrations=[
                # FastAPI / Starlette — traces every HTTP request
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),

                # Celery — traces every task; captures task failures
                CeleryIntegration(
                    monitor_beat_tasks=True,   # Cron-job monitoring
                    propagate_traces=True,     # Link worker traces to HTTP traces
                ),

                # SQLAlchemy — traces slow queries; strips VALUES from INSERT
                SqlalchemyIntegration(),

                # Redis — traces cache hits/misses
                RedisIntegration(),

                # HTTPX — traces outbound requests (Shopify, WooCommerce, Apify)
                HttpxIntegration(),

                # Logging — sends ERROR+ log records to Sentry as breadcrumbs
                LoggingIntegration(
                    level=logging.INFO,        # Breadcrumb level
                    event_level=logging.ERROR, # Send as Sentry event
                ),
            ],

            # ── Privacy / Security ────────────────────────────────────────
            # Strip sensitive request headers before sending to Sentry
            before_send=_before_send,

            # Never send events from test runs
            enabled=app_env not in {"test", "testing"},

            # Attach server name (hostname) to every event for multi-instance debugging
            server_name=os.getenv("HOSTNAME", "unknown"),

            # Max breadcrumb trail (actions leading up to the error)
            max_breadcrumbs=50,
        )

        _SENTRY_INITIALISED = True
        logger.info("Sentry: initialised (env=%s, production=%s)", app_env, is_production)

    except ImportError:
        logger.warning(
            "Sentry: sentry-sdk not installed — run: pip install sentry-sdk[fastapi,celery]"
        )
    except Exception as exc:
        # Never crash the app because Sentry failed to start
        logger.error("Sentry: failed to initialise — %s", exc)


def _before_send(event: dict, hint: dict) -> dict | None:
    """
    Strip sensitive data from every event before it leaves the server.
    Runs just before the event is transmitted to Sentry's servers.
    """
    # Remove auth headers
    _SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-shopify-access-token",
        "x-wc-consumer-key",
        "x-wc-consumer-secret",
    }

    request = event.get("request", {})
    headers = request.get("headers", {})
    for key in list(headers.keys()):
        if key.lower() in _SENSITIVE_HEADERS:
            headers[key] = "[Filtered]"

    # Remove password fields from request body
    data = request.get("data", {})
    if isinstance(data, dict):
        for key in list(data.keys()):
            if "password" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                data[key] = "[Filtered]"

    return event


# ── Manual capture helpers ────────────────────────────────────────────────────

def capture_exception(exc: Exception, **kwargs) -> None:
    """
    Manually capture an exception and send it to Sentry.
    Use for expected-but-notable errors (e.g. third-party API failures).

    Example:
        try:
            shopify.sync()
        except ShopifyError as e:
            capture_exception(e, tags={"store": shop_url})
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.get("tags", {}).items():
                scope.set_tag(key, value)
            for key, value in kwargs.get("extra", {}).items():
                scope.set_extra(key, value)
            if user := kwargs.get("user"):
                scope.set_user(user)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass  # Never let Sentry helpers crash the app


def capture_message(message: str, level: str = "info", **kwargs) -> None:
    """
    Send a plain message event to Sentry (no exception required).

    Example:
        capture_message("Shopify sync completed", level="info",
                        extra={"products_synced": 250, "store": shop_url})
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.get("tags", {}).items():
                scope.set_tag(key, value)
            for key, value in kwargs.get("extra", {}).items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


def set_user_context(user_id: int | None, email: str | None = None) -> None:
    """
    Attach the current authenticated user to all subsequent Sentry events
    in this request context. Call from auth middleware or route dependencies.
    """
    try:
        import sentry_sdk
        if user_id:
            sentry_sdk.set_user({"id": str(user_id), "email": email or ""})
        else:
            sentry_sdk.set_user(None)
    except Exception:
        pass
