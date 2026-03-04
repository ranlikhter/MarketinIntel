"""
Rate limiting for MarketIntel API.

Two layers:
1. Global default (slowapi) — 200 requests / hour per user/IP, applied via
   SlowAPIMiddleware in main.py.  Individual routes can tighten this with
   @limiter.limit("N/period") if they import `limiter` here.

2. AuthRateLimitMiddleware — applied in main.py before SlowAPIMiddleware;
   caps sensitive auth endpoints at 10 requests / minute per IP without
   needing to touch the existing route signatures.
"""

import threading
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware


# ── 1. Global slowapi limiter ─────────────────────────────────────────────────

def _rate_limit_key(request: Request) -> str:
    """Key by authenticated user-id when available, otherwise by remote IP."""
    user_id = request.headers.get("X-User-ID")
    return f"user:{user_id}" if user_id else get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=["200/hour"])


# ── 2. Auth brute-force protection middleware ─────────────────────────────────

_AUTH_PATHS = {
    "/api/auth/login",
    "/api/auth/signup",
    "/api/auth/register",
    "/api/auth/forgot-password",
}

_AUTH_LIMIT = 10       # max requests
_AUTH_WINDOW = 60      # per N seconds


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Caps login / signup / forgot-password at 10 requests per minute per IP.
    Applied before the global slowapi middleware so auth endpoints get both
    the strict per-path limit AND the global 200/hr cap.
    """

    def __init__(self, app, max_calls: int = _AUTH_LIMIT, window_seconds: int = _AUTH_WINDOW):
        super().__init__(app)
        self._max_calls = max_calls
        self._window = window_seconds
        self._buckets: dict[str, deque] = {}
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _AUTH_PATHS:
            ip = get_remote_address(request)
            now = time.monotonic()

            with self._lock:
                bucket = self._buckets.setdefault(ip, deque())
                # Evict timestamps outside the window
                while bucket and bucket[0] < now - self._window:
                    bucket.popleft()

                if len(bucket) >= self._max_calls:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please wait a moment and try again."},
                        headers={"Retry-After": str(self._window)},
                    )
                bucket.append(now)

        return await call_next(request)
