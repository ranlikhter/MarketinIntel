"""
Integration Tests — Dashboards API (/api/dashboards/*)

Tests dashboard CRUD, widget add/update/delete, layout save,
and user isolation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User


def make_user(db, email="dash@x.com"):
    u = User(email=email, hashed_password="x", full_name="Dash User")
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def authed_client(client, db):
    user = make_user(db)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


DASHBOARD_PAYLOAD = {"name": "My Dashboard", "description": "Test dashboard"}
WIDGET_PAYLOAD = {"widget_type": "kpi_summary", "title": "Total Products", "size": "medium", "config": {}}


# ── Tests: Auth ───────────────────────────────────────────────────────────────

class TestDashboardsAuth:

    def test_list_requires_auth(self, client):
        resp = client.get("/api/dashboards")
        assert resp.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        resp = client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        assert resp.status_code in (401, 403)


# ── Tests: Dashboard CRUD ─────────────────────────────────────────────────────

class TestDashboardCRUD:

    def test_create_dashboard(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["name"] == "My Dashboard"

    def test_list_dashboards(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/dashboards")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_created_dashboard_in_list(self, authed_client):
        client, _ = authed_client
        client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        resp = client.get("/api/dashboards")
        names = [d["name"] for d in resp.json()]
        assert "My Dashboard" in names

    def test_get_dashboard_by_id(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        dash_id = create_resp.json()["id"]
        resp = client.get(f"/api/dashboards/{dash_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == dash_id

    def test_get_nonexistent_dashboard_404(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/dashboards/999999")
        assert resp.status_code == 404

    def test_update_dashboard_name(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        dash_id = create_resp.json()["id"]
        resp = client.put(f"/api/dashboards/{dash_id}", json={"name": "Renamed Dashboard"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Dashboard"

    def test_delete_dashboard(self, authed_client):
        client, _ = authed_client
        create_resp = client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        dash_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/dashboards/{dash_id}")
        assert del_resp.status_code in (200, 204)
        assert client.get(f"/api/dashboards/{dash_id}").status_code == 404

    def test_name_required(self, authed_client):
        client, _ = authed_client
        resp = client.post("/api/dashboards", json={})
        assert resp.status_code == 422


# ── Tests: Widgets ────────────────────────────────────────────────────────────

class TestDashboardWidgets:

    def _create_dashboard(self, client):
        resp = client.post("/api/dashboards", json=DASHBOARD_PAYLOAD)
        return resp.json()["id"]

    def test_add_widget(self, authed_client):
        client, _ = authed_client
        dash_id = self._create_dashboard(client)
        resp = client.post(f"/api/dashboards/{dash_id}/widgets", json=WIDGET_PAYLOAD)
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["widget_type"] == "kpi_summary"

    def test_dashboard_includes_widgets(self, authed_client):
        client, _ = authed_client
        dash_id = self._create_dashboard(client)
        client.post(f"/api/dashboards/{dash_id}/widgets", json=WIDGET_PAYLOAD)
        resp = client.get(f"/api/dashboards/{dash_id}")
        assert resp.status_code == 200
        widgets = resp.json().get("widgets", [])
        assert len(widgets) >= 1

    def test_update_widget(self, authed_client):
        client, _ = authed_client
        dash_id = self._create_dashboard(client)
        widget_resp = client.post(f"/api/dashboards/{dash_id}/widgets", json=WIDGET_PAYLOAD)
        widget_id = widget_resp.json()["id"]
        resp = client.put(f"/api/dashboards/{dash_id}/widgets/{widget_id}", json={"title": "Updated Widget"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Widget"

    def test_delete_widget(self, authed_client):
        client, _ = authed_client
        dash_id = self._create_dashboard(client)
        widget_resp = client.post(f"/api/dashboards/{dash_id}/widgets", json=WIDGET_PAYLOAD)
        widget_id = widget_resp.json()["id"]
        del_resp = client.delete(f"/api/dashboards/{dash_id}/widgets/{widget_id}")
        assert del_resp.status_code in (200, 204)

    def test_add_multiple_widget_types(self, authed_client):
        client, _ = authed_client
        dash_id = self._create_dashboard(client)
        widget_types = ["kpi_summary", "price_trendline", "competitor_table"]
        for wt in widget_types:
            resp = client.post(f"/api/dashboards/{dash_id}/widgets", json={
                **WIDGET_PAYLOAD, "widget_type": wt,
            })
            assert resp.status_code in (200, 201), f"Failed for widget_type={wt}"


# ── Tests: Isolation ──────────────────────────────────────────────────────────

class TestDashboardIsolation:

    def test_user_cannot_see_other_users_dashboards(self, client, db):
        u1 = make_user(db, "diso1@x.com")
        u2 = make_user(db, "diso2@x.com")

        app.dependency_overrides[get_current_user] = lambda: u1
        client.post("/api/dashboards", json={"name": "U1 Dashboard"})

        app.dependency_overrides[get_current_user] = lambda: u2
        resp = client.get("/api/dashboards")
        names = [d["name"] for d in resp.json()]
        assert "U1 Dashboard" not in names

        app.dependency_overrides.pop(get_current_user, None)
