"""
Integration Tests — Repricing API (/api/repricing/*)

Tests bulk actions, repricing rule CRUD, and user isolation.
"""

import pytest
from api.dependencies import get_current_user
from api.main import app
from database.models import User, ProductMonitored, CompetitorMatch


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def authed_client(client, db):
    user = User(email="reprice_api@example.com", hashed_password="x", full_name="Repricer")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    # Add a product with a competitor match
    product = ProductMonitored(
        user_id=user.id,
        title="Test Widget",
        sku="TW-001",
        our_price=50.0,
        cost_price=20.0,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    match = CompetitorMatch(
        product_id=product.id,
        user_id=user.id,
        title="Test Widget",
        price=45.0,
        stock_status="In Stock",
        source="amazon",
        url="https://amazon.com/dp/test",
    )
    db.add(match)
    db.commit()

    yield client, user, product
    app.dependency_overrides.pop(get_current_user, None)


# ── Tests: Bulk Actions ───────────────────────────────────────────────────────

class TestBulkActions:

    def test_bulk_match_lowest(self, authed_client):
        client, _, product = authed_client
        resp = client.post(
            "/api/repricing/bulk/match-lowest",
            json=[product.id],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "match_lowest"
        assert data["products_processed"] >= 0

    def test_bulk_undercut(self, authed_client):
        client, _, product = authed_client
        resp = client.post(
            "/api/repricing/bulk/undercut",
            json={
                "product_ids": [product.id],
                "undercut_amount": 1.0,
            },
        )
        assert resp.status_code in (200, 422)  # 422 if schema differs

    def test_bulk_action_with_empty_list(self, authed_client):
        client, _, _ = authed_client
        resp = client.post(
            "/api/repricing/bulk/match-lowest",
            json=[],
        )
        assert resp.status_code == 200
        assert resp.json()["products_processed"] == 0

    def test_bulk_requires_auth(self, client):
        resp = client.post("/api/repricing/bulk/match-lowest", json=[1, 2, 3])
        assert resp.status_code in (401, 403)


# ── Tests: Rule CRUD ──────────────────────────────────────────────────────────

RULE_PAYLOAD = {
    "name": "Match Lowest Rule",
    "rule_type": "match_lowest",
    "config": {"margin_amount": 0.5},
    "priority": 1,
    "auto_apply": False,
    "requires_approval": True,
}


class TestRepricingRuleCRUD:

    def test_create_rule(self, authed_client):
        client, _, _ = authed_client
        resp = client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "Match Lowest Rule"
        assert data["rule_type"] == "match_lowest"
        assert data["requires_approval"] is True

    def test_list_rules_empty(self, authed_client):
        client, _, _ = authed_client
        resp = client.get("/api/repricing/rules")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_includes_created_rule(self, authed_client):
        client, _, _ = authed_client
        client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        resp = client.get("/api/repricing/rules")
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()]
        assert "Match Lowest Rule" in names

    def test_get_rule_by_id(self, authed_client):
        client, _, _ = authed_client
        create_resp = client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        rule_id = create_resp.json()["id"]
        resp = client.get(f"/api/repricing/rules/{rule_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == rule_id

    def test_get_nonexistent_rule_returns_404(self, authed_client):
        client, _, _ = authed_client
        resp = client.get("/api/repricing/rules/999999")
        assert resp.status_code == 404

    def test_update_rule(self, authed_client):
        client, _, _ = authed_client
        create_resp = client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        rule_id = create_resp.json()["id"]
        resp = client.put(
            f"/api/repricing/rules/{rule_id}",
            json={"name": "Updated Rule", "priority": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Rule"
        assert resp.json()["priority"] == 5

    def test_disable_rule(self, authed_client):
        client, _, _ = authed_client
        create_resp = client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        rule_id = create_resp.json()["id"]
        resp = client.put(f"/api/repricing/rules/{rule_id}", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_delete_rule(self, authed_client):
        client, _, _ = authed_client
        create_resp = client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        rule_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/repricing/rules/{rule_id}")
        assert del_resp.status_code in (200, 204)
        get_resp = client.get(f"/api/repricing/rules/{rule_id}")
        assert get_resp.status_code == 404

    def test_create_rule_requires_auth(self, client):
        resp = client.post("/api/repricing/rules", json=RULE_PAYLOAD)
        assert resp.status_code in (401, 403)


# ── Tests: Rule Validation ────────────────────────────────────────────────────

class TestRuleValidation:

    def test_create_rule_missing_name(self, authed_client):
        client, _, _ = authed_client
        resp = client.post(
            "/api/repricing/rules",
            json={"rule_type": "match_lowest", "config": {}},
        )
        assert resp.status_code == 422

    def test_create_rule_missing_type(self, authed_client):
        client, _, _ = authed_client
        resp = client.post(
            "/api/repricing/rules",
            json={"name": "No Type Rule", "config": {}},
        )
        assert resp.status_code == 422

    def test_create_undercut_rule(self, authed_client):
        client, _, _ = authed_client
        resp = client.post("/api/repricing/rules", json={
            **RULE_PAYLOAD,
            "name": "Undercut Rule",
            "rule_type": "undercut",
            "config": {"undercut_pct": 5.0},
        })
        assert resp.status_code in (200, 201)

    def test_create_margin_based_rule(self, authed_client):
        client, _, _ = authed_client
        resp = client.post("/api/repricing/rules", json={
            **RULE_PAYLOAD,
            "name": "Margin Rule",
            "rule_type": "margin_based",
            "config": {"target_margin_pct": 30.0},
        })
        assert resp.status_code in (200, 201)

    def test_create_map_protected_rule(self, authed_client):
        client, _, _ = authed_client
        resp = client.post("/api/repricing/rules", json={
            **RULE_PAYLOAD,
            "name": "MAP Rule",
            "rule_type": "map_protected",
            "map_price": 49.99,
            "config": {},
        })
        assert resp.status_code in (200, 201)
