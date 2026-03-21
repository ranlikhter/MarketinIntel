"""
Benchmark the database optimization work on a copy of the local SQLite database.

If the copied database has no catalog data, the script seeds a representative
benchmark user so the before/after comparisons are still meaningful.
"""

from __future__ import annotations

import shutil
import statistics
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database.models import Base, CompetitorMatch, CompetitorWebsite, PriceHistory, ProductMonitored, User
from services.filter_service import FilterService
from services.forecasting_service import ForecastingService
from services.product_health_service import ProductHealthService
from services.product_catalog_service import get_product_summaries
from services.seller_intel_service import SellerIntelService
from database.models import ReviewSnapshot, SellerProfile


SOURCE_DB = BACKEND_DIR / "marketintel.db"
BENCHMARK_DB = BACKEND_DIR / "benchmark_marketintel_copy.db"
BENCHMARK_EMAIL = "benchmark-user@marketintel.local"


def prepare_database_copy() -> None:
    shutil.copy2(SOURCE_DB, BENCHMARK_DB)


def get_session_factory():
    engine = create_engine(f"sqlite:///{BENCHMARK_DB.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_benchmark_data(SessionLocal) -> int:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == BENCHMARK_EMAIL).first()
        if user:
            return user.id

        user = User(
            email=BENCHMARK_EMAIL,
            hashed_password="benchmark",
            full_name="Benchmark User",
        )
        session.add(user)
        session.flush()

        websites = [
            CompetitorWebsite(name="Amazon", base_url="https://benchmark-amazon.example"),
            CompetitorWebsite(name="Walmart", base_url="https://benchmark-walmart.example"),
            CompetitorWebsite(name="Target", base_url="https://benchmark-target.example"),
        ]
        session.add_all(websites)
        session.flush()

        sellers = [
            ("Amazon.com", True),
            ("Seller Alpha", False),
            ("Seller Beta", False),
            ("Seller Gamma", False),
            ("Seller Delta", False),
        ]
        existing_sellers = {
            row.seller_name
            for row in session.query(SellerProfile.seller_name).filter(
                SellerProfile.seller_name.in_([seller_name for seller_name, _ in sellers])
            ).all()
        }
        for seller_name, is_amazon in sellers:
            if seller_name in existing_sellers:
                continue
            session.add(
                SellerProfile(
                    seller_name=seller_name,
                    amazon_is_1p=is_amazon,
                    feedback_rating=4.8 if is_amazon else 4.5,
                    feedback_count=1000 if is_amazon else 350,
                    positive_feedback_pct=99.0 if is_amazon else 96.0,
                    storefront_url=f"https://benchmark-stores.example/{seller_name.lower().replace(' ', '-')}",
                    first_seen_at=datetime.utcnow() - timedelta(days=180),
                    last_updated_at=datetime.utcnow() - timedelta(days=1),
                )
            )

        now = datetime.utcnow()
        for product_idx in range(80):
            product = ProductMonitored(
                user_id=user.id,
                title=f"Benchmark Product {product_idx + 1}",
                sku=f"BENCH-{product_idx + 1:04d}",
                brand=f"Brand {product_idx % 8}",
                my_price=100 + (product_idx % 17),
                cost_price=70 + (product_idx % 9),
                created_at=now - timedelta(days=product_idx % 45),
            )
            session.add(product)
            session.flush()

            for match_idx in range(5):
                seller_name, is_amazon = sellers[match_idx % len(sellers)]
                match = CompetitorMatch(
                    monitored_product_id=product.id,
                    competitor_name=f"Competitor {match_idx + 1}",
                    competitor_url=f"https://competitor-{product_idx}-{match_idx}.example/item",
                    competitor_product_title=f"Benchmark Product {product_idx + 1} Variant {match_idx + 1}",
                    competitor_website_id=websites[match_idx % len(websites)].id,
                    latest_price=92 + product_idx % 11 + match_idx,
                    stock_status="In Stock" if match_idx != 0 else "Out of Stock",
                    created_at=now - timedelta(days=(product_idx + match_idx) % 10),
                    last_scraped_at=now - timedelta(hours=(product_idx + match_idx) % 36),
                    match_score=95,
                    seller_name=seller_name,
                    amazon_is_seller=is_amazon,
                    seller_feedback_count=200 + (product_idx % 9) * 15 + match_idx,
                    seller_positive_feedback_pct=98 - (match_idx * 0.7),
                    listing_quality_score=90 - (match_idx * 3),
                    questions_count=5 + match_idx,
                )
                session.add(match)
                session.flush()

                for point_idx in range(12):
                    timestamp = now - timedelta(days=point_idx * 7)
                    price = 120 - point_idx + (product_idx % 7) + match_idx
                    session.add(
                        PriceHistory(
                            match_id=match.id,
                            price=price,
                            in_stock=(match_idx != 0 or point_idx % 3 != 0),
                            shipping_cost=4.99,
                            total_price=price + 4.99,
                            discount_pct=5 + (point_idx % 4),
                            was_price=price + 10,
                            promotion_label="Benchmark sale",
                            seller_name=seller_name,
                            timestamp=timestamp,
                        )
                    )

                base_reviews = 100 + (product_idx % 11) * 10 + match_idx
                session.add_all(
                    [
                        ReviewSnapshot(
                            match_id=match.id,
                            review_count=base_reviews,
                            rating=4.8,
                            rating_distribution={"5": 82, "4": 13, "3": 5},
                            questions_count=match.questions_count,
                            scraped_at=now - timedelta(days=40),
                        ),
                        ReviewSnapshot(
                            match_id=match.id,
                            review_count=base_reviews + (8 if match_idx == 0 else 4),
                            rating=4.7,
                            rating_distribution={"5": 80, "4": 15, "3": 5},
                            questions_count=match.questions_count,
                            scraped_at=now - timedelta(days=8),
                        ),
                        ReviewSnapshot(
                            match_id=match.id,
                            review_count=base_reviews + (35 if match_idx == 0 else 10),
                            rating=4.1 if match_idx == 0 else 4.6,
                            rating_distribution={"5": 73, "4": 19, "3": 8},
                            questions_count=match.questions_count,
                            scraped_at=now - timedelta(days=1),
                        ),
                    ]
                )

        session.commit()
        return user.id
    finally:
        session.close()


@contextmanager
def count_select_queries(session):
    statements = []
    connection = session.connection()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(connection, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", before_cursor_execute)


def naive_product_summaries(session, user_id: int):
    week_ago = datetime.utcnow() - timedelta(days=7)
    products = session.query(ProductMonitored).filter(
        ProductMonitored.user_id == user_id
    ).order_by(ProductMonitored.created_at.desc()).all()

    summaries = []
    for product in products:
        matches = session.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product.id
        ).all()
        latest_prices = []
        week_ago_prices = []
        in_stock_count = 0

        for match in matches:
            latest = session.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(PriceHistory.timestamp.desc()).first()
            old = session.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                PriceHistory.timestamp <= week_ago,
            ).order_by(PriceHistory.timestamp.desc()).first()

            if latest and latest.price is not None:
                latest_prices.append(latest.price)
                if latest.in_stock:
                    in_stock_count += 1
            if old and old.price is not None:
                week_ago_prices.append(old.price)

        summaries.append((product.id, len(matches), in_stock_count, latest_prices[:1], week_ago_prices[:1]))

    return summaries


