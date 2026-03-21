from datetime import datetime, timedelta

from api.dependencies import get_current_user
from api.main import app
from database.models import (
    CompetitorMatch,
    PriceHistory,
    ProductMonitored,
    ReviewSnapshot,
    SellerProfile,
    User,
)
from services.product_health_service import ProductHealthService
from services.seller_intel_service import SellerIntelService
from tests.test_database_optimizations import count_select_queries, seed_catalog


def seed_seller_and_health_data(db, *, user: User, product_count: int = 3, matches_per_product: int = 3):
    seed_catalog(db, user=user, product_count=product_count, matches_per_product=matches_per_product)

    now = datetime.utcnow()
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).order_by(ProductMonitored.id).all()
    matches = db.query(CompetitorMatch).join(
        ProductMonitored,
        CompetitorMatch.monitored_product_id == ProductMonitored.id,
    ).filter(
        ProductMonitored.user_id == user.id
    ).order_by(CompetitorMatch.monitored_product_id, CompetitorMatch.id).all()

    sellers = [
        ("Amazon.com", True),
        ("Seller Alpha", False),
        ("Seller Beta", False),
        ("Seller Gamma", False),
    ]
    created_profiles = set()

    matches_by_product = {}
    for match in matches:
        matches_by_product.setdefault(match.monitored_product_id, []).append(match)

    for product_idx, product in enumerate(products):
        for match_idx, match in enumerate(matches_by_product.get(product.id, [])):
            seller_name, is_amazon = sellers[match_idx % len(sellers)]
            match.seller_name = seller_name
            match.amazon_is_seller = is_amazon
            match.seller_feedback_count = 100 + (product_idx * 25) + (match_idx * 5)
            match.seller_positive_feedback_pct = 98.0 - match_idx
            match.listing_quality_score = 88 - (match_idx * 4)
            match.questions_count = 6 + match_idx

            existing_profile = db.query(SellerProfile.id).filter(
                SellerProfile.seller_name == seller_name
            ).first()
            if seller_name not in created_profiles and existing_profile is None:
                db.add(
                    SellerProfile(
                        seller_name=seller_name,
                        amazon_is_1p=is_amazon,
                        feedback_rating=4.8 if is_amazon else 4.4,
                        feedback_count=500 + (match_idx * 20),
                        positive_feedback_pct=99.0 if is_amazon else 96.5,
                        storefront_url=f"https://stores.example/{seller_name.lower().replace(' ', '-')}",
                        first_seen_at=now - timedelta(days=90),
                        last_updated_at=now - timedelta(days=1),
                    )
                )
                created_profiles.add(seller_name)

            existing_history = db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(PriceHistory.timestamp, PriceHistory.id).all()
            for history in existing_history:
                history.seller_name = seller_name

            base_reviews = 100 + (product_idx * 20) + (match_idx * 10)
            latest_reviews = base_reviews + (32 if match_idx == 0 else 8)
            latest_rating = 4.1 if match_idx == 0 else 4.6

            db.add_all(
                [
                    ReviewSnapshot(
                        match_id=match.id,
                        review_count=base_reviews,
                        rating=4.8,
                        rating_distribution={"5": 80, "4": 15, "3": 5},
                        questions_count=match.questions_count,
                        scraped_at=now - timedelta(days=40),
                    ),
                    ReviewSnapshot(
                        match_id=match.id,
                        review_count=base_reviews + (5 if match_idx else 7),
                        rating=4.7,
                        rating_distribution={"5": 78, "4": 17, "3": 5},
                        questions_count=match.questions_count,
                        scraped_at=now - timedelta(days=8),
                    ),
                    ReviewSnapshot(
                        match_id=match.id,
                        review_count=latest_reviews,
                        rating=latest_rating,
                        rating_distribution={"5": 72, "4": 20, "3": 8},
                        questions_count=match.questions_count,
                        scraped_at=now - timedelta(days=1),
                    ),
                ]
            )

    db.commit()


