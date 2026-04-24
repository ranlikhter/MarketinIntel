"""
Price Elasticity Service

Computes per-product price elasticity using a log-log demand model:
    log(Q) = alpha + beta * log(P)

where beta is the elasticity coefficient (typically -0.5 to -3.0 for e-commerce).

Three computation strategies (in priority order):
1. regression   — uses MyPriceHistory + scraped units_sold_past_month snapshots
2. competitor_proxy — uses competitor price spread as an elasticity signal
3. market_default   — falls back to beta = -1.5 (typical e-commerce default)

Simulation endpoint uses stored coefficients to project:
  - demand change %
  - revenue change %
  - margin change % (if cost_price known)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database.models import (
    CompetitorMatch,
    MyPriceHistory,
    PriceHistory,
    ProductElasticity,
    ProductMonitored,
)

logger = logging.getLogger(__name__)

# Default elasticity when no data is available (mid-range e-commerce estimate)
_DEFAULT_BETA = -1.5
# Minimum data points needed for regression; below this we fall back
_MIN_REGRESSION_POINTS = 4
# How many days of price history to use
_HISTORY_DAYS = 90


def get_or_compute_elasticity(product_id: int, db: Session) -> ProductElasticity:
    """
    Return the stored elasticity for a product, computing it if stale/missing.
    Cache TTL is 7 days; recomputes synchronously on miss (fast).
    """
    existing = db.query(ProductElasticity).filter(
        ProductElasticity.product_id == product_id
    ).first()

    if existing and existing.valid_until and existing.valid_until > datetime.utcnow():
        return existing

    return _compute_and_store(product_id, db, existing)


def simulate_price_change(
    product_id: int,
    proposed_price: float,
    db: Session,
) -> dict:
    """
    Simulate the effect of changing to `proposed_price`.

    Returns a dict with projected demand, revenue, and margin changes.
    """
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id
    ).first()
    if not product:
        return {"error": "Product not found"}

    current_price = product.my_price
    if not current_price or current_price <= 0:
        return {"error": "Product has no current price set"}
    if proposed_price <= 0:
        return {"error": "Proposed price must be positive"}

    elasticity = get_or_compute_elasticity(product_id, db)

    price_change_pct = round((proposed_price - current_price) / current_price * 100, 2)

    # log-log model: demand_ratio = (proposed/current)^beta
    demand_ratio = (proposed_price / current_price) ** elasticity.beta
    demand_change_pct = round((demand_ratio - 1) * 100, 2)

    # Revenue = price × demand; ratio = (proposed/current) × demand_ratio
    revenue_ratio = (proposed_price / current_price) * demand_ratio
    revenue_change_pct = round((revenue_ratio - 1) * 100, 2)

    # Margin (only if cost_price known)
    margin_change_pct = None
    cost_price = getattr(product, "cost_price", None)
    if cost_price and cost_price > 0:
        current_margin = (current_price - cost_price) / current_price
        proposed_margin = (proposed_price - cost_price) / proposed_price
        if proposed_price > cost_price:
            # Effective margin change accounting for volume
            margin_change_pct = round(
                ((proposed_margin * demand_ratio) - current_margin) / current_margin * 100, 2
            )

    # Confidence label
    confidence = _confidence_label(elasticity)

    return {
        "product_id": product_id,
        "current_price": round(current_price, 2),
        "proposed_price": round(proposed_price, 2),
        "price_change_pct": price_change_pct,
        "projected_demand_change_pct": demand_change_pct,
        "projected_revenue_change_pct": revenue_change_pct,
        "projected_margin_change_pct": margin_change_pct,
        "elasticity_coefficient": round(elasticity.beta, 3),
        "model_method": elasticity.method,
        "model_confidence": confidence,
        "r_squared": elasticity.r_squared,
        "data_points": elasticity.data_points,
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _compute_and_store(
    product_id: int,
    db: Session,
    existing: Optional[ProductElasticity],
) -> ProductElasticity:
    """Compute elasticity, upsert into DB, return the model row."""
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id
    ).first()
    if not product:
        raise ValueError(f"Product {product_id} not found")

    alpha, beta, r_sq, n_points, method = _compute_coefficients(product, db)

    now = datetime.utcnow()
    valid_until = now + timedelta(days=7)

    if existing:
        existing.alpha = alpha
        existing.beta = beta
        existing.r_squared = r_sq
        existing.data_points = n_points
        existing.method = method
        existing.baseline_price = product.my_price
        existing.computed_at = now
        existing.valid_until = valid_until
        db.commit()
        db.refresh(existing)
        return existing

    row = ProductElasticity(
        product_id=product_id,
        workspace_id=getattr(product, "workspace_id", None),
        alpha=alpha,
        beta=beta,
        r_squared=r_sq,
        data_points=n_points,
        method=method,
        baseline_price=product.my_price,
        computed_at=now,
        valid_until=valid_until,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _compute_coefficients(product: ProductMonitored, db: Session):
    """
    Try regression → competitor proxy → market default.
    Returns (alpha, beta, r_squared, n_points, method).
    """
    # Strategy 1: regression over (my_price, units_sold) snapshots
    result = _try_regression(product, db)
    if result:
        return result

    # Strategy 2: competitor price spread as elasticity signal
    result = _try_competitor_proxy(product, db)
    if result:
        return result

    # Strategy 3: market default
    return _market_default(product)


def _try_regression(product: ProductMonitored, db: Session):
    """
    Pair MyPriceHistory price changes with units_sold_past_month from
    PriceHistory rows scraped around the same time.

    We use scraped competitor data as a proxy for demand — when
    units_sold_past_month is populated on PriceHistory, it represents
    demand velocity at that price point.
    """
    since = datetime.utcnow() - timedelta(days=_HISTORY_DAYS)

    # Gather (price, units_sold) pairs from price history snapshots
    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product.id
    ).all()

    observations: list[tuple[float, float]] = []
    for m in matches:
        rows = db.query(PriceHistory.price, PriceHistory.units_sold_past_month).filter(
            PriceHistory.match_id == m.id,
            PriceHistory.timestamp >= since,
            PriceHistory.units_sold_past_month.isnot(None),
            PriceHistory.price > 0,
            PriceHistory.units_sold_past_month > 0,
        ).all()
        observations.extend((r.price, float(r.units_sold_past_month)) for r in rows)

    # Also use MyPriceHistory if product has own unit data
    if product.units_sold_past_month:
        my_hist = db.query(MyPriceHistory).filter(
            MyPriceHistory.product_id == product.id,
            MyPriceHistory.new_price > 0,
        ).order_by(MyPriceHistory.changed_at).all()
        for i, h in enumerate(my_hist):
            # Use current units for all own-price observations (rough proxy)
            observations.append((h.new_price, float(product.units_sold_past_month)))

    if len(observations) < _MIN_REGRESSION_POINTS:
        return None

    log_p = [math.log(p) for p, _ in observations]
    log_q = [math.log(q) for _, q in observations]

    alpha, beta, r_sq = _ols(log_p, log_q)
    if beta >= 0:
        # Positive elasticity is nonsensical; discard
        return None

    return alpha, beta, r_sq, len(observations), "regression"


def _try_competitor_proxy(product: ProductMonitored, db: Session):
    """
    When no unit data exists, use the spread of competitor prices as a signal.

    Heuristic: a tight price cluster → high elasticity (−2.5);
               a wide spread → low elasticity (−0.8).
    Linear interpolation between those anchors.
    """
    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product.id,
        CompetitorMatch.latest_price.isnot(None),
        CompetitorMatch.latest_price > 0,
    ).all()

    if len(matches) < 2:
        return None

    prices = [m.latest_price for m in matches]
    price_mean = sum(prices) / len(prices)
    price_cv = (  # coefficient of variation
        (sum((p - price_mean) ** 2 for p in prices) / len(prices)) ** 0.5
        / price_mean
    )

    # CV near 0 → tight cluster → high elasticity; CV > 0.3 → wide spread
    beta = -2.5 + (price_cv / 0.3) * 1.7
    beta = max(-2.5, min(-0.8, beta))

    # alpha anchored so that at the mean price demand = 1
    alpha = -beta * math.log(price_mean)

    return alpha, beta, None, len(prices), "competitor_proxy"


def _market_default(product: ProductMonitored):
    """Use beta = -1.5 anchored to my_price (or competitor mean if no own price)."""
    anchor = product.my_price or 50.0
    beta = _DEFAULT_BETA
    alpha = -beta * math.log(anchor)
    return alpha, beta, None, 0, "market_default"


def _ols(x: list[float], y: list[float]):
    """Ordinary Least Squares: y = a + b*x. Returns (alpha, beta, r_squared)."""
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)

    if ss_xx == 0:
        return mean_y, 0.0, 0.0

    beta = ss_xy / ss_xx
    alpha = mean_y - beta * mean_x

    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    if ss_tot == 0:
        r_sq = 1.0
    else:
        y_pred = [alpha + beta * xi for xi in x]
        ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))
        r_sq = max(0.0, 1.0 - ss_res / ss_tot)

    return alpha, beta, round(r_sq, 3)


def _confidence_label(e: ProductElasticity) -> str:
    if e.method == "regression":
        if e.r_squared and e.r_squared >= 0.7:
            return "high"
        return "medium"
    if e.method == "competitor_proxy":
        return "low"
    return "estimate"
