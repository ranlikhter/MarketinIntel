"""
Redis Cache Service

Lightweight wrapper around Redis for TTL-based response caching.
Falls back gracefully when Redis is unavailable so the app keeps working.
"""

import json
import os
from typing import Any, Callable, Optional


def _get_redis_client():
    """Return a connected Redis client, or None if Redis is unreachable."""
    try:
        import redis
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        client = redis.Redis(
            host=host,
            port=port,
            db=db,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


def get_cached(key: str, ttl: int, compute_fn: Callable) -> Any:
    """
    Return cached value from Redis, or compute + store it if missing.

    Args:
        key:        Cache key string.
        ttl:        Time-to-live in seconds.
        compute_fn: Zero-argument callable that returns the fresh value.

    Returns:
        The cached or freshly-computed value.
    """
    client = _get_redis_client()

    if client:
        try:
            raw = client.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception:
            pass

    result = compute_fn()

    if client and result is not None:
        try:
            client.setex(key, ttl, json.dumps(result, default=str))
        except Exception:
            pass

    return result


def invalidate_cache(pattern: str) -> int:
    """
    Delete all Redis keys matching a glob pattern.

    Args:
        pattern: Glob pattern, e.g. "trendline:42:*" or "insights:dashboard:*"

    Returns:
        Number of keys deleted (0 if Redis is unavailable).
    """
    client = _get_redis_client()
    if not client:
        return 0
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception:
        return 0


def cache_set(key: str, value: Any, ttl: int) -> bool:
    """Explicitly store a value. Returns True on success."""
    client = _get_redis_client()
    if not client:
        return False
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception:
        return False


def cache_get(key: str) -> Optional[Any]:
    """Explicitly retrieve a value. Returns None on miss or error."""
    client = _get_redis_client()
    if not client:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception:
        return None
