"""
Enterprise projection helpers for PostgreSQL-backed state and analytics tables.

These helpers are intentionally transition-safe:
- they no-op on SQLite and other non-PostgreSQL environments
- they no-op before the phase-2 tables exist
- they write to the new read-model tables without changing existing API shapes
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from database.models import CompetitorMatch, PriceAlert, ProductMonitored
from services.product_catalog_service import fetch_latest_price_history_rows


def enterprise_rollups_ready(db: Session) -> bool:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return False

    inspector = inspect(bind)
    return (
        inspector.has_schema("state")
        and inspector.has_schema("analytics")
        and inspector.has_table("product_state_current", schema="state")
        and inspector.has_table("competitor_listing_state_current", schema="state")
        and inspector.has_table("seller_state_current", schema="state")
        and inspector.has_table("product_metrics_current", schema="analytics")
        and inspector.has_table("portfolio_metrics_current", schema="analytics")
        and inspector.has_table("seller_metrics_current", schema="analytics")
    )


def _priority_bucket(threat_score: float) -> str:
    if threat_score >= 70:
        return "high"
    if threat_score >= 40:
        return "medium"
    return "low"


def _compute_threat_score(
    *,
    competitor_count: int,
    my_price: float | None,
    lowest_price: float | None,
    amazon_1p_present: bool,
) -> float:
    score = min(competitor_count * 5.0, 25.0)

    if my_price and lowest_price:
        gap_pct = ((my_price - lowest_price) / my_price) * 100
        if gap_pct > 0:
            score += min(gap_pct * 2.0, 45.0)

    if amazon_1p_present:
        score += 15.0

    return round(min(score, 100.0), 2)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _elapsed_seconds_since(timestamp: datetime | None) -> int:
    if timestamp is None:
        return 0

    now = _utc_now()
    normalized = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
    return max(int((now - normalized).total_seconds()), 0)


def refresh_product_rollups(
    db: Session,
    *,
    product_id: int,
    workspace_id: int | None,
) -> bool:
    if workspace_id is None or not enterprise_rollups_ready(db):
        return False

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.workspace_id == workspace_id,
    ).first()

    if not product:
        db.execute(
            text("DELETE FROM analytics.product_metrics_current WHERE product_id = :product_id"),
            {"product_id": product_id},
        )
        db.execute(
            text("DELETE FROM state.product_state_current WHERE product_id = :product_id"),
            {"product_id": product_id},
        )
        return False

    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id,
        CompetitorMatch.workspace_id == workspace_id,
    ).all()

    match_ids = [match.id for match in matches]
    latest_rows = fetch_latest_price_history_rows(db, match_ids)
    now = _utc_now()

    competitor_count = len(matches)
    in_stock_competitor_count = 0
    latest_prices: list[tuple[int, float]] = []
    latest_competitor_change_at = None
    latest_scrape_at = None
    amazon_1p_present = False
    seller_names: set[str] = set()

    for match in matches:
        latest_row = latest_rows.get(match.id)
        latest_price = latest_row.price if latest_row and latest_row.price is not None else match.latest_price
        if latest_price is not None:
            latest_prices.append((match.id, float(latest_price)))

        latest_in_stock = latest_row.in_stock if latest_row and latest_row.in_stock is not None else None
        if latest_in_stock:
            in_stock_competitor_count += 1

        observed_at = latest_row.timestamp if latest_row else match.last_scraped_at or match.created_at
        if observed_at and (latest_competitor_change_at is None or observed_at > latest_competitor_change_at):
            latest_competitor_change_at = observed_at
        if match.last_scraped_at and (latest_scrape_at is None or match.last_scraped_at > latest_scrape_at):
            latest_scrape_at = match.last_scraped_at

        if match.amazon_is_seller:
            amazon_1p_present = True
        if match.seller_name:
            seller_names.add(match.seller_name.strip().lower())

        listing_payload = {
            "competitor_match_id": match.id,
            "workspace_id": workspace_id,
            "product_id": product_id,
            "observed_at": observed_at or now,
            "latest_price": latest_price,
            "shipping_cost": latest_row.shipping_cost if latest_row else None,
            "total_price": latest_row.total_price if latest_row else latest_price,
            "currency": latest_row.currency if latest_row and latest_row.currency else "USD",
            "in_stock": latest_in_stock,
            "stock_status": match.stock_status,
            "seller_name": match.seller_name,
            "amazon_is_seller": match.amazon_is_seller,
            "seller_feedback_count": match.seller_feedback_count,
            "seller_positive_feedback_pct": match.seller_positive_feedback_pct,
            "rating": match.rating,
            "review_count": match.review_count,
            "questions_count": match.questions_count,
            "listing_quality_score": match.listing_quality_score,
            "fulfillment_type": match.fulfillment_type,
            "is_prime": match.is_prime,
            "delivery_fastest_days": match.delivery_fastest_days,
            "delivery_standard_days": match.delivery_standard_days,
            "has_same_day": match.has_same_day,
            "has_free_returns": match.has_free_returns,
            "lowest_new_offer_price": match.lowest_new_offer_price,
            "updated_at": now,
        }

        db.execute(
            text(
                """
                INSERT INTO state.competitor_listing_state_current (
                    competitor_match_id, workspace_id, product_id, observed_at,
                    latest_price, shipping_cost, total_price, currency, in_stock,
                    stock_status, seller_name, amazon_is_seller, seller_feedback_count,
                    seller_positive_feedback_pct, rating, review_count, questions_count,
                    listing_quality_score, fulfillment_type, is_prime,
                    delivery_fastest_days, delivery_standard_days, has_same_day,
                    has_free_returns, lowest_new_offer_price, updated_at
                ) VALUES (
                    :competitor_match_id, :workspace_id, :product_id, :observed_at,
                    :latest_price, :shipping_cost, :total_price, :currency, :in_stock,
                    :stock_status, :seller_name, :amazon_is_seller, :seller_feedback_count,
                    :seller_positive_feedback_pct, :rating, :review_count, :questions_count,
                    :listing_quality_score, :fulfillment_type, :is_prime,
                    :delivery_fastest_days, :delivery_standard_days, :has_same_day,
                    :has_free_returns, :lowest_new_offer_price, :updated_at
                )
                ON CONFLICT (competitor_match_id) DO UPDATE SET
                    workspace_id = EXCLUDED.workspace_id,
                    product_id = EXCLUDED.product_id,
                    observed_at = EXCLUDED.observed_at,
                    latest_price = EXCLUDED.latest_price,
                    shipping_cost = EXCLUDED.shipping_cost,
                    total_price = EXCLUDED.total_price,
                    currency = EXCLUDED.currency,
                    in_stock = EXCLUDED.in_stock,
                    stock_status = EXCLUDED.stock_status,
                    seller_name = EXCLUDED.seller_name,
                    amazon_is_seller = EXCLUDED.amazon_is_seller,
                    seller_feedback_count = EXCLUDED.seller_feedback_count,
                    seller_positive_feedback_pct = EXCLUDED.seller_positive_feedback_pct,
                    rating = EXCLUDED.rating,
                    review_count = EXCLUDED.review_count,
                    questions_count = EXCLUDED.questions_count,
                    listing_quality_score = EXCLUDED.listing_quality_score,
                    fulfillment_type = EXCLUDED.fulfillment_type,
                    is_prime = EXCLUDED.is_prime,
                    delivery_fastest_days = EXCLUDED.delivery_fastest_days,
                    delivery_standard_days = EXCLUDED.delivery_standard_days,
                    has_same_day = EXCLUDED.has_same_day,
                    has_free_returns = EXCLUDED.has_free_returns,
                    lowest_new_offer_price = EXCLUDED.lowest_new_offer_price,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            listing_payload,
        )

    lowest_match_id = None
    highest_match_id = None
    lowest_price = None
    highest_price = None
    avg_price = None

    if latest_prices:
        sorted_prices = sorted(latest_prices, key=lambda item: item[1])
        lowest_match_id, lowest_price = sorted_prices[0]
        highest_match_id, highest_price = sorted_prices[-1]
        avg_price = round(sum(price for _, price in latest_prices) / len(latest_prices), 2)

    active_alert_count = db.query(func.count(PriceAlert.id)).filter(
        PriceAlert.workspace_id == workspace_id,
        PriceAlert.product_id == product_id,
        PriceAlert.enabled == True,
    ).scalar() or 0

    price_gap_vs_mine = None
    price_gap_pct_vs_mine = None
    if product.my_price is not None and lowest_price is not None:
        price_gap_vs_mine = round(product.my_price - lowest_price, 2)
        if product.my_price:
            price_gap_pct_vs_mine = round((price_gap_vs_mine / product.my_price) * 100, 2)

    threat_score = _compute_threat_score(
        competitor_count=competitor_count,
        my_price=product.my_price,
        lowest_price=lowest_price,
        amazon_1p_present=amazon_1p_present,
    )

    state_payload = {
        "product_id": product_id,
        "workspace_id": workspace_id,
        "updated_at": now,
        "competitor_count": competitor_count,
        "in_stock_competitor_count": in_stock_competitor_count,
        "lowest_competitor_price": lowest_price,
        "highest_competitor_price": highest_price,
        "avg_competitor_price": avg_price,
        "cheapest_match_id": lowest_match_id,
        "most_expensive_match_id": highest_match_id,
        "latest_competitor_change_at": latest_competitor_change_at,
        "latest_scrape_at": latest_scrape_at,
        "amazon_1p_present": amazon_1p_present,
    }

    metrics_payload = {
        "product_id": product_id,
        "workspace_id": workspace_id,
        "computed_at": now,
        "competitor_count": competitor_count,
        "in_stock_competitor_count": in_stock_competitor_count,
        "lowest_price": lowest_price,
        "highest_price": highest_price,
        "avg_price": avg_price,
        "price_gap_vs_mine": price_gap_vs_mine,
        "price_gap_pct_vs_mine": price_gap_pct_vs_mine,
        "review_velocity_7d": None,
        "review_velocity_30d": None,
        "rating_drop_30d": None,
        "buy_box_volatility_score": None,
        "seller_diversity_count": len(seller_names),
        "amazon_1p_present": amazon_1p_present,
        "active_alert_count": active_alert_count,
        "threat_score": threat_score,
        "priority_bucket": _priority_bucket(threat_score),
    }

    db.execute(
        text(
            """
            INSERT INTO state.product_state_current (
                product_id, workspace_id, updated_at, competitor_count,
                in_stock_competitor_count, lowest_competitor_price,
                highest_competitor_price, avg_competitor_price,
                cheapest_match_id, most_expensive_match_id,
                latest_competitor_change_at, latest_scrape_at, amazon_1p_present
            ) VALUES (
                :product_id, :workspace_id, :updated_at, :competitor_count,
                :in_stock_competitor_count, :lowest_competitor_price,
                :highest_competitor_price, :avg_competitor_price,
                :cheapest_match_id, :most_expensive_match_id,
                :latest_competitor_change_at, :latest_scrape_at, :amazon_1p_present
            )
            ON CONFLICT (product_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                updated_at = EXCLUDED.updated_at,
                competitor_count = EXCLUDED.competitor_count,
                in_stock_competitor_count = EXCLUDED.in_stock_competitor_count,
                lowest_competitor_price = EXCLUDED.lowest_competitor_price,
                highest_competitor_price = EXCLUDED.highest_competitor_price,
                avg_competitor_price = EXCLUDED.avg_competitor_price,
                cheapest_match_id = EXCLUDED.cheapest_match_id,
                most_expensive_match_id = EXCLUDED.most_expensive_match_id,
                latest_competitor_change_at = EXCLUDED.latest_competitor_change_at,
                latest_scrape_at = EXCLUDED.latest_scrape_at,
                amazon_1p_present = EXCLUDED.amazon_1p_present
            """
        ),
        state_payload,
    )

    db.execute(
        text(
            """
            INSERT INTO analytics.product_metrics_current (
                product_id, workspace_id, computed_at, competitor_count,
                in_stock_competitor_count, lowest_price, highest_price, avg_price,
                price_gap_vs_mine, price_gap_pct_vs_mine, review_velocity_7d,
                review_velocity_30d, rating_drop_30d, buy_box_volatility_score,
                seller_diversity_count, amazon_1p_present, active_alert_count,
                threat_score, priority_bucket
            ) VALUES (
                :product_id, :workspace_id, :computed_at, :competitor_count,
                :in_stock_competitor_count, :lowest_price, :highest_price, :avg_price,
                :price_gap_vs_mine, :price_gap_pct_vs_mine, :review_velocity_7d,
                :review_velocity_30d, :rating_drop_30d, :buy_box_volatility_score,
                :seller_diversity_count, :amazon_1p_present, :active_alert_count,
                :threat_score, :priority_bucket
            )
            ON CONFLICT (product_id) DO UPDATE SET
                workspace_id = EXCLUDED.workspace_id,
                computed_at = EXCLUDED.computed_at,
                competitor_count = EXCLUDED.competitor_count,
                in_stock_competitor_count = EXCLUDED.in_stock_competitor_count,
                lowest_price = EXCLUDED.lowest_price,
                highest_price = EXCLUDED.highest_price,
                avg_price = EXCLUDED.avg_price,
                price_gap_vs_mine = EXCLUDED.price_gap_vs_mine,
                price_gap_pct_vs_mine = EXCLUDED.price_gap_pct_vs_mine,
                review_velocity_7d = EXCLUDED.review_velocity_7d,
                review_velocity_30d = EXCLUDED.review_velocity_30d,
                rating_drop_30d = EXCLUDED.rating_drop_30d,
                buy_box_volatility_score = EXCLUDED.buy_box_volatility_score,
                seller_diversity_count = EXCLUDED.seller_diversity_count,
                amazon_1p_present = EXCLUDED.amazon_1p_present,
                active_alert_count = EXCLUDED.active_alert_count,
                threat_score = EXCLUDED.threat_score,
                priority_bucket = EXCLUDED.priority_bucket
            """
        ),
        metrics_payload,
    )

    return True


