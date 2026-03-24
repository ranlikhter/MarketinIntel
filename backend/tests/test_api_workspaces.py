"""
Integration Tests — Workspaces API (/api/workspaces/*)

Tests workspace CRUD, member management, role-based access,
and isolation between workspace owners and members.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User, Workspace, WorkspaceMember, UserRole


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_user(db, email, name="Test User"):
    user = User(email=email, hashed_password="x", full_name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db, "ws_owner@example.com", "WS Owner")
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestWorkspacesAuth:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/workspaces")
        assert resp.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        resp = client.post("/api/workspaces", json={"name": "New WS"})
        assert resp.status_code in (401, 403)


# ── Tests: CRUD ───────────────────────────────────────────────────────────────

class TestWorkspacesCRUD:

    def test_create_workspace(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/workspaces", json={"name": "My Team"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "My Team"

    def test_list_workspaces(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/workspaces")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_created_workspace_appears_in_list(self, authed_client):
        client, _ = authed_client
        client.post("/api/workspaces", json={"name": "Listed WS"})
        resp = client.get("/api/workspaces")
        names = [ws["name"] for ws in resp.json()]
        assert "Listed WS" in names

    def test_get_workspace_by_id(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/workspaces", json={"name": "Get WS"})
        ws_id = create_resp.json()["id"]
        resp = client.get(f"/api/workspaces/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == ws_id

    def test_get_nonexistent_workspace_returns_404(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/workspaces/999999")
        assert resp.status_code == 404

    def test_update_workspace_name(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/workspaces", json={"name": "Old Name"})
        ws_id = create_resp.json()["id"]
        resp = client.put(f"/api/workspaces/{ws_id}", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_delete_workspace(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/workspaces", json={"name": "To Delete"})
        ws_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/workspaces/{ws_id}")
        assert del_resp.status_code in (200, 204)

    def test_name_required(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/workspaces", json={})
        assert resp.status_code == 422


# ── Tests: Member Management ──────────────────────────────────────────────────

class TestWorkspaceMembers:

    def test_invite_member_by_email(self, client, db):
        owner = make_user(db, "owner_inv@x.com")
        invitee = make_user(db, "invitee@x.com")
        app.dependency_overrides[get_current_user] = lambda: owner

        create_resp = client.post("/api/workspaces", json={"name": "Invite WS"})
        ws_id = create_resp.json()["id"]
        resp = client.post(
            f"/api/workspaces/{ws_id}/members",
            json={"email": "invitee@x.com", "role": "viewer"},
        )
        assert resp.status_code in (200, 201)

        app.dependency_overrides.pop(get_current_user, None)

    def test_list_workspace_members(self, client, db):
        owner = make_user(db, "owner_list@x.com")
        app.dependency_overrides[get_current_user] = lambda: owner

        create_resp = client.post("/api/workspaces", json={"name": "Members WS"})
        ws_id = create_resp.json()["id"]
        resp = client.get(f"/api/workspaces/{ws_id}/members")
        assert resp.status_code == 200
        members = resp.json()
        assert isinstance(members, list)
        # Owner should be in the member list
        emails = [m.get("email") for m in members]
        assert "owner_list@x.com" in emails

        app.dependency_overrides.pop(get_current_user, None)

    def test_update_member_role(self, client, db):
        owner = make_user(db, "owner_role@x.com")
        member = make_user(db, "member_role@x.com")
        app.dependency_overrides[get_current_user] = lambda: owner

        create_resp = client.post("/api/workspaces", json={"name": "Role WS"})
        ws_id = create_resp.json()["id"]
        invite_resp = client.post(
            f"/api/workspaces/{ws_id}/members",
            json={"email": "member_role@x.com", "role": "viewer"},
        )
        assert invite_resp.status_code in (200, 201)

        role_resp = client.put(
            f"/api/workspaces/{ws_id}/members/{member.id}",
            json={"role": "editor"},
        )
        assert role_resp.status_code == 200

        app.dependency_overrides.pop(get_current_user, None)

    def test_remove_member(self, client, db):
        owner = make_user(db, "owner_rm@x.com")
        member = make_user(db, "member_rm@x.com")
        app.dependency_overrides[get_current_user] = lambda: owner

        create_resp = client.post("/api/workspaces", json={"name": "Remove WS"})
        ws_id = create_resp.json()["id"]
        client.post(
            f"/api/workspaces/{ws_id}/members",
            json={"email": "member_rm@x.com", "role": "viewer"},
        )
        del_resp = client.delete(f"/api/workspaces/{ws_id}/members/{member.id}")
        assert del_resp.status_code in (200, 204)

        app.dependency_overrides.pop(get_current_user, None)

    def test_invite_invalid_role_rejected(self, client, db):
        owner = make_user(db, "owner_badrole@x.com")
        make_user(db, "invitee_bad@x.com")
        app.dependency_overrides[get_current_user] = lambda: owner

        create_resp = client.post("/api/workspaces", json={"name": "Bad Role WS"})
        ws_id = create_resp.json()["id"]
        resp = client.post(
            f"/api/workspaces/{ws_id}/members",
            json={"email": "invitee_bad@x.com", "role": "superadmin"},
        )
        assert resp.status_code in (400, 422)

        app.dependency_overrides.pop(get_current_user, None)

    def test_non_owner_cannot_delete_workspace(self, client, db):
        owner = make_user(db, "owner_prot@x.com")
        other = make_user(db, "other_prot@x.com")
        app.dependency_overrides[get_current_user] = lambda: owner

        create_resp = client.post("/api/workspaces", json={"name": "Protected WS"})
        ws_id = create_resp.json()["id"]

        app.dependency_overrides[get_current_user] = lambda: other
        del_resp = client.delete(f"/api/workspaces/{ws_id}")
        assert del_resp.status_code in (403, 404)

        app.dependency_overrides.pop(get_current_user, None)