def naive_filter_apply(session, user):
    week_ago = datetime.utcnow() - timedelta(days=7)
    products = session.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).all()
    matching_ids = []

    for product in products:
        if not product.my_price:
            continue

        competitor_prices = []
        price_dropped = False
        for match in session.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product.id
        ).all():
            latest = session.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(PriceHistory.timestamp.desc()).first()
            recent = session.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                PriceHistory.timestamp >= week_ago,
            ).order_by(PriceHistory.timestamp.asc()).all()

            if latest and latest.in_stock:
                competitor_prices.append(latest.price)
            if len(recent) >= 2 and recent[-1].price < recent[0].price:
                price_dropped = True

        if competitor_prices and product.my_price >= max(competitor_prices) and price_dropped:
            matching_ids.append(product.id)

    return session.query(ProductMonitored).filter(ProductMonitored.id.in_(matching_ids)).all()


def naive_trends_summary(session, user):
    service = ForecastingService(session, user)
    products = session.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).limit(80).all()

    trends = {"increasing": 0, "decreasing": 0, "stable": 0}
    predicted_drops = []
    for product in products:
        analysis = service.get_price_history_analysis(product.id, 30)
        if "trend" in analysis:
            trends[analysis["trend"]["direction"]] += 1
        forecast = service.forecast_price(product.id, 30)
        if "price_change_pct" in forecast and forecast["price_change_pct"] < -5:
            predicted_drops.append(product.id)
    return trends, predicted_drops


def naive_best_time_to_buy(session, user):
    service = ForecastingService(session, user)
    products = session.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).limit(50).all()

    recommendations = defaultdict(int)
    for product in products:
        patterns = service.get_seasonal_patterns(product.id, 12)
        best_day = patterns.get("recommendations", {}).get("best_day_to_buy")
        if best_day:
            recommendations[best_day] += 1
    return recommendations


def naive_amazon_threats(session, user):
    matches = session.query(CompetitorMatch).join(
        ProductMonitored,
        CompetitorMatch.monitored_product_id == ProductMonitored.id,
    ).filter(
        ProductMonitored.user_id == user.id,
        CompetitorMatch.amazon_is_seller.is_(True),
    ).all()

    threats = []
    for match in matches:
        product = session.query(ProductMonitored).filter(
            ProductMonitored.id == match.monitored_product_id
        ).first()
        earliest_entry = session.query(PriceHistory).filter(
            PriceHistory.match_id == match.id
        ).order_by(PriceHistory.timestamp).first()
        threats.append((product.title if product else None, earliest_entry.timestamp if earliest_entry else None))

    return threats


