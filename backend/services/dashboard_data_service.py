"""
Dashboard Data Service
Computes data payloads for every widget type.

Each method takes a `product_id`, time-window `days`, and an optional
`config` dict, and returns a JSON-serialisable dict ready to be sent
to the frontend.

Query discipline: every method issues at most 3 SQL queries regardless
of how many competitor matches the product has.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

from sqlalchemy import func, and_, desc, case
from sqlalchemy.orm import Session

from database.models import (
    CompetitorMatch,
    PriceHistory,
    ProductMonitored,
    ReviewSnapshot,
    ListingQualitySnapshot,
)

import logging

logger = logging.getLogger(__name__)

# ── Colour palettes ────────────────────────────────────────────────────────────
PALETTES = {
    "blue":    ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#2563EB", "#1D4ED8"],
    "green":   ["#10B981", "#34D399", "#6EE7B7", "#A7F3D0", "#059669", "#047857"],
    "purple":  ["#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE", "#7C3AED", "#6D28D9"],
    "orange":  ["#F59E0B", "#FBBF24", "#FCD34D", "#FDE68A", "#D97706", "#B45309"],
    "rainbow": ["#EF4444", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6", "#EC4899",
                "#06B6D4", "#84CC16"],
}


def _palette(scheme: str, n: int) -> List[str]:
    colours = PALETTES.get(scheme, PALETTES["rainbow"])
    return [colours[i % len(colours)] for i in range(n)]


def _get_matches(db: Session, product_id: int,
                 competitor_filter: Optional[List[str]] = None) -> List[CompetitorMatch]:
    q = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product_id
    )
    if competitor_filter:
        q = q.filter(CompetitorMatch.competitor_name.in_(competitor_filter))
    return q.order_by(desc(CompetitorMatch.match_score)).all()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Bubble Chart — Competitive Positioning
# ══════════════════════════════════════════════════════════════════════════════

def get_bubble_chart_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    """
    Returns competitors plotted as bubbles:
      X = latest_price   Y = rating   size = review_count
    """
    matches = _get_matches(db, product_id, config.get("competitors"))
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()

    metric = config.get("metric", "price")
    colours = _palette(config.get("color_scheme", "rainbow"), len(matches))

    competitors = []
    for i, m in enumerate(matches):
        if m.latest_price is None:
            continue
        x = m.latest_price if metric == "price" else (m.effective_price or m.latest_price)
        competitors.append({
            "id": m.id,
            "name": m.competitor_name,
            "x": round(x, 2),
            "y": round(m.rating or 0, 2),
            "r": max(4, min(40, int((m.review_count or 10) ** 0.45))),  # log-scale radius
            "review_count": m.review_count or 0,
            "bsr": m.best_seller_rank,
            "stock_status": m.stock_status,
            "is_prime": m.is_prime,
            "fulfillment_type": m.fulfillment_type,
            "url": m.competitor_url,
            "color": colours[i],
        })

    your_price = product.my_price if product else None
    return {
        "competitors": sorted(competitors, key=lambda c: c["x"]),
        "your_product": {
            "price": your_price,
            "name": product.title if product else "Your Product",
        },
        "axes": {
            "x": "Price ($)" if metric == "price" else "Effective Price ($)",
            "y": "Avg Rating (0–5)",
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. Price History — Multi-line trendlines
# ══════════════════════════════════════════════════════════════════════════════

def get_price_history_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    days = int(config.get("days", 30))
    metric = config.get("metric", "price")
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    matches = _get_matches(db, product_id, config.get("competitors"))
    if not matches:
        return {"dates": [], "datasets": [], "events": []}

    match_ids = [m.id for m in matches]
    match_by_id = {m.id: m for m in matches}
    colours = _palette(config.get("color_scheme", "blue"), len(matches))

    price_col = PriceHistory.price if metric == "price" else (
        func.coalesce(PriceHistory.effective_price, PriceHistory.price)
    )

    rows = (
        db.query(
            PriceHistory.match_id,
            func.date(PriceHistory.timestamp).label("dt"),
            func.avg(price_col).label("avg"),
            func.min(price_col).label("mn"),
            func.max(price_col).label("mx"),
        )
        .filter(
            PriceHistory.match_id.in_(match_ids),
            PriceHistory.timestamp.between(start, end),
        )
        .group_by(PriceHistory.match_id, func.date(PriceHistory.timestamp))
        .order_by(PriceHistory.match_id, func.date(PriceHistory.timestamp))
        .all()
    )

    # Build date spine so all series are aligned
    all_dates = sorted({str(r.dt) for r in rows})

    by_match: Dict[int, Dict[str, float]] = defaultdict(dict)
    for r in rows:
        by_match[r.match_id][str(r.dt)] = round(float(r.avg), 2)

    datasets = []
    for i, match in enumerate(matches):
        if match.id not in by_match:
            continue
        data_map = by_match[match.id]
        datasets.append({
            "label": match.competitor_name,
            "data": [data_map.get(d) for d in all_dates],
            "color": colours[i],
            "url": match.competitor_url,
        })

    return {"dates": all_dates, "datasets": datasets, "metric": metric}


# ══════════════════════════════════════════════════════════════════════════════
# 3. Radar — Listing Quality Spider
# ══════════════════════════════════════════════════════════════════════════════

def get_radar_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    matches = _get_matches(db, product_id, config.get("competitors"))
    if not matches:
        return {"axes": [], "datasets": []}

    match_ids = [m.id for m in matches]
    match_by_id = {m.id: m for m in matches}
    colours = _palette(config.get("color_scheme", "purple"), len(matches))

    # Latest listing quality snapshot per match
    latest_lqs = (
        db.query(
            ListingQualitySnapshot.match_id,
            ListingQualitySnapshot.image_count,
            ListingQualitySnapshot.has_video,
            ListingQualitySnapshot.has_aplus_content,
            ListingQualitySnapshot.bullet_point_count,
            ListingQualitySnapshot.listing_score,
        )
        .filter(ListingQualitySnapshot.match_id.in_(match_ids))
        .order_by(ListingQualitySnapshot.match_id, desc(ListingQualitySnapshot.scraped_at))
        .distinct(ListingQualitySnapshot.match_id)
        .all()
    )
    lqs_by_match = {r.match_id: r for r in latest_lqs}

    def _norm(val, max_val, cap=100):
        if val is None:
            return 0
        return min(cap, round(val / max_val * 100))

    axes = ["Images", "Video", "A+ Content", "Bullets", "Rating", "Reviews", "Quality Score"]

    datasets = []
    for i, m in enumerate(matches):
        lqs = lqs_by_match.get(m.id)
        scores = [
            _norm(lqs.image_count if lqs else m.image_count, 9),
            100 if (lqs.has_video if lqs else m.has_video) else 0,
            100 if (lqs.has_aplus_content if lqs else m.has_aplus_content) else 0,
            _norm(lqs.bullet_point_count if lqs else m.bullet_point_count, 5),
            _norm(m.rating, 5),
            _norm(m.review_count, 5000),
            lqs.listing_score if lqs and lqs.listing_score else (m.listing_quality_score or 0),
        ]
        datasets.append({
            "label": m.competitor_name,
            "data": scores,
            "color": colours[i],
        })

    return {"axes": axes, "datasets": datasets}


# ══════════════════════════════════════════════════════════════════════════════
# 4. Calendar Heatmap — Price change intensity per day
# ══════════════════════════════════════════════════════════════════════════════

def get_calendar_heatmap_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    days = int(config.get("days", 90))
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    matches = _get_matches(db, product_id, config.get("competitors"))
    if not matches:
        return {"cells": [], "min_change": 0, "max_change": 0}

    match_ids = [m.id for m in matches]
    match_by_id = {m.id: m for m in matches}

    rows = (
        db.query(
            func.date(PriceHistory.timestamp).label("dt"),
            PriceHistory.match_id,
            func.avg(PriceHistory.price).label("avg_price"),
            func.min(PriceHistory.price).label("min_price"),
        )
        .filter(
            PriceHistory.match_id.in_(match_ids),
            PriceHistory.timestamp.between(start, end),
        )
        .group_by(func.date(PriceHistory.timestamp), PriceHistory.match_id)
        .order_by(func.date(PriceHistory.timestamp))
        .all()
    )

    # Build daily average across all competitors
    daily: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        daily[str(r.dt)].append(float(r.avg_price))

    ordered_dates = sorted(daily.keys())
    cells = []
    prev_price = None
    for d in ordered_dates:
        avg = sum(daily[d]) / len(daily[d])
        if prev_price and prev_price > 0:
            chg = (avg - prev_price) / prev_price * 100
        else:
            chg = 0.0
        cells.append({
            "date": d,
            "avg_price": round(avg, 2),
            "change_pct": round(chg, 2),
            "direction": "up" if chg > 0.5 else ("down" if chg < -0.5 else "flat"),
            "sample_count": len(daily[d]),
        })
        prev_price = avg

    changes = [c["change_pct"] for c in cells]
    return {
        "cells": cells,
        "min_change": min(changes) if changes else 0,
        "max_change": max(changes) if changes else 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. Momentum Scatter — Price Δ% vs Review Velocity
# ══════════════════════════════════════════════════════════════════════════════

def get_momentum_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    days = int(config.get("days", 30))
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    matches = _get_matches(db, product_id, config.get("competitors"))
    if not matches:
        return {"competitors": [], "quadrant_labels": _quadrant_labels()}

    match_ids = [m.id for m in matches]
    colours = _palette(config.get("color_scheme", "rainbow"), len(matches))

    # Price: oldest vs latest in window
    price_endpoints = (
        db.query(
            PriceHistory.match_id,
            func.min(PriceHistory.price).label("oldest_price"),
            func.max(PriceHistory.timestamp).label("latest_ts"),
        )
        .filter(
            PriceHistory.match_id.in_(match_ids),
            PriceHistory.timestamp >= period_start,
        )
        .group_by(PriceHistory.match_id)
        .all()
    )
    price_by_match = {r.match_id: r for r in price_endpoints}

    # Review velocity: review_count delta from review_snapshots
    review_snapshots = (
        db.query(
            ReviewSnapshot.match_id,
            func.min(ReviewSnapshot.review_count).label("old_reviews"),
            func.max(ReviewSnapshot.review_count).label("new_reviews"),
        )
        .filter(
            ReviewSnapshot.match_id.in_(match_ids),
            ReviewSnapshot.scraped_at >= period_start,
        )
        .group_by(ReviewSnapshot.match_id)
        .all()
    )
    reviews_by_match = {r.match_id: r for r in review_snapshots}

    competitors = []
    for i, m in enumerate(matches):
        p = price_by_match.get(m.id)
        r = reviews_by_match.get(m.id)

        current_price = m.latest_price or 0
        start_price = float(p.oldest_price) if p and p.oldest_price else current_price
        price_chg_pct = ((current_price - start_price) / start_price * 100
                         if start_price > 0 else 0)

        old_rev = r.old_reviews or m.review_count or 0
        new_rev = r.new_reviews or m.review_count or 0
        review_velocity = (new_rev - old_rev) if (old_rev and new_rev) else 0

        # Bubble size: BSR inverted (lower BSR = bigger bubble, capped)
        bsr = m.best_seller_rank or 99999
        bubble_r = max(6, min(40, int(10000 / bsr ** 0.5)))

        competitors.append({
            "name": m.competitor_name,
            "x": round(price_chg_pct, 2),
            "y": review_velocity,
            "r": bubble_r,
            "latest_price": current_price,
            "bsr": m.best_seller_rank,
            "color": colours[i],
            "quadrant": _classify_quadrant(price_chg_pct, review_velocity),
        })

    return {"competitors": competitors, "quadrant_labels": _quadrant_labels()}


def _classify_quadrant(price_chg: float, review_vel: int) -> str:
    if price_chg <= 0 and review_vel >= 0:
        return "discounting_growing"
    if price_chg > 0 and review_vel >= 0:
        return "premium_growing"
    if price_chg <= 0 and review_vel < 0:
        return "losing_ground"
    return "expensive_stagnant"


def _quadrant_labels() -> Dict[str, str]:
    return {
        "discounting_growing": "Discounting & Growing ⚠️",
        "premium_growing": "Premium & Growing ✨",
        "losing_ground": "Losing Ground 📉",
        "expensive_stagnant": "Expensive & Stagnant 🐌",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. KPI Cards
# ══════════════════════════════════════════════════════════════════════════════

def get_kpi_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    matches = _get_matches(db, product_id)
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()

    priced = [m for m in matches if m.latest_price is not None]
    if not priced:
        return {"cards": []}

    prices = [m.latest_price for m in priced]
    ratings = [m.rating for m in priced if m.rating]
    bsrs = [m.best_seller_rank for m in priced if m.best_seller_rank]

    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)
    your_price = product.my_price if product else None

    # Compare to 7-day-ago prices
    week_ago = datetime.utcnow() - timedelta(days=7)
    match_ids = [m.id for m in priced]
    old_rows = (
        db.query(PriceHistory.match_id, func.avg(PriceHistory.price).label("avg"))
        .filter(
            PriceHistory.match_id.in_(match_ids),
            PriceHistory.timestamp <= week_ago,
        )
        .group_by(PriceHistory.match_id)
        .all()
    )
    old_prices = [float(r.avg) for r in old_rows]
    old_avg = sum(old_prices) / len(old_prices) if old_prices else avg_price
    market_chg_pct = (avg_price - old_avg) / old_avg * 100 if old_avg else 0

    cards = [
        {
            "id": "min_price",
            "title": "Lowest Competitor Price",
            "value": f"${min_price:.2f}",
            "raw": min_price,
            "change": None,
            "color": "green",
            "icon": "arrow-down",
        },
        {
            "id": "avg_price",
            "title": "Market Average Price",
            "value": f"${avg_price:.2f}",
            "raw": avg_price,
            "change": round(market_chg_pct, 1),
            "change_label": "vs 7 days ago",
            "color": "blue",
            "icon": "chart-bar",
        },
        {
            "id": "max_price",
            "title": "Highest Competitor Price",
            "value": f"${max_price:.2f}",
            "raw": max_price,
            "change": None,
            "color": "orange",
            "icon": "arrow-up",
        },
        {
            "id": "your_position",
            "title": "Your Price vs Market",
            "value": (f"+{((your_price - avg_price) / avg_price * 100):.1f}%"
                      if your_price and avg_price
                      else "—"),
            "raw": your_price,
            "change": None,
            "color": ("red" if your_price and your_price > avg_price * 1.05
                      else "green" if your_price and your_price < avg_price * 0.95
                      else "gray"),
            "icon": "tag",
        },
        {
            "id": "avg_rating",
            "title": "Avg Competitor Rating",
            "value": f"{(sum(ratings)/len(ratings)):.1f} ★" if ratings else "—",
            "raw": sum(ratings) / len(ratings) if ratings else None,
            "change": None,
            "color": "yellow",
            "icon": "star",
        },
        {
            "id": "competitor_count",
            "title": "Active Competitors",
            "value": str(len(priced)),
            "raw": len(priced),
            "change": None,
            "color": "purple",
            "icon": "users",
        },
    ]
    return {"cards": cards}


# ══════════════════════════════════════════════════════════════════════════════
# 7. Pie / Doughnut — Distribution
# ══════════════════════════════════════════════════════════════════════════════

def get_pie_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    metric = config.get("pie_metric", "fulfillment_type")
    matches = _get_matches(db, product_id, config.get("competitors"))
    priced = [m for m in matches if m.latest_price is not None]

    if metric == "fulfillment_type":
        counter: Dict[str, int] = defaultdict(int)
        for m in priced:
            counter[m.fulfillment_type or "Unknown"] += 1
        title = "Fulfillment Type Distribution"

    elif metric == "price_range":
        counter = defaultdict(int)
        for m in priced:
            bucket = _price_bucket(m.latest_price)
            counter[bucket] += 1
        title = "Competitor Price Range Distribution"

    elif metric == "stock_status":
        counter = defaultdict(int)
        for m in priced:
            counter[m.stock_status or "Unknown"] += 1
        title = "Stock Status Distribution"

    elif metric == "badges":
        counter = defaultdict(int)
        for m in priced:
            if m.badge_amazons_choice:
                counter["Amazon's Choice"] += 1
            if m.badge_best_seller:
                counter["Best Seller"] += 1
            if m.badge_new_release:
                counter["New Release"] += 1
            if not any([m.badge_amazons_choice, m.badge_best_seller, m.badge_new_release]):
                counter["No Badge"] += 1
        title = "Badge Distribution"
    else:
        counter = defaultdict(int)
        title = "Distribution"

    colours = _palette(config.get("color_scheme", "rainbow"), len(counter))
    slices = [
        {"label": k, "value": v, "color": colours[i]}
        for i, (k, v) in enumerate(sorted(counter.items(), key=lambda x: -x[1]))
    ]
    return {"title": title, "slices": slices, "total": sum(s["value"] for s in slices)}


def _price_bucket(price: float) -> str:
    if price < 10:   return "< $10"
    if price < 25:   return "$10–25"
    if price < 50:   return "$25–50"
    if price < 100:  return "$50–100"
    if price < 200:  return "$100–200"
    return "> $200"


# ══════════════════════════════════════════════════════════════════════════════
# 8. Bar Chart — Price comparison
# ══════════════════════════════════════════════════════════════════════════════

def get_bar_chart_data(db: Session, product_id: int, config: Dict[str, Any]) -> Dict:
    metric = config.get("metric", "price")
    matches = _get_matches(db, product_id, config.get("competitors"))
    product = db.query(ProductMonitored).filter(ProductMonitored.id == product_id).first()

    colours = _palette(config.get("color_scheme", "blue"), len(matches) + 1)

    bars = []
    for i, m in enumerate(matches):
        val = getattr(m, "latest_price" if metric == "price" else
                      ("effective_price" if metric == "effective_price" else
                       ("rating" if metric == "rating" else "latest_price")))
        if val is None:
            continue
        bars.append({"label": m.competitor_name, "value": round(val, 2), "color": colours[i]})

    if product and product.my_price and metric == "price":
        bars.append({"label": "Your Price", "value": product.my_price,
                     "color": "#F59E0B", "is_yours": True})

    bars.sort(key=lambda x: x["value"])
    return {
        "bars": bars,
        "metric": metric,
        "unit": "$" if metric in ("price", "effective_price") else "",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Dispatcher
# ══════════════════════════════════════════════════════════════════════════════

WIDGET_DISPATCH = {
    "bubble_chart":     get_bubble_chart_data,
    "price_history":    get_price_history_data,
    "radar":            get_radar_data,
    "calendar_heatmap": get_calendar_heatmap_data,
    "momentum_scatter": get_momentum_data,
    "kpi_cards":        get_kpi_data,
    "pie_chart":        get_pie_data,
    "bar_chart":        get_bar_chart_data,
}


def get_widget_data(db: Session, widget_type: str,
                    product_id: int, config: Dict[str, Any]) -> Dict:
    fn = WIDGET_DISPATCH.get(widget_type)
    if fn is None:
        return {"error": f"Unknown widget type: {widget_type}"}
    try:
        return fn(db, product_id, config)
    except Exception as e:
        logger.exception("Error computing widget data [%s] for product %s: %s",
                         widget_type, product_id, e)
        return {"error": str(e)}
