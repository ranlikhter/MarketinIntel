"""
API Key management endpoints.

Users generate API keys so external tools / automation scripts can call
MarketIntel without using their login password.

Key lifecycle:
  POST   /api/auth/api-keys          → generate key (returns full key ONCE)
  GET    /api/auth/api-keys          → list keys (name, prefix, dates — never full key)
  DELETE /api/auth/api-keys/{id}     → revoke key
  POST   /api/auth/api-keys/{id}/rotate → revoke old + issue new key

The full key is never stored — only a SHA-256 hash.
"""

import hashlib
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import ApiKey, User
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth/api-keys", tags=["API Keys"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str  # Friendly label, e.g. "Zapier integration"


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreated(ApiKeyResponse):
    """Returned only at creation — includes the full plaintext key."""
    full_key: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_key() -> tuple[str, str, str]:
    """
    Returns (full_key, prefix, sha256_hash).
    Format: mi_<40 hex chars>
    """
    raw = os.urandom(20).hex()          # 40 hex chars
    full_key = f"mi_{raw}"
    prefix = full_key[:10]              # "mi_" + first 7 hex chars
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


def _fmt(key: ApiKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "is_active": key.is_active,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "created_at": key.created_at.isoformat(),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the authenticated user (no secrets returned)."""
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [_fmt(k) for k in keys]


@router.post("", status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new API key.  The full key is returned **only once** — store it safely.
    """
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Key name is required")

    # Limit to 20 active keys per user
    active_count = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id,
        ApiKey.is_active == True,
    ).count()
    if active_count >= 20:
        raise HTTPException(status_code=429, detail="Maximum of 20 active API keys reached")

    full_key, prefix, key_hash = _generate_key()

    key = ApiKey(
        user_id=current_user.id,
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
    )
    db.add(key)
    db.commit()
    db.refresh(key)

    result = _fmt(key)
    result["full_key"] = full_key
    return result


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (delete) an API key by ID."""
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(key)
    db.commit()
    return {"success": True, "message": "API key revoked"}


@router.post("/{key_id}/rotate", status_code=201)
def rotate_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rotate an API key: revoke the old one and issue a new key with the same name.
    Returns the new full key (shown once).
    """
    old_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id,
    ).first()
    if not old_key:
        raise HTTPException(status_code=404, detail="API key not found")

    name = old_key.name
    db.delete(old_key)

    full_key, prefix, key_hash = _generate_key()
    new_key = ApiKey(
        user_id=current_user.id,
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    result = _fmt(new_key)
    result["full_key"] = full_key
    return result
