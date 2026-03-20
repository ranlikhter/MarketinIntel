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
from services.product_catalog_service import get_product_summaries


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
                            timestamp=timestamp,
                        )
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
        print(f"  products_monitored: {product_count}")
        print(f"  competitor_matches: {match_count}")
        print(f"  price_history: {history_count}")
    finally:
        session.close()

    print("\nResults (average of 3 runs):")
    for name, runner in cases:
        result = benchmark_case(name, SessionLocal, user_id, runner)
        print(f"  {result['name']}: {result['avg_ms']} ms, {result['queries']} SELECTs")


if __name__ == "__main__":
    main()
