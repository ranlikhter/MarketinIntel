"""
Price Analytics Service
Calculates trends, averages, and insights from price history data.

Performance design
──────────────────
All three public methods previously executed one SQL query **per competitor
match** inside a Python loop (N+1 anti-pattern).  This version replaces those
loops with a single batched query that fetches data for *all* matches in one
round-trip, then groups the result in Python.

Query count comparison (for a product with M competitors):
  Before  After
  get_product_trendline    1 + M     2   (1 for matches, 1 for all price data)
  get_competitor_comparison 1 + M    2
  get_price_alerts         1 + 2M   3   (1 for matches, 2 time-window queries)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from database.models import PriceHistory, CompetitorMatch, ProductMonitored

import logging
logger = logging.getLogger(__name__)


class PriceAnalytics:
    """Service for calculating price trends and analytics."""

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def get_product_trendline(self, product_id: int, days: int = 30) -> Dict:
        """
        Get daily price trendline for a product.

        Executes exactly 2 SQL queries regardless of how many competitor
        matches the product has.
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            matches = self._get_matches(product_id)
            if not matches:
                return {"success": False, "message": "No competitor data found"}

            match_ids = [m.id for m in matches]
            match_by_id = {m.id: m for m in matches}

            # ── Single batched aggregation query ──────────────────────────────
            # GROUP BY (match_id, date) — one query replaces N queries.
            rows = (
                self.db.query(
                    PriceHistory.match_id,
                    func.date(PriceHistory.timestamp).label("date"),
                    func.avg(PriceHistory.price).label("avg_price"),
                    func.min(PriceHistory.price).label("min_price"),
                    func.max(PriceHistory.price).label("max_price"),
                    func.count(PriceHistory.id).label("count"),
                )
                .filter(
                    PriceHistory.match_id.in_(match_ids),
                    PriceHistory.timestamp >= start_date,
                    PriceHistory.timestamp <= end_date,
                )
                .group_by(PriceHistory.match_id, func.date(PriceHistory.timestamp))
                .order_by(PriceHistory.match_id, func.date(PriceHistory.timestamp))
                .all()
            )

            # ── Group results by match in Python ──────────────────────────────
            by_match: Dict[int, List[Dict]] = defaultdict(list)
            for row in rows:
                by_match[row.match_id].append(
                    {
                        "date": str(row.date),
                        "avg_price": float(row.avg_price),
                        "min_price": float(row.min_price),
                        "max_price": float(row.max_price),
                        "count": row.count,
                    }
                )

            # Build per-competitor series
            competitors_data: List[Dict] = []
            # Build aggregate daily series (across all competitors)
            daily_aggregates: Dict[str, List[float]] = defaultdict(list)

            for match_id, daily_prices in by_match.items():
                match = match_by_id[match_id]
                competitors_data.append(
                    {
                        "competitor_id": match_id,
                        "competitor_name": match.competitor_name,
                        "daily_prices": daily_prices,
                    }
                )
                for dp in daily_prices:
                    daily_aggregates[dp["date"]].append(dp["avg_price"])

            # Overall daily trend (mean of competitor means)
            daily_trend = [
                {
                    "date": date,
                    "avg_price": sum(prices) / len(prices),
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "competitor_count": len(prices),
                }
                for date, prices in sorted(daily_aggregates.items())
            ]

            return {
                "success": True,
                "product_id": product_id,
                "date_range": {
                    "start": str(start_date.date()),
                    "end": str(end_date.date()),
                    "days": days,
                },
                "daily_trend": daily_trend,
                "by_competitor": competitors_data,
                "insights": self._calculate_insights(daily_trend),
            }

        except Exception as e:
            logger.exception("Error calculating trendline for product %s: %s", product_id, e)
            return {"success": False, "error": str(e)}

    def get_competitor_comparison(self, product_id: int, days: int = 7) -> Dict:
        """
        Compare prices across competitors for a recent period.

        Executes exactly 2 SQL queries regardless of how many competitor
        matches the product has.
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            matches = self._get_matches(product_id)
            if not matches:
                return {"success": True, "product_id": product_id, "period_days": days,
                        "competitors": [], "summary": {"total_competitors": 0}}

            match_ids = [m.id for m in matches]
            match_by_id = {m.id: m for m in matches}

            # ── Single batched aggregation query ──────────────────────────────
            rows = (
                self.db.query(
                    PriceHistory.match_id,
                    func.avg(PriceHistory.price).label("avg_price"),
                    func.min(PriceHistory.price).label("min_price"),
                    func.max(PriceHistory.price).label("max_price"),
                    func.count(PriceHistory.id).label("count"),
                )
                .filter(
                    PriceHistory.match_id.in_(match_ids),
                    PriceHistory.timestamp >= start_date,
                )
                .group_by(PriceHistory.match_id)
                .all()
            )

            competitors = []
            for row in rows:
                if row.avg_price is None:
                    continue
                match = match_by_id[row.match_id]
                competitors.append(
                    {
                        "competitor_id": row.match_id,
                        "competitor_name": match.competitor_name,
                        "competitor_url": match.competitor_url,
                        "avg_price": round(float(row.avg_price), 2),
                        "min_price": round(float(row.min_price), 2),
                        "max_price": round(float(row.max_price), 2),
                        "price_checks": row.count,
                    }
                )

            competitors.sort(key=lambda x: x["avg_price"])
            for i, comp in enumerate(competitors):
                comp["rank"] = i + 1
                comp["is_lowest"] = i == 0
                comp["is_highest"] = i == len(competitors) - 1

            return {
                "success": True,
                "product_id": product_id,
                "period_days": days,
                "competitors": competitors,
                "summary": {
                    "total_competitors": len(competitors),
                    "lowest_price": competitors[0]["avg_price"] if competitors else None,
                    "highest_price": competitors[-1]["avg_price"] if competitors else None,
                    "price_spread": round(
                        competitors[-1]["avg_price"] - competitors[0]["avg_price"], 2
                    ) if len(competitors) > 1 else None,
                },
            }

        except Exception as e:
            logger.exception("Error in competitor comparison for product %s: %s", product_id, e)
            return {"success": False, "error": str(e)}

    def get_price_alerts(self, product_id: int, threshold_pct: float = 5.0) -> Dict:
        """
        Check for significant price changes that should trigger alerts.

        Executes exactly 3 SQL queries regardless of how many competitor
        matches the product has (down from 1 + 2*N).
        """
        try:
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            day_before = yesterday - timedelta(days=1)

            matches = self._get_matches(product_id)
            if not matches:
                return {"success": True, "product_id": product_id, "alerts_count": 0, "alerts": []}

            match_ids = [m.id for m in matches]
            match_by_id = {m.id: m for m in matches}

            # ── Two batched window queries (recent + previous) ─────────────────
            recent_rows = (
                self.db.query(
                    PriceHistory.match_id,
                    func.avg(PriceHistory.price).label("avg_price"),
                )
                .filter(
                    PriceHistory.match_id.in_(match_ids),
                    PriceHistory.timestamp >= yesterday,
                )
                .group_by(PriceHistory.match_id)
                .all()
            )

            previous_rows = (
                self.db.query(
                    PriceHistory.match_id,
                    func.avg(PriceHistory.price).label("avg_price"),
                )
                .filter(
                    PriceHistory.match_id.in_(match_ids),
                    PriceHistory.timestamp >= day_before,
                    PriceHistory.timestamp < yesterday,
                )
                .group_by(PriceHistory.match_id)
                .all()
            )

            recent_by_match = {r.match_id: float(r.avg_price) for r in recent_rows if r.avg_price}
            prev_by_match = {r.match_id: float(r.avg_price) for r in previous_rows if r.avg_price}

            alerts = []
            for match_id, recent_price in recent_by_match.items():
                previous_price = prev_by_match.get(match_id)
                if previous_price is None or previous_price == 0:
                    continue
                change = recent_price - previous_price
                change_pct = change / previous_price * 100
                if abs(change_pct) >= threshold_pct:
                    match = match_by_id[match_id]
                    alerts.append(
                        {
                            "competitor_name": match.competitor_name,
                            "previous_price": round(previous_price, 2),
                            "current_price": round(recent_price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "alert_type": "price_drop" if change < 0 else "price_increase",
                            "severity": "high" if abs(change_pct) > 10 else "medium",
                        }
                    )

            return {
                "success": True,
                "product_id": product_id,
                "alerts_count": len(alerts),
                "alerts": sorted(alerts, key=lambda x: abs(x["change_pct"]), reverse=True),
            }

        except Exception as e:
            logger.exception("Error checking price alerts for product %s: %s", product_id, e)
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_matches(self, product_id: int) -> List[CompetitorMatch]:
        """Return all CompetitorMatch rows for a product (1 query)."""
        return (
            self.db.query(CompetitorMatch)
            .filter(CompetitorMatch.monitored_product_id == product_id)
            .all()
        )

    def _calculate_insights(self, daily_trend: List[Dict]) -> Dict:
        """Derive trend insights from the daily aggregate series."""
        if not daily_trend:
            return {}

        prices = [d["avg_price"] for d in daily_trend]
        current_price = prices[-1]
        oldest_price = prices[0]
        price_change = current_price - oldest_price
        price_change_pct = (price_change / oldest_price * 100) if oldest_price else 0

        avg_price = sum(prices) / len(prices)
        lowest_price = min(prices)
        highest_price = max(prices)

        trend_direction = "stable"
        if abs(price_change_pct) > 5:
            trend_direction = "increasing" if price_change > 0 else "decreasing"

        mean = avg_price
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        volatility = (std_dev / mean * 100) if mean else 0

        price_changes = sum(1 for i in range(1, len(prices)) if prices[i] != prices[i - 1])
        stability_score = 100 - (price_changes / len(prices) * 100)

        return {
            "current_price": round(current_price, 2),
            "oldest_price": round(oldest_price, 2),
            "price_change": round(price_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "avg_price_period": round(avg_price, 2),
            "lowest_price": round(lowest_price, 2),
            "highest_price": round(highest_price, 2),
            "price_range": round(highest_price - lowest_price, 2),
            "trend_direction": trend_direction,
            "volatility_pct": round(volatility, 2),
            "stability_score": round(stability_score, 2),
            "recommendation": self._get_recommendation(
                current_price, avg_price, trend_direction, volatility
            ),
        }

    def _get_recommendation(
        self,
        current_price: float,
        avg_price: float,
        trend: str,
        volatility: float,
    ) -> str:
        if current_price < avg_price * 0.95:
            return "Great time to buy - price below average"
        if current_price > avg_price * 1.05:
            return "Price above average - consider waiting"
        if trend == "decreasing":
            return "Price trending down - monitor for better deals"
        if trend == "increasing":
            return "Price trending up - consider buying soon"
        if volatility > 10:
            return "High volatility - price changes frequently"
        return "Stable pricing - consistent over time"
