"""
Security-focused tests for AI matching endpoints.
"""

from database.models import ProductMonitored, CompetitorMatch, User
from tests.conftest import register_and_login, auth_headers


class TestAIMatchingSecurity:
    def test_pending_review_requires_auth(self, client):
        resp = client.get("/api/ai-matching/pending-review")
        assert resp.status_code in (401, 403)

    def test_pending_review_is_scoped_to_current_user(self, client, db):
        owner_token = register_and_login(client, email="ai-owner@example.com")
        register_and_login(client, email="ai-other@example.com")

        owner = db.query(User).filter(User.email == "ai-owner@example.com").first()
        other = db.query(User).filter(User.email == "ai-other@example.com").first()
        assert owner is not None
        assert other is not None

        owner_product = ProductMonitored(title="Owner Match Product", user_id=owner.id)
        other_product = ProductMonitored(title="Other Match Product", user_id=other.id)
        db.add_all([owner_product, other_product])
        db.flush()

        db.add_all([
            CompetitorMatch(
                monitored_product_id=owner_product.id,
                competitor_name="Amazon",
                competitor_url="https://example.com/owner",
                competitor_product_title="Owner Competitor Product",
                match_score=80.0,
                latest_price=10.0,
            ),
            CompetitorMatch(
                monitored_product_id=other_product.id,
                competitor_name="Walmart",
                competitor_url="https://example.com/other",
                competitor_product_title="Other Competitor Product",
                match_score=79.0,
                latest_price=11.0,
            ),
        ])
        db.commit()

        resp = client.get(
            "/api/ai-matching/pending-review?min_score=50&max_score=85",
            headers=auth_headers(owner_token),
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["pending_count"] == 1
        assert data["matches"][0]["product_title"] == "Owner Match Product"

    def test_stats_are_scoped_to_current_user(self, client, db):
        owner_token = register_and_login(client, email="ai-stats-owner@example.com")
        register_and_login(client, email="ai-stats-other@example.com")

        owner = db.query(User).filter(User.email == "ai-stats-owner@example.com").first()
        other = db.query(User).filter(User.email == "ai-stats-other@example.com").first()
        assert owner is not None
        assert other is not None

        owner_product = ProductMonitored(title="Owner Stats Product", user_id=owner.id)
        other_product = ProductMonitored(title="Other Stats Product", user_id=other.id)
        db.add_all([owner_product, other_product])
        db.flush()

        db.add_all([
            CompetitorMatch(
                monitored_product_id=owner_product.id,
                competitor_name="Amazon",
                competitor_url="https://example.com/stats-owner",
                competitor_product_title="Owner Stats Competitor",
                match_score=90.0,
                latest_price=20.0,
            ),
            CompetitorMatch(
                monitored_product_id=other_product.id,
                competitor_name="Target",
                competitor_url="https://example.com/stats-other",
                competitor_product_title="Other Stats Competitor",
                match_score=60.0,
                latest_price=21.0,
            ),
        ])
        db.commit()

        resp = client.get("/api/ai-matching/stats", headers=auth_headers(owner_token))
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["total_matches"] == 1
        assert data["distribution"]["high_confidence"] == 1
        assert data["distribution"]["low_confidence"] == 0

    def test_batch_match_rejects_foreign_product(self, client, db):
        owner_token = register_and_login(client, email="ai-batch-owner@example.com")
        register_and_login(client, email="ai-batch-other@example.com")

        other = db.query(User).filter(User.email == "ai-batch-other@example.com").first()
        assert other is not None

        foreign_product = ProductMonitored(title="Foreign Batch Product", user_id=other.id)
        db.add(foreign_product)
        db.commit()

        resp = client.post(
            "/api/ai-matching/batch-match",
            json={"product_id": foreign_product.id, "competitor_products": []},
            headers=auth_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_rematch_rejects_foreign_product(self, client, db):
        owner_token = register_and_login(client, email="ai-rematch-owner@example.com")
        register_and_login(client, email="ai-rematch-other@example.com")

        other = db.query(User).filter(User.email == "ai-rematch-other@example.com").first()
        assert other is not None

        foreign_product = ProductMonitored(title="Foreign Rematch Product", user_id=other.id)
        db.add(foreign_product)
        db.commit()

        resp = client.post(
            f"/api/ai-matching/rematch/{foreign_product.id}",
            headers=auth_headers(owner_token),
        )
        assert resp.status_code == 404

    def test_review_rejects_foreign_match(self, client, db):
        register_and_login(client, email="ai-review-owner@example.com")
        other_token = register_and_login(client, email="ai-review-other@example.com")

        owner = db.query(User).filter(User.email == "ai-review-owner@example.com").first()
        assert owner is not None

        product = ProductMonitored(title="Review Owner Product", user_id=owner.id)
        db.add(product)
        db.flush()

        match = CompetitorMatch(
            monitored_product_id=product.id,
            competitor_name="Amazon",
            competitor_url="https://example.com/review-owner",
            competitor_product_title="Review Owner Competitor",
            match_score=75.0,
            latest_price=15.0,
        )
        db.add(match)
        db.commit()

        resp = client.post(
            "/api/ai-matching/review",
            json={"match_id": match.id, "approved": True},
            headers=auth_headers(other_token),
        )
        assert resp.status_code == 404

    def test_explain_rejects_foreign_match(self, client, db):
        register_and_login(client, email="ai-explain-owner@example.com")
        other_token = register_and_login(client, email="ai-explain-other@example.com")

        owner = db.query(User).filter(User.email == "ai-explain-owner@example.com").first()
        assert owner is not None

        product = ProductMonitored(title="Explain Owner Product", user_id=owner.id)
        db.add(product)
        db.flush()

        match = CompetitorMatch(
            monitored_product_id=product.id,
            competitor_name="Amazon",
            competitor_url="https://example.com/explain-owner",
            competitor_product_title="Explain Owner Competitor",
            match_score=78.0,
            latest_price=16.0,
        )
        db.add(match)
        db.commit()

        resp = client.post(
            f"/api/ai-matching/explain/{match.id}",
            headers=auth_headers(other_token),
        )
        assert resp.status_code == 404
