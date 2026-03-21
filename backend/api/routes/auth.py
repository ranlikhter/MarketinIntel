"""
Authentication API Endpoints
Handles signup, login, logout, password reset, email verification
"""

import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import ConfigDict, BaseModel, EmailStr
from typing import Optional
from datetime import datetime


from api.auth_cookies import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    get_request_token,
    set_access_cookie,
    set_auth_cookies,
)
from api.dependencies import get_current_user
from database.connection import get_db
from database.models import User, SubscriptionTier, SubscriptionStatus
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_sso_state_token,
    verify_sso_state_token,
    create_email_verification_token,
    verify_email_token,
    create_password_reset_token,
    verify_password_reset_token
)
from services.email_service import email_service
from services.sso_service import (
    SSOValidationError,
    build_microsoft_authorize_url,
    exchange_microsoft_code_for_claims,
    validate_google_id_token,
)
from services.workspace_service import ensure_personal_workspace

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


# Pydantic Models
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    active_workspace_id: Optional[int]
    auth_provider: str
    avatar_url: Optional[str]
    password_login_enabled: bool
    subscription_tier: str
    subscription_status: str
    is_verified: bool
    products_limit: int
    matches_limit: int
    alerts_limit: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class GoogleSSORequest(BaseModel):
    credential: str


def get_provider_display_name(provider: str) -> str:
    labels = {
        "google": "Google",
        "microsoft": "Microsoft",
        "local": "Email & Password",
    }
    return labels.get(provider or "", provider.capitalize() if provider else "SSO")


def sanitize_return_to(return_to: Optional[str]) -> str:
    if not return_to:
        return "/dashboard"
    if not return_to.startswith("/") or return_to.startswith("//"):
        return "/dashboard"
    return return_to


def build_frontend_sso_redirect(
    return_to: str,
    *,
    error: Optional[str] = None,
) -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    params = {"redirect": sanitize_return_to(return_to)}

    if error:
        params["error"] = error

    return f"{frontend_url}/auth/sso-complete#{urlencode(params)}"


def build_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "active_workspace_id": user.default_workspace_id,
        "auth_provider": user.auth_provider,
        "avatar_url": user.avatar_url,
        "password_login_enabled": user.password_login_enabled,
        "subscription_tier": user.subscription_tier.value,
        "subscription_status": user.subscription_status.value,
        "is_verified": user.is_verified,
        "products_limit": user.products_limit,
        "matches_limit": user.matches_limit,
        "alerts_limit": user.alerts_limit,
    }


def build_token_response(user: User) -> TokenResponse:
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            **build_user_payload(user),
            "created_at": user.created_at,
        },
    )


def build_authenticated_response(response: Response, user: User) -> TokenResponse:
    token_response = build_token_response(user)
    set_auth_cookies(
        response,
        token_response.access_token,
        token_response.refresh_token,
    )
    return token_response


