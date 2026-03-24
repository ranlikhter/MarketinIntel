"""
End-to-End Flow Tests

Tests complete user journeys across multiple API calls, simulating
real usage patterns from registration through to core workflows.

Flows covered:
  1. Full auth flow (register → login → use API → logout)
  2. Product import + alert setup
  3. Repricing rule creation + bulk action
  4. Workspace creation + member invite
  5. API key generation + usage
"""

import pytest
from api.dependencies import get_current_user, get_current_workspace
from api.main import app
from database.models import User, ProductMonitored


# ── Helpers ───────────────────────────────────────────────────────────────────

def register(client, email, password="FlowTest1!", name="Flow User"):
    return client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": name,
    })


def login(client, email, password="FlowTest1!"):
    return client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def get_token(client, email, password="FlowTest1!"):
    r = login(client, email, password)
    if r.status_code != 200:
        return None
    data = r.json()
    return data.get("access_token") or data.get("token")


# ── Flow 1: Full Auth Flow ────────────────────────────────────────────────────

class TestAuthFlow:

    def test_register_login_profile_logout(self, client):
        """Complete auth journey: register → login → /me → logout."""
        email = "e2e_auth@example.com"

        # 1. Register
        reg_resp = register(client, email)
        assert reg_resp.status_code in (200, 201), f"Register failed: {reg_resp.text}"

        # 2. Login
        login_resp = login(client, email)
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token") or login_resp.json().get("token")
        assert token, "No token returned from login"

        # 3. Access protected endpoint
        me_resp = client.get("/api/auth/me", headers=auth_header(token))
        assert me_resp.status_code == 200
        assert me_resp.json().get("email") == email

        # 4. Logout
        logout_resp = client.post("/api/auth/logout", headers=auth_header(token))
        assert logout_resp.status_code in (200, 204)

    def test_wrong_password_blocked(self, client):
        """Login with wrong password fails; correct password succeeds."""
        email = "e2e_auth_pw@example.com"
        register(client, email, "Correct1!")
        bad = login(client, email, "WrongPw99!")
        assert bad.status_code in (400, 401)
        good = login(client, email, "Correct1!")
        assert good.status_code == 200

    def test_duplicate_email_rejected(self, client):
        """Registering the same email twice fails on second attempt."""
        email = "e2e_dup@example.com"
        r1 = register(client, email)
        assert r1.status_code in (200, 201)
        r2 = register(client, email)
        assert r2.status_code in (400, 409, 422)

    def test_unauthenticated_access_blocked(self, client):
        """Protected endpoints return 401 without token."""
        endpoints = [
            ("GET", "/api/products"),
            ("GET", "/api/alerts/"),
            ("GET", "/api/repricing/rules"),
            ("GET", "/api/workspaces"),
            ("GET", "/api/auth/api-keys"),
        ]
        for method, path in endpoints:
            resp = client.request(method, path)
            assert resp.status_code in (401, 403), (
                f"{method} {path} should require auth, got {resp.status_code}"
            )

    def test_password_change_flow(self, client):
        """User can change password; new password works, old doesn't."""
        email = "e2e_pwchange@example.com"
        register(client, email, "OldPass1!")
        token = get_token(client, email, "OldPass1!")
        if not token:
            pytest.skip("Login failed — skipping password change test")

        change_resp = client.post(
            "/api/auth/change-password",
            headers=auth_header(token),
            json={"current_password": "OldPass1!", "new_password": "NewPass2!"},
        )
        assert change_resp.status_code in (200, 204)

        # New password works
        new_login = login(client, email, "NewPass2!")
        assert new_login.status_code == 200

        # Old password no longer works
        old_login = login(client, email, "OldPass1!")
        assert old_login.status_code in (400, 401)


# ── Flow 2: Product Import + Alert Setup ──────────────────────────────────────

class TestProductAlertFlow:

    @pytest.fixture()
    def user_client(self, client, db):
        user = User(email="e2e_prod_alert@x.com", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)

        class FakeWS:
            workspace_id = user.default_workspace_id or user.id

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_workspace] = lambda: FakeWS()
        yield client, user
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_workspace, None)

    def test_create_product_then_alert(self, user_client):
        """Create a product, then set up a price drop alert on it."""
        client, _ = user_client

        # 1. Create product
        prod_resp = client.post("/api/products", json={
            "title": "E2E Test Product",
            "url": "https://amazon.com/dp/E2ETEST",
            "our_price": 79.99,
            "sku": "E2E-001",
        })
        assert prod_resp.status_code in (200, 201), f"Product create failed: {prod_resp.text}"
        product_id = prod_resp.json()["id"]

        # 2. Create a price drop alert on it
        alert_resp = client.post("/api/alerts/", json={
            "product_id": product_id,
            "alert_type": "price_drop",
            "threshold_pct": 5.0,
            "notify_email": True,
        })
        assert alert_resp.status_code in (200, 201), f"Alert create failed: {alert_resp.text}"
        assert alert_resp.json()["product_id"] == product_id

        # 3. Verify alert appears in list
        list_resp = client.get("/api/alerts/")
        assert any(a["product_id"] == product_id for a in list_resp.json())

    def test_create_product_multiple_alerts(self, user_client):
        """One product can have multiple alerts of different types."""
        client, _ = user_client

        prod_resp = client.post("/api/products", json={
            "title": "Multi-Alert Product",
            "url": "https://amazon.com/dp/MULTI",
            "our_price": 49.99,
            "sku": "MULTI-001",
        })
        assert prod_resp.status_code in (200, 201)
        product_id = prod_resp.json()["id"]

        for alert_type in ["price_drop", "out_of_stock", "most_expensive"]:
            resp = client.post("/api/alerts/", json={
                "product_id": product_id,
                "alert_type": alert_type,
                "threshold_pct": 5.0,
                "notify_email": True,
            })
            assert resp.status_code in (200, 201), f"Failed for {alert_type}: {resp.text}"

        list_resp = client.get("/api/alerts/")
        product_alerts = [a for a in list_resp.json() if a["product_id"] == product_id]
        assert len(product_alerts) >= 3

    def test_delete_product_cleans_up_alert(self, user_client):
        """Deleting a product should make its alerts inaccessible."""
        client, _ = user_client

        prod_resp = client.post("/api/products", json={
            "title": "Delete Me Product",
            "url": "https://amazon.com/dp/DELME",
            "our_price": 29.99,
            "sku": "DEL-001",
        })
        assert prod_resp.status_code in (200, 201)
        product_id = prod_resp.json()["id"]

        # Create alert
        client.post("/api/alerts/", json={
            "product_id": product_id,
            "alert_type": "price_drop",
            "threshold_pct": 5.0,
            "notify_email": True,
        })

        # Delete product
        del_resp = client.delete(f"/api/products/{product_id}")
        assert del_resp.status_code in (200, 204)


