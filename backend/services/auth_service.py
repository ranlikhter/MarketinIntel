"""
Authentication Service
Handles password hashing, JWT token creation/verification
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
import uuid
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# Configuration — require a real secret in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("APP_ENV", "development") == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is required in production. "
            "Generate one with: openssl rand -hex 32"
        )
    SECRET_KEY = "dev-only-insecure-key-set-JWT_SECRET_KEY-in-production"
    log.warning("JWT_SECRET_KEY not set — using insecure development fallback")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Embeds a unique `jti` (JWT ID) so the token can be individually revoked
    by adding the JTI to the Redis blocklist on logout or password change.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token (longer expiration).

    Also embeds a `jti` so it can be blocklisted server-side.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Note: blocklist checking (Redis) is done in the FastAPI dependency
    (api/dependencies.py) so this function stays synchronous and reusable.

    Returns:
        Decoded payload dict, or None if invalid / wrong type.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type and token_type != expected_type:
            return None
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user ID (integer) from a JWT access token."""
    payload = verify_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return None


def create_email_verification_token(email: str) -> str:
    """Create a short-lived token for email verification (24 h)."""
    expire = datetime.utcnow() + timedelta(hours=24)
    data = {
        "sub": email,
        "type": "email_verification",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_email_token(token: str) -> Optional[str]:
    """Verify an email verification token. Returns email or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_password_reset_token(email: str) -> str:
    """Create a short-lived token for password reset (1 h)."""
    expire = datetime.utcnow() + timedelta(hours=1)
    data = {
        "sub": email,
        "type": "password_reset",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token. Returns email or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