def upsert_sso_user(db: Session, provider: str, claims: dict) -> User:
    user = db.query(User).filter(User.email == claims["email"]).first()

    if user and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated"
        )

    if user and user.auth_provider in {"google", "microsoft"} and user.auth_provider != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This email is already linked to {get_provider_display_name(user.auth_provider)} sign-in"
        )

    if user and user.auth_provider_subject and user.auth_provider_subject != claims["sub"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This email is already linked to a different {get_provider_display_name(provider)} account"
        )

    if not user:
        user = User(
            email=claims["email"],
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=claims.get("full_name"),
            auth_provider=provider,
            auth_provider_subject=claims["sub"],
            avatar_url=claims.get("avatar_url"),
            password_login_enabled=False,
            subscription_tier=SubscriptionTier.FREE,
            subscription_status=SubscriptionStatus.ACTIVE,
            products_limit=5,
            matches_limit=10,
            alerts_limit=1,
            is_verified=claims.get("email_verified", False),
            email_verified_at=datetime.utcnow() if claims.get("email_verified", False) else None,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()
    else:
        user.auth_provider = provider
        user.auth_provider_subject = claims["sub"]
        if claims.get("full_name") and not user.full_name:
            user.full_name = claims["full_name"]
        if claims.get("avatar_url"):
            user.avatar_url = claims["avatar_url"]
        if claims.get("email_verified") and not user.is_verified:
            user.is_verified = True
            user.email_verified_at = datetime.utcnow()

    ensure_personal_workspace(db, user)
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return user


# ============================================
# Authentication Endpoints
# ============================================

@router.post("/signup", response_model=TokenResponse)
@router.post("/register", response_model=TokenResponse)
async def signup(
    request: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Register a new user account

    - **email**: Valid email address
    - **password**: Password (min 8 characters recommended)
    - **full_name**: Optional full name

    Returns JWT tokens and user info
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate password strength (basic check)
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Create new user with FREE tier
    hashed_pwd = hash_password(request.password)

    new_user = User(
        email=request.email,
        hashed_password=hashed_pwd,
        full_name=request.full_name,
        auth_provider="local",
        password_login_enabled=True,
        subscription_tier=SubscriptionTier.FREE,
        subscription_status=SubscriptionStatus.ACTIVE,
        products_limit=5,
        matches_limit=10,
        alerts_limit=1,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.flush()
    ensure_personal_workspace(db, new_user)
    db.commit()
    db.refresh(new_user)

    # Send welcome + verification emails
    verification_token = create_email_verification_token(new_user.email)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    verification_url = f"{frontend_url}/verify-email?token={verification_token}"

    try:
        email_service.send_welcome_email(new_user.email, new_user.full_name or "there")
        email_service.send_verification_email(
            new_user.email, new_user.full_name or "there", verification_url
        )
    except Exception as e:
        print(f"Failed to send welcome/verification email: {e}")

    return build_authenticated_response(response, new_user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Login to existing account

    - **email**: Registered email address
    - **password**: Account password

    Returns JWT tokens and user info
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.password_login_enabled:
        provider_name = get_provider_display_name(user.auth_provider or "SSO")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This account uses {provider_name} sign-in. Use SSO to log in."
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated"
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    return build_authenticated_response(response, user)


@router.post("/sso/google", response_model=TokenResponse)
async def login_with_google(
    request: GoogleSSORequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Exchange a Google Identity Services credential for local JWT tokens.
    """
    try:
        claims = await validate_google_id_token(request.credential)
    except SSOValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    user = upsert_sso_user(db, "google", claims)
    return build_authenticated_response(response, user)


@router.get("/sso/microsoft/start")
async def start_microsoft_sso(request: Request, return_to: Optional[str] = None):
    """
    Start Microsoft OAuth sign-in by redirecting to Microsoft.
    """
    safe_return_to = sanitize_return_to(return_to)
    nonce = secrets.token_urlsafe(32)
    state_token = create_sso_state_token("microsoft", safe_return_to, nonce)

    try:
        authorize_url = build_microsoft_authorize_url(
            state_token=state_token,
            nonce=nonce,
            redirect_uri=str(request.url_for("microsoft_sso_callback")),
        )
    except SSOValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    return RedirectResponse(authorize_url, status_code=status.HTTP_302_FOUND)


@router.get("/sso/microsoft/callback", name="microsoft_sso_callback")
async def microsoft_sso_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Complete Microsoft OAuth sign-in and redirect back to the frontend.
    """
    safe_return_to = "/dashboard"

    if state:
        state_payload = verify_sso_state_token(state, "microsoft")
        if state_payload:
            safe_return_to = sanitize_return_to(state_payload.get("return_to"))
        else:
            return RedirectResponse(
                build_frontend_sso_redirect("/dashboard", error="Microsoft sign-in session is invalid or expired"),
                status_code=status.HTTP_302_FOUND,
            )
    elif error:
        safe_return_to = "/dashboard"

    if error:
        message = error_description or error.replace("_", " ")
        return RedirectResponse(
            build_frontend_sso_redirect(safe_return_to, error=message),
            status_code=status.HTTP_302_FOUND,
        )

    if not code or not state:
        return RedirectResponse(
            build_frontend_sso_redirect(safe_return_to, error="Microsoft sign-in did not return an authorization code"),
            status_code=status.HTTP_302_FOUND,
        )

    state_payload = verify_sso_state_token(state, "microsoft")
    if not state_payload:
        return RedirectResponse(
            build_frontend_sso_redirect("/dashboard", error="Microsoft sign-in session is invalid or expired"),
            status_code=status.HTTP_302_FOUND,
        )

    try:
        claims = await exchange_microsoft_code_for_claims(
            code=code,
            redirect_uri=str(request.url_for("microsoft_sso_callback")),
            expected_nonce=state_payload["nonce"],
        )
        user = upsert_sso_user(db, "microsoft", claims)
    except (SSOValidationError, HTTPException) as exc:
        message = exc.detail if isinstance(exc, HTTPException) else str(exc)
        return RedirectResponse(
            build_frontend_sso_redirect(safe_return_to, error=message),
            status_code=status.HTTP_302_FOUND,
        )

    token_response = build_token_response(user)
    redirect_response = RedirectResponse(
        build_frontend_sso_redirect(safe_return_to),
        status_code=status.HTTP_302_FOUND,
    )
    set_auth_cookies(
        redirect_response,
        token_response.access_token,
        token_response.refresh_token,
    )
    return redirect_response


@router.post("/refresh")
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token

    Accepts the refresh token from either Authorization header or secure cookie.
    """
    token = get_request_token(
        request,
        credentials,
        cookie_name=REFRESH_COOKIE_NAME,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required"
        )

    payload = verify_token(token, expected_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new access token
    new_access_token = create_access_token(data={"sub": str(user.id)})
    set_access_cookie(response, new_access_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user's information

    Accepts a bearer token or the secure auth cookie.
    """
    return UserResponse(
        **build_user_payload(current_user),
        created_at=current_user.created_at
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information (full name)"""
    if request.full_name is not None:
        current_user.full_name = request.full_name

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        **build_user_payload(current_user),
        created_at=current_user.created_at
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for authenticated user"""
    if not current_user.password_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses SSO and does not have a password to change"
        )

    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )

    current_user.hashed_password = hash_password(request.new_password)
    db.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.post("/verify-email")
async def verify_email(
    request: Optional[VerifyEmailRequest] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Verify user's email address

    - **token**: Email verification token from email link
    """
    verification_token = request.token if request else token
    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is required"
        )

    email = verify_email_token(verification_token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.is_verified:
        return {
            "success": True,
            "message": "Email already verified"
        }

    # Mark email as verified
    user.is_verified = True
    user.email_verified_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": "Email verified successfully"
    }


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Request password reset email

    - **email**: Registered email address

    Sends password reset link to email
    """
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success (don't reveal if email exists)
    if not user:
        return {
            "success": True,
            "message": "If that email exists, a reset link has been sent"
        }

    if not user.password_login_enabled:
        return {
            "success": True,
            "message": "If that email exists, a reset link has been sent"
        }

    # Generate reset token and send email
    reset_token = create_password_reset_token(user.email)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"

    try:
        email_service.send_password_reset_email(user.email, reset_url)
    except Exception as e:
        print(f"Failed to send reset email: {e}")

    return {
        "success": True,
        "message": "If that email exists, a reset link has been sent"
    }


@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Reset password using token from email

    - **token**: Reset token from email link
    - **new_password**: New password (min 8 characters)
    """
    email = verify_password_reset_token(request.token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.password_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses SSO and cannot reset a password"
        )

    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Update password
    user.hashed_password = hash_password(request.new_password)
    db.commit()

    return {
        "success": True,
        "message": "Password reset successfully"
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Clear browser auth cookies and end the current browser session.
    """
    clear_auth_cookies(response)
    return {
        "success": True,
        "message": "Logged out successfully"
    }
