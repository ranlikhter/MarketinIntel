from database.models import ProductMonitored, User
from services.filter_service import FilterService
from services.forecasting_service import ForecastingService
from tests.test_database_optimizations import count_select_queries, seed_catalog


class TestFilterAndForecastingOptimizations:
    def test_filter_service_uses_single_snapshot_for_python_filters(self, db):
        user = User(email="filter-perf@example.com", hashed_password="x", full_name="Filter Perf")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=4, matches_per_product=3)
        db.refresh(user)

        service = FilterService(db, user)

        with count_select_queries(db) as statements:
            results = service.apply_filters(
                {
                    "price_position": "most_expensive",
                    "activity": "price_dropped",
                }
            ).all()

        assert isinstance(results, list)
        assert len(statements) <= 5

    def test_filter_options_stay_within_small_query_budget(self, db):
        user = User(email="filter-options@example.com", hashed_password="x", full_name="Filter Options")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=3, matches_per_product=3)
        db.refresh(user)

        service = FilterService(db, user)

        with count_select_queries(db) as statements:
            options = service.get_filter_options()

        assert options["total_products"] == 3
        assert "recent_activity" in options
        assert len(statements) <= 6

    def test_price_history_analysis_batches_match_history_queries(self, db):
        user = User(email="forecast-analysis@example.com", hashed_password="x", full_name="Forecast Analysis")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=2, matches_per_product=4)
        db.refresh(user)

        product_id = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == user.id
        ).first().id
        service = ForecastingService(db, user)

        with count_select_queries(db) as statements:
            analysis = service.get_price_history_analysis(product_id, 90)

        assert analysis["product"]["id"] == product_id
        assert len(statements) <= 3

    def test_trends_summary_uses_bulk_history_loading(self, db):
        user = User(email="forecast-summary@example.com", hashed_password="x", full_name="Forecast Summary")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=5, matches_per_product=4)
        db.refresh(user)

        service = ForecastingService(db, user)

        with count_select_queries(db) as statements:
            summary = service.get_trends_summary(limit=5)

        assert summary["total_products_analyzed"] == 5
        assert "trend_distribution" in summary
        assert len(statements) <= 3

    def test_best_time_to_buy_summary_uses_bulk_history_loading(self, db):
        user = User(email="forecast-bestbuy@example.com", hashed_password="x", full_name="Forecast Best Buy")
        db.add(user)
        db.commit()
        db.refresh(user)
        seed_catalog(db, user=user, product_count=4, matches_per_product=3)
        db.refresh(user)

        service = ForecastingService(db, user)

        with count_select_queries(db) as statements:
            insights = service.get_best_time_to_buy_insights(limit=4, months=12)

        assert insights["products_analyzed"] == 4
        assert "overall_recommendations" in insights
        assert len(statements) <= 3
