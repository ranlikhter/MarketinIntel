"""
JWT Token Blocklist (Redis-backed)

Allows server-side token revocation on logout and password change.
Each revoked token's JTI (JWT ID) is stored in Redis with a TTL matching
the remaining lifetime of the token, so Redis automatically cleans up.

Usage:
    from services.token_blocklist import blocklist

    # Revoke a token (on logout)
    await blocklist.revoke(jti, expires_at)

    # Check if revoked (in get_current_user)
    if await blocklist.is_revoked(jti):
        raise HTTPException(401, "Token has been revoked")
"""

import os
import time
from typing import Optional

_REDIS_URL = (
    f"redis://:{os.getenv('REDIS_PASSWORD', '')}@"
    f"{os.getenv('REDIS_HOST', 'localhost')}"
    f":{os.getenv('REDIS_PORT', '6379')}"
    f"/{os.getenv('REDIS_DB', '0')}"
).replace("redis://:@", "redis://")   # omit empty password

_KEY_PREFIX = "jwt_blocklist:"


class TokenBlocklist:
    """
    Thin Redis wrapper for JTI blocklisting.

    Falls back gracefully when Redis is unavailable so that the rest of the
    application keeps running (tokens simply can't be revoked until Redis
    recovers).  This is logged as an error so ops can react.
    """

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis
            self._client = redis.Redis.from_url(
                _REDIS_URL,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            self._client.ping()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "TokenBlocklist: Redis unavailable — token revocation disabled: %s", exc
            )
            self._client = None
        return self._client

    def revoke(self, jti: str, exp: Optional[int] = None) -> bool:
        """
        Add a JTI to the blocklist.

        Args:
            jti: The JWT ID claim from the token payload.
            exp: Token expiry as a UNIX timestamp (from the 'exp' claim).
                 Used to set an appropriate TTL so Redis self-cleans.

        Returns:
            True if successfully stored, False if Redis is unavailable.
        """
        client = self._get_client()
        if client is None:
            return False
        try:
            key = _KEY_PREFIX + jti
            if exp is not None:
                ttl = max(int(exp - time.time()), 1)
                client.setex(key, ttl, "1")
            else:
                # No expiry info — store for 30 days as a safe upper bound
                client.setex(key, 60 * 60 * 24 * 30, "1")
            return True
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("TokenBlocklist.revoke failed: %s", exc)
            return False

    def is_revoked(self, jti: str) -> bool:
        """
        Check whether a JTI has been revoked.

        Returns False (not revoked / pass-through) when Redis is unavailable,
        so auth still works even without Redis.
        """
        client = self._get_client()
        if client is None:
            return False
        try:
            return client.exists(_KEY_PREFIX + jti) == 1
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("TokenBlocklist.is_revoked failed: %s", exc)
            return False


# Module-level singleton — import and use directly
blocklist = TokenBlocklist()
