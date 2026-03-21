"""
Regression tests for the workspace-scoped enterprise cutover behavior.
"""

from datetime import datetime

from database.models import ProductMonitored, User, UserRole, Workspace, WorkspaceMember
from tests.conftest import auth_headers, register_and_login


def _seed_workspace(db, *, user: User, name: str) -> Workspace:
    workspace = Workspace(name=name, owner_id=user.id, created_at=datetime.utcnow())
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=UserRole.ADMIN,
            joined_at=datetime.utcnow(),
        )
    )
    db.flush()
    return workspace


class TestWorkspaceScope:
    def test_products_list_uses_active_workspace_scope(self, client, db):
        token = register_and_login(client, email="workspace-scope@example.com")
        user = db.query(User).filter(User.email == "workspace-scope@example.com").first()
        assert user is not None

        primary = _seed_workspace(db, user=user, name="Primary Workspace")
        secondary = _seed_workspace(db, user=user, name="Secondary Workspace")
        user.default_workspace_id = primary.id
        db.flush()

        db.add_all(
            [
                ProductMonitored(
                    user_id=user.id,
                    workspace_id=primary.id,
                    title="Primary Product",
                    sku="PRIMARY-1",
                ),
                ProductMonitored(
                    user_id=user.id,
                    workspace_id=secondary.id,
                    title="Secondary Product",
                    sku="SECONDARY-1",
                ),
            ]
        )
        db.commit()

        default_resp = client.get("/api/products", headers=auth_headers(token))
        assert default_resp.status_code == 200, default_resp.text
        default_titles = [item["title"] for item in default_resp.json()]
        assert default_titles == ["Primary Product"]

        secondary_resp = client.get(
            "/api/products",
            headers={
                **auth_headers(token),
                "X-Workspace-ID": str(secondary.id),
            },
        )
        assert secondary_resp.status_code == 200, secondary_resp.text
        secondary_titles = [item["title"] for item in secondary_resp.json()]
        assert secondary_titles == ["Secondary Product"]

    def test_select_workspace_updates_active_workspace_payload(self, client, db):
        token = register_and_login(client, email="workspace-select@example.com")
        user = db.query(User).filter(User.email == "workspace-select@example.com").first()
        assert user is not None

        first = _seed_workspace(db, user=user, name="First Workspace")
        second = _seed_workspace(db, user=user, name="Second Workspace")
        user.default_workspace_id = first.id
        db.commit()
        db.refresh(user)

        list_resp = client.get("/api/workspaces", headers=auth_headers(token))
        assert list_resp.status_code == 200, list_resp.text
        assert list_resp.json()["active_workspace_id"] == first.id

        select_resp = client.post(f"/api/workspaces/{second.id}/select", headers=auth_headers(token))
        assert select_resp.status_code == 200, select_resp.text
        assert select_resp.json()["active_workspace_id"] == second.id
        assert select_resp.json()["workspace"]["is_active_workspace"] is True

        me_resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert me_resp.status_code == 200, me_resp.text
        assert me_resp.json()["active_workspace_id"] == second.id

        refreshed_list = client.get("/api/workspaces", headers=auth_headers(token))
        assert refreshed_list.status_code == 200, refreshed_list.text
        payload = refreshed_list.json()
        assert payload["active_workspace_id"] == second.id
        owned_flags = {workspace["id"]: workspace["is_active_workspace"] for workspace in payload["owned"]}
        assert owned_flags[first.id] is False
        assert owned_flags[second.id] is True
