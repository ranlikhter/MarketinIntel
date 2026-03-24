"""
API dependencies shared by protected routes.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.auth_cookies import ACCESS_COOKIE_NAME, get_request_token
from database.connection import get_db
from database.models import User, Workspace
from services.auth_service import verify_token
from services.workspace_service import (
    WORKSPACE_HEADER_NAME,
    get_accessible_workspace,
    resolve_active_workspace,
    build_scope_predicate,
)

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ActiveWorkspace:
    workspace_id: int | None
    workspace: Workspace | None
    membership_role: str | None = None

    @property
    def is_selected(self) -> bool:
        return self.workspace_id is not None


def _validate_access_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> dict:
    token = get_request_token(
        request,
        credentials,
        cookie_name=ACCESS_COOKIE_NAME,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_token_payload(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Return the validated access-token payload from a bearer header or auth cookie.
    """
    return _validate_access_token(request, credentials)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Also checks the Redis blocklist so tokens revoked on logout or
    password-change are rejected immediately instead of remaining valid
    until their natural expiry.
    """
    payload = _validate_access_token(request, credentials)

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


async def get_current_workspace(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActiveWorkspace:
    """
    Resolve the active workspace for this request.

    Selection order:
    1. ``X-Workspace-ID`` request header, if present and accessible.
    2. ``current_user.default_workspace_id``.
    3. First accessible owned/member workspace.
    4. No workspace selected yet -> fall back to legacy user-owned scope.
    """
    requested_workspace_id: int | None = None
    raw_workspace_id = request.headers.get(WORKSPACE_HEADER_NAME)
    if raw_workspace_id is not None and raw_workspace_id.strip():
        try:
            requested_workspace_id = int(raw_workspace_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{WORKSPACE_HEADER_NAME} must be an integer workspace ID",
            ) from exc

        workspace, membership = get_accessible_workspace(
            db,
            current_user,
            requested_workspace_id,
        )
        if workspace is None:
            existing_workspace = db.query(Workspace).filter(
                Workspace.id == requested_workspace_id,
                Workspace.is_active == True,
            ).first()
            if existing_workspace is None:
                raise HTTPException(status_code=404, detail="Workspace not found")
            raise HTTPException(status_code=403, detail="Access denied to workspace")

        return ActiveWorkspace(
            workspace_id=workspace.id,
            workspace=workspace,
            membership_role=membership.role.value if membership else "admin",
        )

    workspace, membership = resolve_active_workspace(db, current_user)
    if workspace is None:
        return ActiveWorkspace(workspace_id=None, workspace=None, membership_role=None)

    return ActiveWorkspace(
        workspace_id=workspace.id,
        workspace=workspace,
        membership_role=membership.role.value if membership else "admin",
    )


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


def check_usage_limit(
    user: User,
    resource_type: str,
    db: Session,
    workspace_id: int | None = None,
):
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
            build_scope_predicate(
                ProductMonitored,
                workspace_id=workspace_id,
                user_id=user.id,
            )
        ).count()

        if current_count >= user.products_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Product limit reached ({user.products_limit}). Upgrade your plan to add more products."
            )

    elif resource_type == "alerts":
        current_count = db.query(PriceAlert).filter(
            build_scope_predicate(
                PriceAlert,
                workspace_id=workspace_id,
                user_id=user.id,
            )
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