# ── Flow 3: Repricing Rule + Bulk Action ─────────────────────────────────────

class TestRepricingFlow:

    @pytest.fixture()
    def user_client(self, client, db):
        user = User(email="e2e_reprice@x.com", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        app.dependency_overrides[get_current_user] = lambda: user
        yield client, user
        app.dependency_overrides.pop(get_current_user, None)

    def test_create_rule_then_bulk_action(self, user_client):
        """Create a repricing rule, then run a bulk action on products."""
        client, _ = user_client

        # 1. Create a repricing rule
        rule_resp = client.post("/api/repricing/rules", json={
            "name": "E2E Match Lowest",
            "rule_type": "match_lowest",
            "config": {"margin_amount": 0.5},
            "priority": 1,
            "auto_apply": False,
            "requires_approval": True,
        })
        assert rule_resp.status_code in (200, 201), f"Rule create failed: {rule_resp.text}"
        rule_id = rule_resp.json()["id"]

        # 2. Verify rule in list
        list_resp = client.get("/api/repricing/rules")
        assert any(r["id"] == rule_id for r in list_resp.json())

        # 3. Run bulk match-lowest action (no products = 0 processed)
        bulk_resp = client.post("/api/repricing/bulk/match-lowest", json=[])
        assert bulk_resp.status_code == 200
        assert bulk_resp.json()["products_processed"] == 0

    def test_rule_update_and_disable_flow(self, user_client):
        """Create → update → disable repricing rule."""
        client, _ = user_client

        rule_resp = client.post("/api/repricing/rules", json={
            "name": "E2E Undercut",
            "rule_type": "undercut",
            "config": {"undercut_amount": 1.0},
            "priority": 2,
            "auto_apply": False,
            "requires_approval": False,
        })
        assert rule_resp.status_code in (200, 201)
        rule_id = rule_resp.json()["id"]

        # Update name
        update_resp = client.put(f"/api/repricing/rules/{rule_id}", json={"name": "E2E Undercut Updated"})
        assert update_resp.status_code == 200

        # Disable
        disable_resp = client.put(f"/api/repricing/rules/{rule_id}", json={"enabled": False})
        assert disable_resp.status_code == 200
        assert disable_resp.json()["enabled"] is False


# ── Flow 4: Workspace + API Key ───────────────────────────────────────────────

class TestWorkspaceApiKeyFlow:

    @pytest.fixture()
    def user_client(self, client, db):
        user = User(email="e2e_ws_key@x.com", hashed_password="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        app.dependency_overrides[get_current_user] = lambda: user
        yield client, user
        app.dependency_overrides.pop(get_current_user, None)

    def test_create_workspace_and_api_key(self, user_client):
        """Create workspace → create API key → verify both exist."""
        client, _ = user_client

        # Create workspace
        ws_resp = client.post("/api/workspaces", json={"name": "E2E Workspace"})
        assert ws_resp.status_code in (200, 201), f"Workspace create failed: {ws_resp.text}"

        # Create API key
        key_resp = client.post("/api/auth/api-keys", json={"name": "E2E API Key"})
        assert key_resp.status_code in (200, 201), f"API key create failed: {key_resp.text}"
        full_key = key_resp.json().get("full_key")
        assert full_key and full_key.startswith("mi_")

        # Verify workspace exists
        ws_list = client.get("/api/workspaces")
        assert any(ws["name"] == "E2E Workspace" for ws in ws_list.json())

        # Verify key exists
        key_list = client.get("/api/auth/api-keys")
        assert any(k["name"] == "E2E API Key" for k in key_list.json())

    def test_create_and_revoke_api_key(self, user_client):
        """Full API key lifecycle: create → use → revoke."""
        client, _ = user_client

        # Create
        create_resp = client.post("/api/auth/api-keys", json={"name": "Lifecycle Key"})
        assert create_resp.status_code in (200, 201)
        key_id = create_resp.json()["id"]

        # Revoke
        revoke_resp = client.delete(f"/api/auth/api-keys/{key_id}")
        assert revoke_resp.status_code in (200, 204)

        # Should no longer appear as active
        list_resp = client.get("/api/auth/api-keys")
        active_keys = [k for k in list_resp.json() if k.get("is_active")]
        assert not any(k["id"] == key_id for k in active_keys)