def refresh_workspace_seller_rollups(db: Session, *, workspace_id: int | None) -> bool:
    if workspace_id is None or not enterprise_rollups_ready(db):
        return False

    rows = db.execute(
        text(
            """
            WITH listings AS (
                SELECT
                    workspace_id,
                    lower(trim(seller_name)) AS seller_name_normalized,
                    max(seller_name) AS seller_name,
                    count(*) AS active_listing_count,
                    count(DISTINCT product_id) AS product_coverage_count,
                    bool_or(coalesce(amazon_is_seller, false)) AS amazon_is_1p,
                    avg(rating) AS avg_rating,
                    avg(CASE
                        WHEN total_price IS NOT NULL
                         AND total_price > 0
                         AND latest_price IS NOT NULL
                        THEN (latest_price / total_price) * 100
                        ELSE NULL
                    END) AS avg_price_position,
                    avg(CASE
                        WHEN amazon_is_seller THEN 100
                        ELSE 0
                    END) AS buy_box_win_rate_pct
                FROM state.competitor_listing_state_current
                WHERE workspace_id = :workspace_id
                  AND seller_name IS NOT NULL
                  AND trim(seller_name) <> ''
                GROUP BY workspace_id, lower(trim(seller_name))
            )
            SELECT * FROM listings
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().all()

    db.execute(
        text("DELETE FROM analytics.seller_metrics_current WHERE workspace_id = :workspace_id"),
        {"workspace_id": workspace_id},
    )
    db.execute(
        text("DELETE FROM state.seller_state_current WHERE workspace_id = :workspace_id"),
        {"workspace_id": workspace_id},
    )

    now = _utc_now()
    for row in rows:
        state_payload = {
            "workspace_id": workspace_id,
            "seller_name_normalized": row["seller_name_normalized"],
            "seller_name": row["seller_name"],
            "storefront_url": None,
            "amazon_is_1p": bool(row["amazon_is_1p"]),
            "feedback_rating": row["avg_rating"],
            "feedback_count": None,
            "positive_feedback_pct": None,
            "active_listing_count": row["active_listing_count"],
            "product_coverage_count": row["product_coverage_count"],
            "updated_at": now,
        }
        metrics_payload = {
            "workspace_id": workspace_id,
            "seller_name_normalized": row["seller_name_normalized"],
            "seller_name": row["seller_name"],
            "computed_at": now,
            "product_coverage_count": row["product_coverage_count"],
            "active_listing_count": row["active_listing_count"],
            "avg_price_position": round(float(row["avg_price_position"]), 2) if row["avg_price_position"] is not None else None,
            "avg_rating": round(float(row["avg_rating"]), 2) if row["avg_rating"] is not None else None,
            "buy_box_win_rate_pct": round(float(row["buy_box_win_rate_pct"]), 2) if row["buy_box_win_rate_pct"] is not None else None,
            "volatility_score": None,
            "amazon_is_1p": bool(row["amazon_is_1p"]),
        }

        db.execute(
            text(
                """
                INSERT INTO state.seller_state_current (
                    workspace_id, seller_name_normalized, seller_name, storefront_url,
                    amazon_is_1p, feedback_rating, feedback_count, positive_feedback_pct,
                    active_listing_count, product_coverage_count, updated_at
                ) VALUES (
                    :workspace_id, :seller_name_normalized, :seller_name, :storefront_url,
                    :amazon_is_1p, :feedback_rating, :feedback_count, :positive_feedback_pct,
                    :active_listing_count, :product_coverage_count, :updated_at
                )
                """
            ),
            state_payload,
        )

        db.execute(
            text(
                """
                INSERT INTO analytics.seller_metrics_current (
                    workspace_id, seller_name_normalized, seller_name, computed_at,
                    product_coverage_count, active_listing_count, avg_price_position,
                    avg_rating, buy_box_win_rate_pct, volatility_score, amazon_is_1p
                ) VALUES (
                    :workspace_id, :seller_name_normalized, :seller_name, :computed_at,
                    :product_coverage_count, :active_listing_count, :avg_price_position,
                    :avg_rating, :buy_box_win_rate_pct, :volatility_score, :amazon_is_1p
                )
                """
            ),
            metrics_payload,
        )

    return True


def refresh_workspace_rollups(db: Session, *, workspace_id: int | None) -> bool:
    if workspace_id is None or not enterprise_rollups_ready(db):
        return False

    row = db.execute(
        text(
            """
            SELECT
                count(*) AS total_products,
                coalesce(sum(competitor_count), 0) AS total_active_listings,
                coalesce(sum(active_alert_count), 0) AS total_active_alerts,
                count(*) FILTER (WHERE threat_score >= 60) AS products_with_threats,
                count(*) FILTER (WHERE coalesce(review_velocity_7d, 0) >= 10) AS products_with_surging_reviews,
                count(*) FILTER (WHERE coalesce(price_gap_vs_mine, 0) < 0) AS products_with_price_drops,
                avg(competitor_count::numeric) AS average_competitor_count,
                avg(price_gap_pct_vs_mine::numeric) AS average_price_gap_pct,
                max(computed_at) AS latest_computed_at
            FROM analytics.product_metrics_current
            WHERE workspace_id = :workspace_id
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().first()

    freshness_seconds = _elapsed_seconds_since(row["latest_computed_at"])

    db.execute(
        text(
            """
            INSERT INTO analytics.portfolio_metrics_current (
                workspace_id, computed_at, total_products, total_active_listings,
                total_active_alerts, products_with_threats,
                products_with_surging_reviews, products_with_price_drops,
                average_competitor_count, average_price_gap_pct, data_freshness_seconds
            ) VALUES (
                :workspace_id, :computed_at, :total_products, :total_active_listings,
                :total_active_alerts, :products_with_threats,
                :products_with_surging_reviews, :products_with_price_drops,
                :average_competitor_count, :average_price_gap_pct, :data_freshness_seconds
            )
            ON CONFLICT (workspace_id) DO UPDATE SET
                computed_at = EXCLUDED.computed_at,
                total_products = EXCLUDED.total_products,
                total_active_listings = EXCLUDED.total_active_listings,
                total_active_alerts = EXCLUDED.total_active_alerts,
                products_with_threats = EXCLUDED.products_with_threats,
                products_with_surging_reviews = EXCLUDED.products_with_surging_reviews,
                products_with_price_drops = EXCLUDED.products_with_price_drops,
                average_competitor_count = EXCLUDED.average_competitor_count,
                average_price_gap_pct = EXCLUDED.average_price_gap_pct,
                data_freshness_seconds = EXCLUDED.data_freshness_seconds
            """
        ),
        {
            "workspace_id": workspace_id,
            "computed_at": _utc_now(),
            "total_products": row["total_products"] or 0,
            "total_active_listings": row["total_active_listings"] or 0,
            "total_active_alerts": row["total_active_alerts"] or 0,
            "products_with_threats": row["products_with_threats"] or 0,
            "products_with_surging_reviews": row["products_with_surging_reviews"] or 0,
            "products_with_price_drops": row["products_with_price_drops"] or 0,
            "average_competitor_count": round(float(row["average_competitor_count"]), 2) if row["average_competitor_count"] is not None else None,
            "average_price_gap_pct": round(float(row["average_price_gap_pct"]), 2) if row["average_price_gap_pct"] is not None else None,
            "data_freshness_seconds": freshness_seconds,
        },
    )

    return True


def refresh_workspace_product_rollups(db: Session, *, workspace_id: int | None) -> bool:
    if workspace_id is None or not enterprise_rollups_ready(db):
        return False

    product_ids = [
        product_id
        for (product_id,) in db.query(ProductMonitored.id).filter(
            ProductMonitored.workspace_id == workspace_id
        ).all()
    ]
    for product_id in product_ids:
        refresh_product_rollups(db, product_id=product_id, workspace_id=workspace_id)
    refresh_workspace_seller_rollups(db, workspace_id=workspace_id)
    refresh_workspace_rollups(db, workspace_id=workspace_id)
    return True
