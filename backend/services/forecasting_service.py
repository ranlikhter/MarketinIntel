"""
Forecasting Service
Historical analysis and price predictions
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory, User
)
from services.product_catalog_service import (
    fetch_first_price_history_rows,
    fetch_latest_price_history_rows,
    fetch_price_history_rows,
)


class ForecastingService:
    """
    Service for historical price analysis and forecasting
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_price_history_analysis(
        self,
        product_id: int,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Analyze price history for a product across all competitors

        Returns:
        - Time series data
        - Price statistics (min, max, avg, volatility)
        - Trend analysis
        - Seasonality detection
        - Best/worst times to buy
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found"}

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all competitor matches
        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()
        history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=cutoff_date,
        )

        if not matches:
            return {
                "product": self._product_summary(product),
                "message": "No competitor data available"
            }

        # Collect price history for each competitor
        competitor_histories = {}

        for match in matches:
            history = history_by_match.get(match.id, [])

            if history:
                competitor_histories[match.competitor_name] = [
                    {
                        "timestamp": h.timestamp.isoformat(),
                        "price": float(h.price),
                        "in_stock": h.in_stock
                    }
                    for h in history
                ]

        # Calculate statistics across all competitors
        all_prices = []
        for histories in competitor_histories.values():
            all_prices.extend([h["price"] for h in histories if h["price"] > 0])

        if not all_prices:
            return {
                "product": self._product_summary(product),
                "message": "No price data in selected time range"
            }

        statistics_summary = {
            "min_price": min(all_prices),
            "max_price": max(all_prices),
            "avg_price": statistics.mean(all_prices),
            "median_price": statistics.median(all_prices),
            "std_dev": statistics.stdev(all_prices) if len(all_prices) > 1 else 0,
            "price_range": max(all_prices) - min(all_prices),
            "volatility": self._calculate_volatility(all_prices)
        }

        # Trend analysis
        trend = self._analyze_trend(competitor_histories, days)

        # Best times to buy (historical low periods)
        best_times = self._find_best_buying_times(competitor_histories)

        return {
            "product": self._product_summary(product),
            "period_days": days,
            "statistics": statistics_summary,
            "trend": trend,
            "best_buying_times": best_times,
            "competitor_histories": competitor_histories,
            "total_data_points": len(all_prices)
        }

    def forecast_price(
        self,
        product_id: int,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Forecast future prices using simple linear regression

        Note: For production, you'd use more sophisticated methods like:
        - ARIMA (AutoRegressive Integrated Moving Average)
        - Prophet (Facebook's forecasting library)
        - LSTM neural networks

        This uses simple trend extrapolation for MVP.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found"}

        # Get 90 days of history for training
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()
        history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=ninety_days_ago,
        )

        if not matches:
            return {
                "product": self._product_summary(product),
                "message": "No competitor data for forecasting"
            }

        # Collect price data
        all_price_points = []

        for match in matches:
            history = history_by_match.get(match.id, [])

            for h in history:
                if h.price > 0:
                    all_price_points.append({
                        "timestamp": h.timestamp,
                        "price": float(h.price),
                        "competitor": match.competitor_name
                    })

        if len(all_price_points) < 10:
            return {
                "product": self._product_summary(product),
                "message": "Insufficient data for forecasting (need at least 10 data points)"
            }

        # Simple linear regression
        forecast = self._simple_forecast(all_price_points, days_ahead)

        # Calculate confidence intervals
        confidence = self._calculate_confidence_intervals(all_price_points, forecast)

        return {
            "product": self._product_summary(product),
            "forecast_days": days_ahead,
            "current_price": all_price_points[-1]["price"],
            "predicted_price": forecast["predicted_price"],
            "price_change": forecast["price_change"],
            "price_change_pct": forecast["price_change_pct"],
            "trend_direction": forecast["trend_direction"],
            "confidence": confidence,
            "forecast_points": forecast["forecast_points"],
            "methodology": "Simple Linear Regression",
            "data_points_used": len(all_price_points)
        }

    def get_seasonal_patterns(
        self,
        product_id: int,
        months: int = 12
    ) -> Dict[str, Any]:
        """
        Detect seasonal pricing patterns

        Looks for:
        - Day of week patterns (weekend vs weekday)
        - Month-to-month patterns
        - Holiday/event patterns
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found"}

        cutoff_date = datetime.utcnow() - timedelta(days=months * 30)

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()
        history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=cutoff_date,
        )

        # Collect price data grouped by time period
        day_of_week_prices = defaultdict(list)
        month_prices = defaultdict(list)

        for match in matches:
            history = history_by_match.get(match.id, [])

            for h in history:
                if h.price > 0:
                    # Group by day of week (0=Monday, 6=Sunday)
                    day_of_week = h.timestamp.weekday()
                    day_of_week_prices[day_of_week].append(float(h.price))

                    # Group by month
                    month = h.timestamp.month
                    month_prices[month].append(float(h.price))

        # Calculate averages
        day_of_week_avg = {}
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for day in range(7):
            if day in day_of_week_prices and day_of_week_prices[day]:
                day_of_week_avg[day_names[day]] = {
                    "avg_price": round(statistics.mean(day_of_week_prices[day]), 2),
                    "data_points": len(day_of_week_prices[day])
                }

        month_avg = {}
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        for month in range(1, 13):
            if month in month_prices and month_prices[month]:
                month_avg[month_names[month - 1]] = {
                    "avg_price": round(statistics.mean(month_prices[month]), 2),
                    "data_points": len(month_prices[month])
                }

        # Find best days/months to buy
        best_day = min(
            day_of_week_avg.items(),
            key=lambda x: x[1]["avg_price"]
        )[0] if day_of_week_avg else None

        best_month = min(
            month_avg.items(),
            key=lambda x: x[1]["avg_price"]
        )[0] if month_avg else None

        return {
            "product": self._product_summary(product),
            "analysis_period_months": months,
            "day_of_week_patterns": day_of_week_avg,
            "monthly_patterns": month_avg,
            "recommendations": {
                "best_day_to_buy": best_day,
                "best_month_to_buy": best_month
            }
        }

    def compare_historical_performance(
        self,
        competitor_name: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Analyze a competitor's pricing performance over time

        Shows:
        - Average price relative to market
        - Price stability/volatility
        - Win rate (how often they had lowest price)
        - Price change frequency
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all matches for this competitor
        matches = self.db.query(CompetitorMatch).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id,
            func.lower(CompetitorMatch.competitor_name) == competitor_name.lower()
        ).all()
        history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=cutoff_date,
        )

        if not matches:
            return {"error": "Competitor not found"}

        product_ids = sorted({match.monitored_product_id for match in matches})
        sibling_matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id.in_(product_ids or [-1])
        ).all()
        sibling_history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in sibling_matches],
            since=cutoff_date - timedelta(hours=1),
        )
        sibling_history_by_product: Dict[int, List[PriceHistory]] = defaultdict(list)
        for sibling_match in sibling_matches:
            sibling_history_by_product[sibling_match.monitored_product_id].extend(
                sibling_history_by_match.get(sibling_match.id, [])
            )
        product_titles = {
            product.id: product.title
            for product in self.db.query(ProductMonitored).filter(
                ProductMonitored.id.in_(product_ids or [-1])
            ).all()
        }

        performance_data = []
        total_win_count = 0
        total_checks = 0

        for match in matches:
            history = history_by_match.get(match.id, [])

            if not history:
                continue

            prices = [float(h.price) for h in history if h.price > 0]

            if not prices:
                continue

            # Check if this competitor had lowest price
            for h in history:
                if h.price > 0:
                    total_checks += 1

                    # Get all competitor prices at this timestamp
                    all_prices = self._get_all_prices_at_time(
                        sibling_history_by_product.get(match.monitored_product_id, []),
                        h.timestamp,
                    )

                    if all_prices and h.price == min(all_prices):
                        total_win_count += 1

            # Calculate statistics for this product
            performance_data.append({
                "product_id": match.monitored_product_id,
                "product_title": product_titles.get(match.monitored_product_id, f"Product {match.monitored_product_id}"),
                "avg_price": round(statistics.mean(prices), 2),
                "price_volatility": round(statistics.stdev(prices), 2) if len(prices) > 1 else 0,
                "price_changes": len(prices) - 1,
                "data_points": len(prices)
            })

        if not performance_data:
            return {
                "competitor_name": competitor_name,
                "message": "No data in selected time range"
            }

        win_rate = (total_win_count / total_checks * 100) if total_checks > 0 else 0

        return {
            "competitor_name": competitor_name,
            "period_days": days,
            "total_products_tracked": len(performance_data),
            "win_rate": round(win_rate, 1),
            "total_price_checks": total_checks,
            "times_had_lowest_price": total_win_count,
            "avg_volatility": round(
                statistics.mean([p["price_volatility"] for p in performance_data]),
                2
            ) if performance_data else 0,
            "product_performance": performance_data[:10]  # Top 10 products
        }

    def get_price_drop_alerts(
        self,
        days: int = 30,
        min_drop_pct: float = 10.0
    ) -> Dict[str, Any]:
        """
        Find significant price drops in recent history

        Useful for:
        - Identifying buying opportunities
        - Detecting competitor sales/promotions
        - Triggering price match strategies
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()
        product_ids = [product.id for product in products]
        product_lookup = {product.id: product for product in products}
        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id.in_(product_ids or [-1])
        ).all()
        first_prices_by_match = fetch_first_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=cutoff_date,
        )
        latest_prices_by_match = fetch_latest_price_history_rows(
            self.db,
            [match.id for match in matches],
        )

        price_drops = []

        for match in matches:
            product = product_lookup.get(match.monitored_product_id)
            first_price = first_prices_by_match.get(match.id)
            latest_price = latest_prices_by_match.get(match.id)

            if not product or not first_price or not latest_price or first_price.price <= 0:
                continue

            drop_pct = (
                (first_price.price - latest_price.price) /
                first_price.price * 100
            )

            if drop_pct >= min_drop_pct:
                price_drops.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "competitor_name": match.competitor_name,
                    "competitor_url": match.competitor_url,
                    "original_price": float(first_price.price),
                    "current_price": float(latest_price.price),
                    "drop_amount": round(first_price.price - latest_price.price, 2),
                    "drop_pct": round(drop_pct, 1),
                    "first_seen": first_price.timestamp.isoformat(),
                    "last_checked": latest_price.timestamp.isoformat()
                })

        # Sort by drop percentage
        price_drops.sort(key=lambda x: x["drop_pct"], reverse=True)

        return {
            "period_days": days,
            "min_drop_threshold": min_drop_pct,
            "total_drops_found": len(price_drops),
            "significant_drops": price_drops[:20]  # Top 20 drops
        }

    def get_trends_summary(self, limit: int = 100) -> Dict[str, Any]:
        """Get high-level trend and forecast signals across the user's catalog."""
        now = datetime.utcnow()
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).limit(limit).all()
        product_ids = [product.id for product in products]

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id.in_(product_ids or [-1])
        ).all()
        matches_by_product: Dict[int, List[CompetitorMatch]] = defaultdict(list)
        for match in matches:
            matches_by_product[match.monitored_product_id].append(match)

        history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=now - timedelta(days=90),
        )

        trends = {"increasing": 0, "decreasing": 0, "stable": 0}
        high_volatility_products = []
        predicted_drops = []

        for product in products:
            competitor_histories_30 = {}
            all_price_points_90 = []

            for match in matches_by_product.get(product.id, []):
                history_90 = history_by_match.get(match.id, [])
                history_30 = [
                    row for row in history_90
                    if row.timestamp >= now - timedelta(days=30)
                ]

                if history_30:
                    competitor_histories_30[match.competitor_name] = [
                        {
                            "timestamp": row.timestamp.isoformat(),
                            "price": float(row.price),
                            "in_stock": row.in_stock,
                        }
                        for row in history_30
                    ]

                for row in history_90:
                    if row.price > 0:
                        all_price_points_90.append({
                            "timestamp": row.timestamp,
                            "price": float(row.price),
                            "competitor": match.competitor_name,
                        })

            if competitor_histories_30:
                trend = self._analyze_trend(competitor_histories_30, 30)
                trends[trend["direction"]] = trends.get(trend["direction"], 0) + 1

                all_prices_30 = [
                    point["price"]
                    for history in competitor_histories_30.values()
                    for point in history
                    if point["price"] > 0
                ]
                if all_prices_30 and self._calculate_volatility(all_prices_30) == "High":
                    high_volatility_products.append({
                        "product_id": product.id,
                        "product_title": product.title,
                        "volatility": "High",
                    })

            if len(all_price_points_90) >= 10:
                forecast = self._simple_forecast(all_price_points_90, 30)
                if forecast["price_change_pct"] < -5:
                    predicted_drops.append({
                        "product_id": product.id,
                        "product_title": product.title,
                        "predicted_drop_pct": forecast["price_change_pct"],
                    })

        predicted_drops.sort(key=lambda x: x["predicted_drop_pct"])

        return {
            "total_products_analyzed": len(products),
            "trend_distribution": trends,
            "high_volatility_products": high_volatility_products[:10],
            "predicted_price_drops": predicted_drops[:10],
            "summary": {
                "market_trend": max(trends, key=trends.get) if products else "stable",
                "volatile_products_count": len(high_volatility_products),
                "predicted_drops_count": len(predicted_drops),
            },
        }

    def get_best_time_to_buy_insights(
        self,
        limit: int = 50,
        months: int = 12,
    ) -> Dict[str, Any]:
        """Aggregate day/month buying recommendations across the catalog."""
        cutoff_date = datetime.utcnow() - timedelta(days=months * 30)
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).limit(limit).all()
        product_ids = [product.id for product in products]

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id.in_(product_ids or [-1])
        ).all()
        matches_by_product: Dict[int, List[CompetitorMatch]] = defaultdict(list)
        for match in matches:
            matches_by_product[match.monitored_product_id].append(match)

        history_by_match = fetch_price_history_rows(
            self.db,
            [match.id for match in matches],
            since=cutoff_date,
        )

        day_recommendations = defaultdict(int)
        month_recommendations = defaultdict(int)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        for product in products:
            day_of_week_prices = defaultdict(list)
            month_prices = defaultdict(list)

            for match in matches_by_product.get(product.id, []):
                for row in history_by_match.get(match.id, []):
                    if row.price <= 0:
                        continue
                    day_of_week_prices[row.timestamp.weekday()].append(float(row.price))
                    month_prices[row.timestamp.month].append(float(row.price))

            if day_of_week_prices:
                best_day_index = min(
                    day_of_week_prices.items(),
                    key=lambda item: statistics.mean(item[1]),
                )[0]
                day_recommendations[day_names[best_day_index]] += 1

            if month_prices:
                best_month_index = min(
                    month_prices.items(),
                    key=lambda item: statistics.mean(item[1]),
                )[0]
                month_recommendations[month_names[best_month_index - 1]] += 1

        best_day = max(day_recommendations.items(), key=lambda item: item[1])[0] if day_recommendations else None
        best_month = max(month_recommendations.items(), key=lambda item: item[1])[0] if month_recommendations else None

        return {
            "products_analyzed": len(products),
            "overall_recommendations": {
                "best_day_to_buy": best_day,
                "best_month_to_buy": best_month,
            },
            "day_distribution": dict(day_recommendations),
            "month_distribution": dict(month_recommendations),
            "insights": [
                f"Most products have lowest prices on {best_day}" if best_day else None,
                f"Prices tend to be lowest in {best_month}" if best_month else None,
                "Patterns detected across your catalog",
            ],
        }

    # Helper methods

    def _product_summary(self, product: ProductMonitored) -> Dict[str, Any]:
        """Create a summary dict for a product"""
        return {
            "id": product.id,
            "title": product.title,
            "brand": product.brand,
            "sku": product.sku
        }

    def _calculate_volatility(self, prices: List[float]) -> str:
        """Categorize price volatility"""
        if len(prices) < 2:
            return "Unknown"

        std_dev = statistics.stdev(prices)
        mean_price = statistics.mean(prices)

        coefficient_of_variation = (std_dev / mean_price) * 100

        if coefficient_of_variation < 5:
            return "Low"
        elif coefficient_of_variation < 15:
            return "Medium"
        else:
            return "High"

    def _analyze_trend(
        self,
        competitor_histories: Dict[str, List[Dict]],
        days: int
    ) -> Dict[str, Any]:
        """Analyze overall price trend"""
        # Collect all prices chronologically
        all_points = []

        for histories in competitor_histories.values():
            all_points.extend(histories)

        # Sort by timestamp
        all_points.sort(key=lambda x: x["timestamp"])

        if len(all_points) < 2:
            return {"direction": "stable", "change_pct": 0}

        # Compare first week vs last week averages
        week_in_seconds = 7 * 24 * 60 * 60
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        start_week = now - timedelta(days=days)
        start_week_end = start_week + timedelta(days=7)

        first_week_prices = [
            p["price"] for p in all_points
            if start_week <= datetime.fromisoformat(p["timestamp"]) <= start_week_end
        ]

        last_week_prices = [
            p["price"] for p in all_points
            if datetime.fromisoformat(p["timestamp"]) >= week_ago
        ]

        if not first_week_prices or not last_week_prices:
            return {"direction": "stable", "change_pct": 0}

        first_avg = statistics.mean(first_week_prices)
        last_avg = statistics.mean(last_week_prices)

        change_pct = ((last_avg - first_avg) / first_avg) * 100

        direction = "stable"
        if change_pct > 5:
            direction = "increasing"
        elif change_pct < -5:
            direction = "decreasing"

        return {
            "direction": direction,
            "change_pct": round(change_pct, 2),
            "first_week_avg": round(first_avg, 2),
            "last_week_avg": round(last_avg, 2)
        }

    def _find_best_buying_times(
        self,
        competitor_histories: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """Find periods when prices were historically lowest"""
        # Collect all prices with timestamps
        all_points = []

        for competitor, histories in competitor_histories.items():
            for h in histories:
                all_points.append({
                    "timestamp": datetime.fromisoformat(h["timestamp"]),
                    "price": h["price"],
                    "competitor": competitor
                })

        # Sort by price
        all_points.sort(key=lambda x: x["price"])

        # Get bottom 10% of prices
        bottom_count = max(1, len(all_points) // 10)
        best_deals = all_points[:bottom_count]

        # Group by month
        monthly_deals = defaultdict(int)
        for deal in best_deals:
            month_key = deal["timestamp"].strftime("%Y-%m")
            monthly_deals[month_key] += 1

        # Find months with most deals
        best_months = sorted(
            monthly_deals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return [
            {
                "period": month,
                "deal_count": count,
                "insight": f"Historically {count} of lowest prices occurred in {month}"
            }
            for month, count in best_months
        ]

    def _simple_forecast(
        self,
        price_points: List[Dict],
        days_ahead: int
    ) -> Dict[str, Any]:
        """Simple linear regression forecast"""
        # Convert timestamps to days from start
        start_time = price_points[0]["timestamp"]

        x_values = []
        y_values = []

        for point in price_points:
            days_diff = (point["timestamp"] - start_time).days
            x_values.append(days_diff)
            y_values.append(point["price"])

        # Calculate linear regression (y = mx + b)
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x_squared = sum(x ** 2 for x in x_values)

        # Slope (m)
        denominator = n * sum_x_squared - sum_x ** 2
        if denominator == 0:
            m = 0  # No trend when all data points are at the same timestamp
        else:
            m = (n * sum_xy - sum_x * sum_y) / denominator

        # Intercept (b)
        b = (sum_y - m * sum_x) / n

        # Predict future price
        last_day = x_values[-1]
        future_day = last_day + days_ahead
        predicted_price = max(0, m * future_day + b)  # Clamp to non-negative

        current_price = price_points[-1]["price"]
        price_change = predicted_price - current_price
        price_change_pct = (price_change / current_price * 100) if current_price != 0 else 0

        # Generate forecast points
        forecast_points = []
        for day in range(last_day + 1, future_day + 1, max(1, days_ahead // 10)):
            forecast_points.append({
                "days_from_now": day - last_day,
                "predicted_price": round(m * day + b, 2)
            })

        return {
            "predicted_price": round(predicted_price, 2),
            "price_change": round(price_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "trend_direction": "increasing" if m > 0 else "decreasing" if m < 0 else "stable",
            "slope": round(m, 4),
            "forecast_points": forecast_points
        }

    def _calculate_confidence_intervals(
        self,
        price_points: List[Dict],
        forecast: Dict
    ) -> Dict[str, Any]:
        """Calculate confidence intervals for forecast"""
        prices = [p["price"] for p in price_points]
        std_dev = statistics.stdev(prices) if len(prices) > 1 else 0

        predicted = forecast["predicted_price"]

        # Simple confidence intervals (68-95-99.7 rule)
        return {
            "level": "68%",
            "lower_bound": round(predicted - std_dev, 2),
            "upper_bound": round(predicted + std_dev, 2),
            "note": "68% confidence that actual price will be within these bounds"
        }

    def _get_all_prices_at_time(
        self,
        history_rows: List[PriceHistory],
        timestamp: datetime
    ) -> List[float]:
        """Get all competitor prices at a specific time"""
        time_window = timedelta(hours=1)
        return [
            float(row.price)
            for row in history_rows
            if row.price > 0 and timestamp - time_window <= row.timestamp <= timestamp + time_window
        ]


def get_forecasting_service(db: Session, user: User) -> ForecastingService:
    """Factory function for ForecastingService"""
    return ForecastingService(db, user)
