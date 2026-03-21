"""
Workspace helpers for the enterprise cutover.

These helpers let the app scope reads by active workspace while still
supporting legacy user-owned rows during the transition period.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from database.models import User, Workspace, WorkspaceMember
from database.models import UserRole


WORKSPACE_HEADER_NAME = "X-Workspace-ID"


def ensure_personal_workspace(
    db: Session,
    user: User,
) -> tuple[Workspace, WorkspaceMember]:
    """
    Ensure the user has a default personal workspace plus an active admin membership.

    This is required for new accounts after the workspace-scope cutover because
    ``users.default_workspace_id`` becomes mandatory on PostgreSQL.
    """
    workspace = None
    membership = None

    if getattr(user, "default_workspace_id", None):
        workspace, membership = get_accessible_workspace(db, user, user.default_workspace_id)

    if workspace is None:
        workspace = db.query(Workspace).filter(
            Workspace.owner_id == user.id,
            Workspace.is_active == True,
        ).order_by(Workspace.id.asc()).first()

    if workspace is None:
        display_name = (user.full_name or user.email.split("@")[0] or "Personal").strip()
        workspace = Workspace(
            name=f"{display_name} Workspace",
            owner_id=user.id,
        )
        db.add(workspace)
        db.flush()

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id,
    ).first()
    if membership is None:
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(membership)
    else:
        membership.role = UserRole.ADMIN
        membership.is_active = True
        if membership.joined_at is None:
            membership.joined_at = membership.invited_at

    user.default_workspace_id = workspace.id
    from services.enterprise_rollup_service import refresh_workspace_rollups

    refresh_workspace_rollups(db, workspace_id=workspace.id)
    return workspace, membership


def get_accessible_workspace(
    db: Session,
    user: User,
    workspace_id: int,
) -> tuple[Workspace | None, WorkspaceMember | None]:
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.is_active == True,
    ).first()
    if not workspace:
        return None, None

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.is_active == True,
    ).first()

    is_owner = workspace.owner_id == user.id
    if not is_owner and membership is None:
        return None, None

    return workspace, membership


def resolve_active_workspace(
    db: Session,
    user: User,
    requested_workspace_id: int | None = None,
) -> tuple[Workspace | None, WorkspaceMember | None]:
    candidate_ids: list[int] = []
    if requested_workspace_id is not None:
        candidate_ids.append(requested_workspace_id)

    default_workspace_id = getattr(user, "default_workspace_id", None)
    if default_workspace_id is not None and default_workspace_id not in candidate_ids:
        candidate_ids.append(default_workspace_id)

    for workspace_id in candidate_ids:
        workspace, membership = get_accessible_workspace(db, user, workspace_id)
        if workspace is not None:
            return workspace, membership

    owned_workspace = db.query(Workspace).filter(
        Workspace.owner_id == user.id,
        Workspace.is_active == True,
    ).order_by(Workspace.id.asc()).first()
    if owned_workspace is not None:
        membership = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == owned_workspace.id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.is_active == True,
        ).first()
        return owned_workspace, membership

    membership = db.query(WorkspaceMember).join(
        Workspace,
        WorkspaceMember.workspace_id == Workspace.id,
    ).filter(
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.is_active == True,
        Workspace.is_active == True,
    ).order_by(WorkspaceMember.workspace_id.asc()).first()
    if membership is None:
        return None, None

    return membership.workspace, membership


def build_scope_predicate(
    model: type[Any],
    *,
    workspace_id: int | None,
    user_id: int | None,
):
    workspace_column = getattr(model, "workspace_id", None)
    user_column = getattr(model, "user_id", None)

    if workspace_column is not None and workspace_id is not None:
        if user_column is not None and user_id is not None:
            return or_(
                workspace_column == workspace_id,
                and_(workspace_column.is_(None), user_column == user_id),
            )
        return workspace_column == workspace_id

    if user_column is not None and user_id is not None:
        return user_column == user_id

    raise ValueError(
        f"{model.__name__} cannot be workspace-scoped because it exposes neither "
        "workspace_id nor user_id."
    )
