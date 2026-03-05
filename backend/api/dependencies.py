"""
API Dependencies
Reusable dependencies for route protection and user authentication
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.auth_service import verify_token
from services.token_blocklist import blocklist

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Also checks the Redis blocklist so tokens revoked on logout or
    password-change are rejected immediately instead of remaining valid
    until their natural expiry.
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Blocklist check — reject revoked tokens
    jti = payload.get("jti")
    if jti and blocklist.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated"
        )

    return user


async def get_current_active_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and ensure email is verified

    Use this for routes that require email verification

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Verified user object

    Raises:
        HTTPException: If email is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this feature."
        )

    return current_user


def _enforce_trial_limits(user: User) -> None:
    """
    Downgrade usage limits to FREE-tier values when a trial has expired.

    Called by check_usage_limit so that expired-trial users cannot exceed
    free-tier quotas even if their DB limits were set to a higher value when
    the trial was created.  The DB record is intentionally NOT mutated here
    to keep the function read-only; billing webhooks handle permanent tier
    changes.
    """
    from database.models import SubscriptionStatus
    from datetime import datetime

    if (
        user.trial_ends_at is not None
        and user.trial_ends_at < datetime.utcnow()
        and user.subscription_status == SubscriptionStatus.TRIALING
    ):
        # Temporarily cap limits to free-tier values for this request
        user.products_limit = min(user.products_limit, 5)
        user.alerts_limit = min(user.alerts_limit, 1)
        user.matches_limit = min(user.matches_limit, 10)


def check_usage_limit(user: User, resource_type: str, db: Session):
    """
    Check if user has reached their usage limit for a resource.

    Also enforces free-tier limits for users whose trial has expired but
    whose subscription_status hasn't been updated yet by a billing webhook.

    Args:
        user: User object
        resource_type: Type of resource ("products", "alerts", etc.)
        db: Database session

    Raises:
        HTTPException: If limit is reached

    Example:
        check_usage_limit(current_user, "products", db)
    """
    _enforce_trial_limits(user)

    from database.models import ProductMonitored, PriceAlert

    if resource_type == "products":
        current_count = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == user.id
        ).count()

        if current_count >= user.products_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Product limit reached ({user.products_limit}). Upgrade your plan to add more products."
            )

    elif resource_type == "alerts":
        current_count = db.query(PriceAlert).filter(
            PriceAlert.user_id == user.id
        ).count()

        if current_count >= user.alerts_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Alert limit reached ({user.alerts_limit}). Upgrade your plan to create more alerts."
            )


async def require_subscription_tier(
    required_tier: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require user to have a specific subscription tier or higher

    Args:
        required_tier: Minimum tier required ("pro", "business", "enterprise")
        current_user: Current authenticated user

    Returns:
        User if authorized

    Raises:
        HTTPException: If user doesn't have required tier

    Example:
        @router.get("/pro-feature")
        async def pro_only(user: User = Depends(lambda: require_subscription_tier("pro", get_current_user()))):
            pass
    """
    tier_hierarchy = {
        "free": 0,
        "pro": 1,
        "business": 2,
        "enterprise": 3
    }

    user_tier_level = tier_hierarchy.get(current_user.subscription_tier.value, 0)
    required_tier_level = tier_hierarchy.get(required_tier.lower(), 999)

    if user_tier_level < required_tier_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires {required_tier.upper()} plan or higher. Please upgrade your subscription."
        )

    return current_user
