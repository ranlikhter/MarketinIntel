"""
Helpers for loading product catalog summaries with a small, fixed query count.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from database.models import CompetitorMatch, CompetitorWebsite, PriceHistory, ProductMonitored


@dataclass(frozen=True)
class PriceSnapshot:
    match_id: int
    price: float | None
    in_stock: bool | None
    timestamp: datetime | None


def fetch_latest_price_history_rows(
    db: Session,
    match_ids: list[int],
    *,
    before: datetime | None = None,
) -> dict[int, PriceHistory]:
    """
    Return the latest ``PriceHistory`` row per match.

    When ``before`` is supplied, the snapshot is taken from the most recent row at
    or before that timestamp. This supports "current" and "7 days ago" lookups
    without one query per match.
    """
    if not match_ids:
        return {}

    latest_timestamp_query = db.query(
        PriceHistory.match_id.label("match_id"),
        func.max(PriceHistory.timestamp).label("max_timestamp"),
    ).filter(
        PriceHistory.match_id.in_(match_ids)
    )

    if before is not None:
        latest_timestamp_query = latest_timestamp_query.filter(
            PriceHistory.timestamp <= before
        )

    latest_timestamp_subquery = latest_timestamp_query.group_by(
        PriceHistory.match_id
    ).subquery()

    rows = db.query(PriceHistory).join(
        latest_timestamp_subquery,
        and_(
            PriceHistory.match_id == latest_timestamp_subquery.c.match_id,
            PriceHistory.timestamp == latest_timestamp_subquery.c.max_timestamp,
        ),
    ).order_by(
        PriceHistory.match_id.asc(),
        PriceHistory.id.desc(),
    ).all()

    latest_rows: dict[int, PriceHistory] = {}
    for row in rows:
        if row.match_id in latest_rows:
            continue
        latest_rows[row.match_id] = row

    return latest_rows


def fetch_first_price_history_rows(
    db: Session,
    match_ids: list[int],
    *,
    since: datetime | None = None,
) -> dict[int, PriceHistory]:
    """
    Return the earliest ``PriceHistory`` row per match.

    This is mainly used for "price drop since X days ago" style calculations.
    """
    if not match_ids:
        return {}

    first_timestamp_query = db.query(
        PriceHistory.match_id.label("match_id"),
        func.min(PriceHistory.timestamp).label("min_timestamp"),
    ).filter(
        PriceHistory.match_id.in_(match_ids)
    )

    if since is not None:
        first_timestamp_query = first_timestamp_query.filter(
            PriceHistory.timestamp >= since
        )

    first_timestamp_subquery = first_timestamp_query.group_by(
        PriceHistory.match_id
    ).subquery()

    rows = db.query(PriceHistory).join(
        first_timestamp_subquery,
        and_(
            PriceHistory.match_id == first_timestamp_subquery.c.match_id,
            PriceHistory.timestamp == first_timestamp_subquery.c.min_timestamp,
        ),
    ).order_by(
        PriceHistory.match_id.asc(),
        PriceHistory.id.asc(),
    ).all()

    first_rows: dict[int, PriceHistory] = {}
    for row in rows:
        if row.match_id in first_rows:
            continue
        first_rows[row.match_id] = row

    return first_rows


def fetch_price_history_rows(
    db: Session,
    match_ids: list[int],
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[int, list[PriceHistory]]:
    """Return ordered ``PriceHistory`` rows grouped by match id."""
    grouped_rows: dict[int, list[PriceHistory]] = defaultdict(list)
    if not match_ids:
        return grouped_rows

    query = db.query(PriceHistory).filter(
        PriceHistory.match_id.in_(match_ids)
    )

    if since is not None:
        query = query.filter(PriceHistory.timestamp >= since)
    if until is not None:
        query = query.filter(PriceHistory.timestamp <= until)

    rows = query.order_by(
        PriceHistory.match_id.asc(),
        PriceHistory.timestamp.asc(),
        PriceHistory.id.asc(),
    ).all()

    for row in rows:
        grouped_rows[row.match_id].append(row)

    return grouped_rows


def fetch_latest_price_snapshots(
    db: Session,
    match_ids: list[int],
    *,
    before: datetime | None = None,
) -> dict[int, PriceSnapshot]:
    """Return the latest known price snapshot per match."""
    latest_rows = fetch_latest_price_history_rows(
        db,
        match_ids,
        before=before,
    )

    return {
        match_id: PriceSnapshot(
            match_id=row.match_id,
            price=row.price,
            in_stock=row.in_stock,
            timestamp=row.timestamp,
        )
        for match_id, row in latest_rows.items()
    }


def get_product_summaries(
    db: Session,
    *,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    Fetch paginated product summaries for the products page with batch queries.
    """
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == user_id
    ).order_by(
        ProductMonitored.created_at.desc()
    ).offset(offset).limit(limit).all()

    product_ids = [product.id for product in products]
    if not product_ids:
        return []

    matches = db.query(
        CompetitorMatch.id,
        CompetitorMatch.monitored_product_id,
    ).filter(
        CompetitorMatch.monitored_product_id.in_(product_ids)
    ).all()

    match_ids_by_product: dict[int, list[int]] = defaultdict(list)
    all_match_ids: list[int] = []
    for match in matches:
        match_ids_by_product[match.monitored_product_id].append(match.id)
        all_match_ids.append(match.id)

    latest_snapshots = fetch_latest_price_snapshots(db, all_match_ids)
    week_ago_snapshots = fetch_latest_price_snapshots(
        db,
        all_match_ids,
        before=datetime.utcnow() - timedelta(days=7),
    )

    summaries = []
    for product in products:
        latest_prices = []
        week_ago_prices = []
        in_stock_count = 0

        for match_id in match_ids_by_product.get(product.id, []):
            latest = latest_snapshots.get(match_id)
            if latest and latest.price is not None:
                latest_prices.append(latest.price)
                if latest.in_stock:
                    in_stock_count += 1

            week_ago = week_ago_snapshots.get(match_id)
            if week_ago and week_ago.price is not None:
                week_ago_prices.append(week_ago.price)

        lowest_price = min(latest_prices) if latest_prices else None
        avg_price = (sum(latest_prices) / len(latest_prices)) if latest_prices else None

        price_position = None
        if product.my_price is not None and lowest_price is not None:
            if product.my_price <= lowest_price:
                price_position = "cheapest"
            elif avg_price is not None and product.my_price > avg_price * 1.1:
                price_position = "expensive"
            else:
                price_position = "mid"

        price_change_pct = None
        if latest_prices and week_ago_prices:
            current_avg = sum(latest_prices) / len(latest_prices)
            old_avg = sum(week_ago_prices) / len(week_ago_prices)
            if old_avg:
                price_change_pct = round(((current_avg - old_avg) / old_avg) * 100, 1)

        summaries.append(
            {
                "id": product.id,
                "title": product.title,
                "sku": product.sku,
                "brand": product.brand,
                "image_url": product.image_url,
                "my_price": product.my_price,
                "description": product.description,
                "mpn": product.mpn,
                "upc_ean": product.upc_ean,
                "cost_price": product.cost_price,
                "created_at": product.created_at,
                "competitor_count": len(match_ids_by_product.get(product.id, [])),
                "lowest_price": round(lowest_price, 2) if lowest_price is not None else None,
                "avg_price": round(avg_price, 2) if avg_price is not None else None,
                "in_stock_count": in_stock_count,
                "price_position": price_position,
                "price_change_pct": price_change_pct,
            }
        )

    return summaries


def get_home_catalog_summary(
    db: Session,
    *,
    user_id: int,
    recent_limit: int = 6,
) -> dict:
    """
    Lightweight summary for the homepage so the frontend doesn't fetch the full
    catalog just to render counts and a short recent list.
    """
    total_products = db.query(func.count(ProductMonitored.id)).filter(
        ProductMonitored.user_id == user_id
    ).scalar() or 0

    total_matches = db.query(func.count(CompetitorMatch.id)).join(
        ProductMonitored,
        CompetitorMatch.monitored_product_id == ProductMonitored.id,
    ).filter(
        ProductMonitored.user_id == user_id
    ).scalar() or 0

    total_competitors = db.query(func.count(CompetitorWebsite.id)).scalar() or 0

    recent_summaries = get_product_summaries(
        db,
        user_id=user_id,
        limit=recent_limit,
        offset=0,
    )

    recent_products = [
        {
            "id": summary["id"],
            "title": summary["title"],
            "brand": summary["brand"],
            "competitor_count": summary["competitor_count"],
            "created_at": summary["created_at"],
        }
        for summary in recent_summaries
    ]

    return {
        "total_products": total_products,
        "total_matches": total_matches,
        "total_competitors": total_competitors,
        "recent_products": recent_products,
    }