def naive_portfolio_health(session, user):
    now = datetime.utcnow()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    flagged = []

    products = session.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).all()

    for product in products:
        matches = session.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product.id
        ).all()

        flags = []
        for match in matches:
            snapshots = session.query(ReviewSnapshot).filter(
                ReviewSnapshot.match_id == match.id
            ).order_by(ReviewSnapshot.scraped_at).all()

            if not snapshots:
                continue

            latest = snapshots[-1]
            snap_7d = None
            snap_30d = None
            for snapshot in snapshots:
                if snapshot.scraped_at <= cutoff_30d:
                    snap_30d = snapshot
                if snapshot.scraped_at <= cutoff_7d:
                    snap_7d = snapshot
                else:
                    break

            if snap_7d and latest.review_count is not None and snap_7d.review_count is not None:
                if latest.review_count - snap_7d.review_count > 20:
                    flags.append(("surging_reviews", match.competitor_name))

            if snap_30d and latest.rating is not None and snap_30d.rating is not None:
                if float(snap_30d.rating) - float(latest.rating) > 0.2:
                    flags.append(("rating_drop", match.competitor_name))

        if flags:
            flagged.append((product.id, len(flags)))

    return flagged


def benchmark_case(name, SessionLocal, user_id: int, runner):
    durations = []
    query_counts = []

    for _ in range(3):
        session = SessionLocal()
        user = session.get(User, user_id)
        try:
            with count_select_queries(session) as statements:
                start = perf_counter()
                runner(session, user)
                durations.append(perf_counter() - start)
            query_counts.append(len(statements))
        finally:
            session.close()

    return {
        "name": name,
        "avg_ms": round(statistics.mean(durations) * 1000, 2),
        "queries": round(statistics.mean(query_counts), 1),
    }


def main() -> None:
    if not SOURCE_DB.exists():
        raise SystemExit(f"Source database not found: {SOURCE_DB}")

    prepare_database_copy()
    SessionLocal = get_session_factory()
    user_id = ensure_benchmark_data(SessionLocal)

    cases = [
        (
            "product_summaries_baseline",
            lambda session, user: naive_product_summaries(session, user.id),
        ),
        (
            "product_summaries_optimized",
            lambda session, user: get_product_summaries(session, user_id=user.id, limit=200, offset=0),
        ),
        (
            "filter_apply_baseline",
            lambda session, user: naive_filter_apply(session, user),
        ),
        (
            "filter_apply_optimized",
            lambda session, user: FilterService(session, user).apply_filters(
                {"price_position": "most_expensive", "activity": "price_dropped"}
            ).all(),
        ),
        (
            "trends_summary_baseline",
            lambda session, user: naive_trends_summary(session, user),
        ),
        (
            "trends_summary_optimized",
            lambda session, user: ForecastingService(session, user).get_trends_summary(limit=80),
        ),
        (
            "best_time_to_buy_baseline",
            lambda session, user: naive_best_time_to_buy(session, user),
        ),
        (
            "best_time_to_buy_optimized",
            lambda session, user: ForecastingService(session, user).get_best_time_to_buy_insights(limit=50, months=12),
        ),
        (
            "amazon_threats_baseline",
            lambda session, user: naive_amazon_threats(session, user),
        ),
        (
            "amazon_threats_optimized",
            lambda session, user: SellerIntelService(session, user).get_amazon_1p_threats(),
        ),
        (
            "portfolio_health_baseline",
            lambda session, user: naive_portfolio_health(session, user),
        ),
        (
            "portfolio_health_optimized",
            lambda session, user: ProductHealthService(session, user).get_portfolio_health(),
        ),
    ]

    print(f"Benchmark DB copy: {BENCHMARK_DB}")
    print("Rows for benchmark user:")
    session = SessionLocal()
    try:
        product_count = session.query(ProductMonitored).filter(ProductMonitored.user_id == user_id).count()
        match_count = session.query(CompetitorMatch).join(
            ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id
        ).filter(ProductMonitored.user_id == user_id).count()
        history_count = session.query(PriceHistory).join(
            CompetitorMatch, PriceHistory.match_id == CompetitorMatch.id
        ).join(
            ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id
        ).filter(ProductMonitored.user_id == user_id).count()
        review_count = session.query(ReviewSnapshot).join(
            CompetitorMatch, ReviewSnapshot.match_id == CompetitorMatch.id
        ).join(
            ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id
        ).filter(ProductMonitored.user_id == user_id).count()
        print(f"  products_monitored: {product_count}")
        print(f"  competitor_matches: {match_count}")
        print(f"  price_history: {history_count}")
        print(f"  review_snapshots: {review_count}")
    finally:
        session.close()

    print("\nResults (average of 3 runs):")
    for name, runner in cases:
        result = benchmark_case(name, SessionLocal, user_id, runner)
        print(f"  {result['name']}: {result['avg_ms']} ms, {result['queries']} SELECTs")


if __name__ == "__main__":
    main()