class TestSellerAndProductHealthOptimizations:
    def test_seller_overview_stays_within_small_query_budget(self, db):
        user = User(email="seller-overview@example.com", hashed_password="x", full_name="Seller Overview")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_seller_and_health_data(db, user=user, product_count=4, matches_per_product=3)
        db.refresh(user)

        service = SellerIntelService(db, user)

        with count_select_queries(db) as statements:
            overview = service.get_seller_overview()

        assert len(overview) == 3
        assert overview[0]["product_count"] >= overview[-1]["product_count"]
        assert len(statements) <= 3

    def test_amazon_threats_batch_product_and_first_seen_loading(self, db):
        user = User(email="seller-threats@example.com", hashed_password="x", full_name="Seller Threats")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_seller_and_health_data(db, user=user, product_count=3, matches_per_product=3)
        db.refresh(user)

        service = SellerIntelService(db, user)

        with count_select_queries(db) as statements:
            threats = service.get_amazon_1p_threats()

        assert len(threats) == 3
        assert all(threat["product_title"] for threat in threats)
        assert all(threat["since"] for threat in threats)
        assert len(statements) <= 3

    def test_seller_profile_joins_product_titles_in_one_pass(self, db):
        user = User(email="seller-profile@example.com", hashed_password="x", full_name="Seller Profile")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_seller_and_health_data(db, user=user, product_count=3, matches_per_product=3)
        db.refresh(user)

        service = SellerIntelService(db, user)

        with count_select_queries(db) as statements:
            profile = service.get_seller_profile("Seller Alpha")

        assert profile["seller_name"] == "Seller Alpha"
        assert profile["total_competing_products"] == 3
        assert all(item["product_title"] for item in profile["competing_products"])
        assert len(statements) <= 3

    def test_buybox_volatility_batches_history_loading(self, db):
        user = User(email="buybox-volatility@example.com", hashed_password="x", full_name="Buy Box")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_seller_and_health_data(db, user=user, product_count=2, matches_per_product=3)
        db.refresh(user)

        product_id = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == user.id
        ).order_by(ProductMonitored.id).first().id
        service = SellerIntelService(db, user)

        with count_select_queries(db) as statements:
            result = service.get_buybox_volatility(product_id)

        assert result["product_id"] == product_id
        assert result["total_observations"] > 0
        assert result["unique_seller_count"] >= 2
        assert len(result["timeline"]) == result["total_observations"]
        assert len(statements) <= 4

    def test_product_health_summary_uses_bulk_review_snapshot_loading(self, db):
        user = User(email="product-health-summary@example.com", hashed_password="x", full_name="Product Health")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_seller_and_health_data(db, user=user, product_count=2, matches_per_product=3)
        db.refresh(user)

        product_id = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == user.id
        ).order_by(ProductMonitored.id).first().id
        service = ProductHealthService(db, user)

        with count_select_queries(db) as statements:
            summary = service.get_product_health_summary(product_id)

        assert summary["product_id"] == product_id
        assert len(summary["competitors"]) == 3
        assert any(item["review_velocity_7d"] is not None for item in summary["competitors"])
        assert len(statements) <= 4

    def test_portfolio_health_uses_bulk_match_and_snapshot_loading(self, db):
        user = User(email="portfolio-health@example.com", hashed_password="x", full_name="Portfolio Health")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_seller_and_health_data(db, user=user, product_count=4, matches_per_product=3)
        db.refresh(user)

        service = ProductHealthService(db, user)

        with count_select_queries(db) as statements:
            portfolio = service.get_portfolio_health()

        assert portfolio["summary"]["total_products"] == 4
        assert portfolio["summary"]["products_with_flags"] >= 1
        assert len(statements) <= 4

    def test_review_velocity_trend_requires_owned_match(self, client, db):
        user = User(email="velocity-owner@example.com", hashed_password="x", full_name="Velocity Owner")
        other_user = User(email="velocity-other@example.com", hashed_password="x", full_name="Velocity Other")
        db.add_all([user, other_user])
        db.commit()
        db.refresh(user)
        db.refresh(other_user)

        seed_seller_and_health_data(db, user=user, product_count=1, matches_per_product=2)
        seed_seller_and_health_data(db, user=other_user, product_count=1, matches_per_product=2)

        other_match_id = db.query(CompetitorMatch).join(
            ProductMonitored,
            CompetitorMatch.monitored_product_id == ProductMonitored.id,
        ).filter(
            ProductMonitored.user_id == other_user.id
        ).order_by(CompetitorMatch.id).first().id

        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = client.get(f"/api/product-health/velocity/{other_match_id}")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 404
        assert response.json()["detail"] == "Match not found"
