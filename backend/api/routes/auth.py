"""
Authentication API Endpoints
Handles signup, login, logout, password reset, email verification
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import User, SubscriptionTier, SubscriptionStatus
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_email_verification_token,
    verify_email_token,
    create_password_reset_token,
    verify_password_reset_token
)
from services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


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
    subscription_tier: str
    subscription_status: str
    is_verified: bool
    products_limit: int
    matches_limit: int
    alerts_limit: int
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# ============================================
# Authentication Endpoints
# ============================================

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
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
        subscription_tier=SubscriptionTier.FREE,
        subscription_status=SubscriptionStatus.ACTIVE,
        products_limit=5,
        matches_limit=10,
        alerts_limit=1,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create JWT tokens
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    # Send verification email
    verification_token = create_email_verification_token(new_user.email)
    verification_url = f"http://localhost:3000/verify-email?token={verification_token}"

    try:
        email_service.send_welcome_email(new_user.email, new_user.full_name or "there")
        # TODO: Send verification email with link
    except Exception as e:
        print(f"Failed to send welcome email: {e}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "subscription_tier": new_user.subscription_tier.value,
            "subscription_status": new_user.subscription_status.value,
            "is_verified": new_user.is_verified,
            "products_limit": new_user.products_limit,
            "matches_limit": new_user.matches_limit,
            "alerts_limit": new_user.alerts_limit
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
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

    # Create JWT tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "subscription_tier": user.subscription_tier.value,
            "subscription_status": user.subscription_status.value,
            "is_verified": user.is_verified,
            "products_limit": user.products_limit,
            "matches_limit": user.matches_limit,
            "alerts_limit": user.alerts_limit
        }
    )


@router.post("/refresh")
async def refresh_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token

    Send refresh token in Authorization header
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if it's a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
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

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's information

    Requires valid JWT token in Authorization header
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        subscription_tier=user.subscription_tier.value,
        subscription_status=user.subscription_status.value,
        is_verified=user.is_verified,
        products_limit=user.products_limit,
        matches_limit=user.matches_limit,
        alerts_limit=user.alerts_limit,
        created_at=user.created_at
    )


@router.post("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify user's email address

    - **token**: Email verification token from email link
    """
    email = verify_email_token(token)

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

    # Generate reset token
    reset_token = create_password_reset_token(user.email)
    reset_url = f"http://localhost:3000/reset-password?token={reset_token}"

    # TODO: Send email with reset link
    try:
        # email_service.send_password_reset_email(user.email, reset_url)
        print(f"Password reset link: {reset_url}")
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
async def logout():
    """
    Logout (client-side token removal)

    Server doesn't maintain session state, so logout is handled client-side
    by removing the JWT token from storage.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }
