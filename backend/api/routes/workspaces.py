"""
Workspace / Team collaboration endpoints.

Workspaces let Business/Enterprise users share products, views, and alerts
across a team with role-based access control.

Roles:
  admin  → can manage members, delete workspace
  editor → can create/update products and alerts
  viewer → read-only access

Endpoints:
  GET    /api/workspaces                          list user's workspaces
  POST   /api/workspaces                          create workspace
  GET    /api/workspaces/{id}                     get workspace + members
  PUT    /api/workspaces/{id}                     rename workspace
  DELETE /api/workspaces/{id}                     delete workspace (owner only)
  GET    /api/workspaces/{id}/members             list members
  POST   /api/workspaces/{id}/members             invite member by email
  PUT    /api/workspaces/{id}/members/{user_id}   update member role
  DELETE /api/workspaces/{id}/members/{user_id}   remove member
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, UserRole, Workspace, WorkspaceMember
from api.dependencies import get_current_user
from services.enterprise_rollup_service import refresh_workspace_rollups

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceUpdate(BaseModel):
    name: str


class MemberInvite(BaseModel):
    email: str
    role: str = "viewer"  # "admin" | "editor" | "viewer"


class MemberRoleUpdate(BaseModel):
    role: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_member(m: WorkspaceMember) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "email": m.user.email if m.user else None,
        "full_name": m.user.full_name if m.user else None,
        "role": m.role.value,
        "is_active": m.is_active,
        "invited_at": m.invited_at.isoformat() if m.invited_at else None,
        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
    }


def _fmt_workspace(
    ws: Workspace,
    include_members: bool = False,
    *,
    is_active_workspace: bool = False,
) -> dict:
    d = {
        "id": ws.id,
        "name": ws.name,
        "owner_id": ws.owner_id,
        "is_active": ws.is_active,
        "is_active_workspace": is_active_workspace,
        "created_at": ws.created_at.isoformat(),
        "member_count": len([m for m in ws.members if m.is_active]),
    }
    if include_members:
        d["members"] = [_fmt_member(m) for m in ws.members if m.is_active]
    return d


def _get_workspace_or_404(ws_id: int, user_id: int, db: Session) -> Workspace:
    """Return workspace if user is owner or active member, else raise 404."""
    ws = db.query(Workspace).filter(Workspace.id == ws_id, Workspace.is_active == True).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    is_owner = ws.owner_id == user_id
    is_member = any(m.user_id == user_id and m.is_active for m in ws.members)
    if not is_owner and not is_member:
        raise HTTPException(status_code=403, detail="Access denied")
    return ws


def _parse_role(role_str: str) -> UserRole:
    try:
        return UserRole(role_str.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid role '{role_str}'. Use admin, editor, or viewer")


# ── Workspace CRUD ────────────────────────────────────────────────────────────

@router.get("")
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workspaces where the user is owner or active member."""
    owned = db.query(Workspace).filter(
        Workspace.owner_id == current_user.id,
        Workspace.is_active == True,
    ).all()

    member_ws_ids = [
        m.workspace_id for m in current_user.workspace_memberships
        if m.is_active
    ]
    member_wss = db.query(Workspace).filter(
        Workspace.id.in_(member_ws_ids),
        Workspace.is_active == True,
        Workspace.owner_id != current_user.id,
    ).all()
    active_workspace_id = current_user.default_workspace_id

    return {
        "active_workspace_id": active_workspace_id,
        "owned": [
            _fmt_workspace(ws, is_active_workspace=ws.id == active_workspace_id)
            for ws in owned
        ],
        "member_of": [
            _fmt_workspace(ws, is_active_workspace=ws.id == active_workspace_id)
            for ws in member_wss
        ],
    }


@router.post("", status_code=201)
def create_workspace(
    body: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workspace. The creator becomes owner + admin member."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Workspace name is required")

    ws = Workspace(name=name, owner_id=current_user.id)
    db.add(ws)
    db.flush()  # get ws.id

    # Auto-add owner as admin member
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=current_user.id,
        role=UserRole.ADMIN,
        joined_at=datetime.utcnow(),
    )
    db.add(member)
    if current_user.default_workspace_id is None:
        current_user.default_workspace_id = ws.id
    refresh_workspace_rollups(db, workspace_id=ws.id)
    db.commit()
    db.refresh(ws)
    return _fmt_workspace(
        ws,
        include_members=True,
        is_active_workspace=current_user.default_workspace_id == ws.id,
    )


@router.get("/{ws_id}")
def get_workspace(
    ws_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = _get_workspace_or_404(ws_id, current_user.id, db)
    return _fmt_workspace(
        ws,
        include_members=True,
        is_active_workspace=current_user.default_workspace_id == ws.id,
    )


@router.put("/{ws_id}")
def update_workspace(
    ws_id: int,
    body: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = _get_workspace_or_404(ws_id, current_user.id, db)
    # Only owner or admin member can rename
    is_owner = ws.owner_id == current_user.id
    is_admin = any(
        m.user_id == current_user.id and m.role == UserRole.ADMIN and m.is_active
        for m in ws.members
    )
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can rename the workspace")

    ws.name = body.name.strip()
    ws.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ws)
    return _fmt_workspace(ws, is_active_workspace=current_user.default_workspace_id == ws.id)


@router.delete("/{ws_id}")
def delete_workspace(
    ws_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws or ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete a workspace")

    if current_user.default_workspace_id == ws.id:
        replacement = db.query(Workspace).filter(
            Workspace.owner_id == current_user.id,
            Workspace.is_active == True,
            Workspace.id != ws.id,
        ).order_by(Workspace.id.asc()).first()
        if replacement is None:
            membership = db.query(WorkspaceMember).join(
                Workspace,
                WorkspaceMember.workspace_id == Workspace.id,
            ).filter(
                WorkspaceMember.user_id == current_user.id,
                WorkspaceMember.is_active == True,
                Workspace.is_active == True,
                Workspace.id != ws.id,
            ).order_by(WorkspaceMember.workspace_id.asc()).first()
            replacement = membership.workspace if membership else None

        current_user.default_workspace_id = replacement.id if replacement else None

    db.delete(ws)
    db.commit()
    return {"success": True, "message": "Workspace deleted"}


@router.post("/{ws_id}/select")
def select_workspace(
    ws_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Set the active workspace for future requests.
    """
    ws = _get_workspace_or_404(ws_id, current_user.id, db)
    current_user.default_workspace_id = ws.id
    db.commit()
    db.refresh(current_user)
    return {
        "success": True,
        "active_workspace_id": ws.id,
        "workspace": _fmt_workspace(ws, is_active_workspace=True),
    }


# ── Member management ─────────────────────────────────────────────────────────

@router.get("/{ws_id}/members")
def list_members(
    ws_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = _get_workspace_or_404(ws_id, current_user.id, db)
    return [_fmt_member(m) for m in ws.members if m.is_active]


@router.post("/{ws_id}/members", status_code=201)
def invite_member(
    ws_id: int,
    body: MemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a user by email. They must already have a MarketIntel account."""
    ws = _get_workspace_or_404(ws_id, current_user.id, db)

    # Only owner or admin can invite
    is_owner = ws.owner_id == current_user.id
    is_admin = any(
        m.user_id == current_user.id and m.role == UserRole.ADMIN and m.is_active
        for m in ws.members
    )
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can invite members")

    # Find target user
    target = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if not target:
        raise HTTPException(status_code=404, detail="No account found with that email address")

    # Already a member?
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.user_id == target.id,
    ).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="User is already a member")
        # Re-activate
        existing.is_active = True
        existing.role = _parse_role(body.role)
        existing.joined_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return _fmt_member(existing)

    role = _parse_role(body.role)
    member = WorkspaceMember(
        workspace_id=ws_id,
        user_id=target.id,
        role=role,
        joined_at=datetime.utcnow(),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _fmt_member(member)


@router.put("/{ws_id}/members/{uid}")
def update_member_role(
    ws_id: int,
    uid: int,
    body: MemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = _get_workspace_or_404(ws_id, current_user.id, db)

    is_owner = ws.owner_id == current_user.id
    is_admin = any(
        m.user_id == current_user.id and m.role == UserRole.ADMIN and m.is_active
        for m in ws.members
    )
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can change roles")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.user_id == uid,
        WorkspaceMember.is_active == True,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.role = _parse_role(body.role)
    db.commit()
    db.refresh(member)
    return _fmt_member(member)


@router.delete("/{ws_id}/members/{uid}")
def remove_member(
    ws_id: int,
    uid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = _get_workspace_or_404(ws_id, current_user.id, db)

    is_owner = ws.owner_id == current_user.id
    is_admin = any(
        m.user_id == current_user.id and m.role == UserRole.ADMIN and m.is_active
        for m in ws.members
    )
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.user_id == uid,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Prevent removing the owner
    if uid == ws.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove the workspace owner")

    member.is_active = False
    db.commit()
    return {"success": True, "message": "Member removed"}
