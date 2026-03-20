"""
Authentication Service
Handles password hashing, JWT token creation/verification
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "your-secret-key-change-this-in-production"
# WARNING: The fallback above is for development only. Set JWT_SECRET_KEY in production.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password

    Args:
        plain_password: Password to verify
        hashed_password: Stored hashed password

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Custom expiration time (optional)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token (longer expiration)

    Args:
        data: Data to encode in the token

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_sso_state_token(provider: str, return_to: str, nonce: str) -> str:
    """
    Create a short-lived signed state token for OAuth redirects.
    """
    expire = datetime.utcnow() + timedelta(minutes=15)
    data = {
        "provider": provider,
        "return_to": return_to,
        "nonce": nonce,
        "type": "sso_state",
        "exp": expire,
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_sso_state_token(token: str, provider: str) -> Optional[dict]:
    """
    Verify the OAuth state token for a specific provider.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "sso_state":
            return None
        if payload.get("provider") != provider:
            return None
        return payload
    except JWTError:
        return None


def verify_token(token: str, expected_type: str = "access") -> Optional[dict]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload dict, or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Reject tokens with wrong type (prevents refresh tokens being used as access tokens)
        token_type = payload.get("type")
        if token_type and token_type != expected_type:
            return None
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    Extract user ID from JWT token

    Args:
        token: JWT token string

    Returns:
        User ID (integer) or None if invalid
    """
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
    """
    Create a token for email verification

    Args:
        email: User's email address

    Returns:
        Verification token string
    """
    expire = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
    data = {
        "sub": email,
        "type": "email_verification",
        "exp": expire
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_email_token(token: str) -> Optional[str]:
    """
    Verify an email verification token

    Args:
        token: Email verification token

    Returns:
        Email address if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_password_reset_token(email: str) -> str:
    """
    Create a token for password reset

    Args:
        email: User's email address

    Returns:
        Reset token string
    """
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    data = {
        "sub": email,
        "type": "password_reset",
        "exp": expire
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token

    Args:
        token: Password reset token

    Returns:
        Email address if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
