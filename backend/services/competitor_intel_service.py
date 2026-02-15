"""
Competitor Intelligence Service
Advanced competitor analysis and profiling
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory,
    CompetitorWebsite, User
)


class CompetitorIntelService:
    """
    Service for analyzing competitor behavior and strategies
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_competitor_profile(self, competitor_name: str) -> Dict[str, Any]:
        """
        Get comprehensive profile for a specific competitor

        Includes:
        - Total products tracked
        - Average pricing vs your prices
        - Price change frequency
        - Stock availability rate
        - Pricing strategy detection
        - Recent activity
        """
        # Get all matches for this competitor
        matches = self.db.query(CompetitorMatch).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id,
            func.lower(CompetitorMatch.competitor_name) == competitor_name.lower()
        ).all()

        if not matches:
            return {
                "error": "Competitor not found",
                "competitor_name": competitor_name
            }

        # Get competitor website info
        competitor_site = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.user_id == self.user.id,
            func.lower(CompetitorWebsite.name) == competitor_name.lower()
        ).first()

        # Basic stats
        total_products = len(matches)

        # Get latest prices for each match
        price_comparisons = []
        total_cheaper = 0
        total_more_expensive = 0
        total_similar = 0

        for match in matches:
            latest_price = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).first()

            if latest_price and latest_price.in_stock:
                # Get your product's price (would come from your system)
                # For now, assume we're comparing to lowest competitor
                price_comparisons.append({
                    "product_id": match.monitored_product_id,
                    "product_title": match.monitored_product.title,
                    "competitor_price": float(latest_price.price),
                    "competitor_url": match.competitor_url
                })

                # Calculate relative pricing
                all_competitor_prices = self._get_all_competitor_prices(match.monitored_product_id)
                if all_competitor_prices:
                    avg_market_price = sum(all_competitor_prices) / len(all_competitor_prices)

                    if latest_price.price < avg_market_price * 0.95:
                        total_cheaper += 1
                    elif latest_price.price > avg_market_price * 1.05:
                        total_more_expensive += 1
                    else:
                        total_similar += 1

        # Price change frequency
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        price_changes = []

        for match in matches:
            changes = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                PriceHistory.timestamp >= thirty_days_ago
            ).count()

            if changes > 1:
                price_changes.append(changes)

        avg_changes_per_product = (
            sum(price_changes) / len(price_changes) if price_changes else 0
        )

        # Stock availability rate
        stock_checks = []
        for match in matches:
            recent_checks = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                PriceHistory.timestamp >= thirty_days_ago
            ).all()

            if recent_checks:
                in_stock_count = sum(1 for p in recent_checks if p.in_stock)
                stock_rate = (in_stock_count / len(recent_checks)) * 100
                stock_checks.append(stock_rate)

        avg_stock_rate = (
            sum(stock_checks) / len(stock_checks) if stock_checks else 0
        )

        # Detect pricing strategy
        pricing_strategy = self._detect_pricing_strategy(
            total_cheaper,
            total_similar,
            total_more_expensive,
            avg_changes_per_product
        )

        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = self._get_recent_activity(competitor_name, week_ago)

        return {
            "competitor_name": competitor_name,
            "competitor_website": competitor_site.website_url if competitor_site else None,
            "total_products_tracked": total_products,
            "pricing_profile": {
                "products_cheaper_than_market": total_cheaper,
                "products_at_market_price": total_similar,
                "products_more_expensive": total_more_expensive,
                "avg_price_changes_per_month": round(avg_changes_per_product, 1),
                "detected_strategy": pricing_strategy
            },
            "availability": {
                "avg_stock_rate": round(avg_stock_rate, 1),
                "status": "High" if avg_stock_rate > 90 else "Medium" if avg_stock_rate > 70 else "Low"
            },
            "recent_activity": recent_activity,
            "product_sample": price_comparisons[:10]  # Top 10 products
        }

    def compare_competitors(
        self,
        competitor_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple competitors side-by-side

        If no names provided, compares all competitors
        """
        # Get all competitors if none specified
        if not competitor_names:
            all_matches = self.db.query(
                CompetitorMatch.competitor_name
            ).join(ProductMonitored).filter(
                ProductMonitored.user_id == self.user.id
            ).distinct().all()

            competitor_names = [match[0] for match in all_matches]

        if not competitor_names:
            return {
                "error": "No competitors found",
                "competitors": []
            }

        # Get profiles for each
        profiles = []
        for name in competitor_names:
            profile = self.get_competitor_profile(name)
            if "error" not in profile:
                profiles.append(profile)

        # Sort by total products tracked
        profiles.sort(
            key=lambda x: x["total_products_tracked"],
            reverse=True
        )

        # Calculate competitive advantages
        market_leader = self._determine_market_leader(profiles)

        return {
            "total_competitors": len(profiles),
            "market_leader": market_leader,
            "competitors": profiles,
            "summary": {
                "most_aggressive_pricer": self._find_most_aggressive(profiles),
                "most_reliable_stock": self._find_most_reliable(profiles),
                "most_dynamic": self._find_most_dynamic(profiles)
            }
        }

    def get_cross_product_comparison(
        self,
        product_id: int
    ) -> Dict[str, Any]:
        """
        Compare all competitors for a single product

        Shows who has best price, stock, shipping, etc.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found"}

        # Get all competitor matches
        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()

        if not matches:
            return {
                "product": {
                    "id": product.id,
                    "title": product.title,
                    "brand": product.brand
                },
                "competitors": [],
                "message": "No competitors found for this product"
            }

        # Get latest price for each competitor
        competitor_data = []

        for match in matches:
            latest_price = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).first()

            if latest_price:
                # Get price history for trend
                price_trend = self._calculate_price_trend(match.id)

                competitor_data.append({
                    "competitor_name": match.competitor_name,
                    "competitor_url": match.competitor_url,
                    "price": float(latest_price.price),
                    "currency": latest_price.currency,
                    "in_stock": latest_price.in_stock,
                    "last_checked": latest_price.timestamp.isoformat(),
                    "price_trend": price_trend,
                    "match_score": match.match_score
                })

        # Sort by price (lowest first)
        competitor_data.sort(key=lambda x: x["price"] if x["in_stock"] else float('inf'))

        # Find best values
        best_price = None
        best_availability = None

        if competitor_data:
            in_stock_competitors = [c for c in competitor_data if c["in_stock"]]

            if in_stock_competitors:
                best_price = in_stock_competitors[0]

            # Find competitor with best availability history
            stock_rates = []
            for comp in competitor_data:
                match = next(m for m in matches if m.competitor_name == comp["competitor_name"])
                rate = self._calculate_stock_rate(match.id)
                stock_rates.append((comp, rate))

            if stock_rates:
                best_availability = max(stock_rates, key=lambda x: x[1])[0]

        return {
            "product": {
                "id": product.id,
                "title": product.title,
                "brand": product.brand,
                "image_url": product.image_url
            },
            "total_competitors": len(competitor_data),
            "price_range": {
                "lowest": min([c["price"] for c in competitor_data if c["in_stock"]], default=None),
                "highest": max([c["price"] for c in competitor_data if c["in_stock"]], default=None),
                "average": (
                    sum([c["price"] for c in competitor_data if c["in_stock"]]) /
                    len([c for c in competitor_data if c["in_stock"]])
                ) if any(c["in_stock"] for c in competitor_data) else None
            },
            "best_deals": {
                "cheapest": best_price,
                "most_reliable": best_availability
            },
            "all_competitors": competitor_data
        }

    def get_pricing_strategies(self) -> Dict[str, Any]:
        """
        Detect and analyze pricing strategies across all competitors

        Identifies:
        - Price leaders (always cheapest)
        - Premium positioners (always expensive)
        - Dynamic pricers (frequent changes)
        - Followers (match market)
        """
        # Get all competitors
        all_matches = self.db.query(
            CompetitorMatch.competitor_name
        ).join(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).distinct().all()

        competitor_names = [match[0] for match in all_matches]

        strategies = {
            "price_leaders": [],
            "premium_players": [],
            "dynamic_pricers": [],
            "market_followers": []
        }

        for name in competitor_names:
            profile = self.get_competitor_profile(name)

            if "error" in profile:
                continue

            pricing = profile["pricing_profile"]
            strategy = pricing["detected_strategy"]

            competitor_summary = {
                "name": name,
                "products_tracked": profile["total_products_tracked"],
                "avg_price_changes": pricing["avg_price_changes_per_month"]
            }

            if strategy == "Aggressive Pricer":
                strategies["price_leaders"].append(competitor_summary)
            elif strategy == "Premium Positioning":
                strategies["premium_players"].append(competitor_summary)
            elif strategy == "Dynamic Pricing":
                strategies["dynamic_pricers"].append(competitor_summary)
            else:
                strategies["market_followers"].append(competitor_summary)

        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "total_competitors_analyzed": len(competitor_names),
            "strategies": strategies,
            "insights": self._generate_strategy_insights(strategies)
        }

    def get_market_positioning(self) -> Dict[str, Any]:
        """
        Analyze overall market positioning

        Shows where you stand vs competitors
        """
        # Get all your products
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        if not products:
            return {"error": "No products found"}

        positioning_data = {
            "cheapest": 0,
            "competitive": 0,
            "expensive": 0,
            "no_competition": 0
        }

        product_breakdown = []

        for product in products:
            # Get all competitor prices
            competitor_prices = self._get_all_competitor_prices(product.id)

            if not competitor_prices:
                positioning_data["no_competition"] += 1
                continue

            # For this demo, assume your price is the average
            # In reality, you'd have your actual product price
            your_price = sum(competitor_prices) / len(competitor_prices)
            lowest_competitor = min(competitor_prices)
            highest_competitor = max(competitor_prices)

            if your_price <= lowest_competitor:
                position = "cheapest"
                positioning_data["cheapest"] += 1
            elif your_price >= highest_competitor:
                position = "expensive"
                positioning_data["expensive"] += 1
            else:
                position = "competitive"
                positioning_data["competitive"] += 1

            product_breakdown.append({
                "product_id": product.id,
                "product_title": product.title,
                "your_price": round(your_price, 2),
                "market_low": round(lowest_competitor, 2),
                "market_high": round(highest_competitor, 2),
                "position": position,
                "competitors_count": len(competitor_prices)
            })

        total_with_competition = (
            positioning_data["cheapest"] +
            positioning_data["competitive"] +
            positioning_data["expensive"]
        )

        return {
            "total_products": len(products),
            "positioning_summary": positioning_data,
            "market_share_estimate": {
                "price_leader_products": positioning_data["cheapest"],
                "competitive_products": positioning_data["competitive"],
                "premium_products": positioning_data["expensive"],
                "percentage_competitive": round(
                    (positioning_data["cheapest"] + positioning_data["competitive"]) /
                    total_with_competition * 100, 1
                ) if total_with_competition > 0 else 0
            },
            "product_breakdown": product_breakdown[:20],  # Top 20 products
            "recommendations": self._generate_positioning_recommendations(positioning_data)
        }

    # Helper methods

    def _get_all_competitor_prices(self, product_id: int) -> List[float]:
        """Get all current competitor prices for a product"""
        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()

        prices = []
        for match in matches:
            latest_price = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).first()

            if latest_price and latest_price.in_stock:
                prices.append(float(latest_price.price))

        return prices

    def _detect_pricing_strategy(
        self,
        cheaper: int,
        similar: int,
        expensive: int,
        avg_changes: float
    ) -> str:
        """Detect competitor's pricing strategy based on behavior"""
        total = cheaper + similar + expensive

        if total == 0:
            return "Unknown"

        # High frequency changes = dynamic pricing
        if avg_changes > 10:
            return "Dynamic Pricing"

        # Mostly cheaper = aggressive pricer
        if cheaper / total > 0.6:
            return "Aggressive Pricer"

        # Mostly expensive = premium positioning
        if expensive / total > 0.6:
            return "Premium Positioning"

        # Mostly at market = follower
        return "Market Follower"

    def _get_recent_activity(
        self,
        competitor_name: str,
        since: datetime
    ) -> List[Dict[str, Any]]:
        """Get recent price changes and new products"""
        matches = self.db.query(CompetitorMatch).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id,
            func.lower(CompetitorMatch.competitor_name) == competitor_name.lower()
        ).all()

        activity = []

        for match in matches:
            # Check for price changes
            price_history = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                PriceHistory.timestamp >= since
            ).order_by(PriceHistory.timestamp).all()

            if len(price_history) >= 2:
                for i in range(1, len(price_history)):
                    if price_history[i].price != price_history[i-1].price:
                        activity.append({
                            "type": "price_change",
                            "product_title": match.monitored_product.title,
                            "old_price": float(price_history[i-1].price),
                            "new_price": float(price_history[i].price),
                            "change_pct": round(
                                ((price_history[i].price - price_history[i-1].price) /
                                 price_history[i-1].price * 100), 2
                            ),
                            "timestamp": price_history[i].timestamp.isoformat()
                        })

            # Check if newly added
            if match.created_at >= since:
                activity.append({
                    "type": "new_product",
                    "product_title": match.monitored_product.title,
                    "timestamp": match.created_at.isoformat()
                })

        # Sort by timestamp, most recent first
        activity.sort(
            key=lambda x: x["timestamp"],
            reverse=True
        )

        return activity[:20]  # Return last 20 activities

    def _calculate_price_trend(self, match_id: int) -> str:
        """Calculate if price is trending up, down, or stable"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        prices = self.db.query(PriceHistory).filter(
            PriceHistory.match_id == match_id,
            PriceHistory.timestamp >= thirty_days_ago
        ).order_by(PriceHistory.timestamp).all()

        if len(prices) < 2:
            return "stable"

        first_price = float(prices[0].price)
        last_price = float(prices[-1].price)

        change_pct = ((last_price - first_price) / first_price) * 100

        if change_pct > 5:
            return "increasing"
        elif change_pct < -5:
            return "decreasing"
        else:
            return "stable"

    def _calculate_stock_rate(self, match_id: int) -> float:
        """Calculate stock availability rate over last 30 days"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        checks = self.db.query(PriceHistory).filter(
            PriceHistory.match_id == match_id,
            PriceHistory.timestamp >= thirty_days_ago
        ).all()

        if not checks:
            return 0.0

        in_stock_count = sum(1 for p in checks if p.in_stock)
        return (in_stock_count / len(checks)) * 100

    def _determine_market_leader(self, profiles: List[Dict]) -> Dict[str, Any]:
        """Determine which competitor is the market leader"""
        if not profiles:
            return {}

        # Leader = most products + best pricing position
        leader = max(
            profiles,
            key=lambda p: p["total_products_tracked"]
        )

        return {
            "name": leader["competitor_name"],
            "products_tracked": leader["total_products_tracked"],
            "reason": "Most comprehensive product coverage"
        }

    def _find_most_aggressive(self, profiles: List[Dict]) -> Optional[str]:
        """Find competitor with most aggressive pricing"""
        if not profiles:
            return None

        aggressive = max(
            profiles,
            key=lambda p: p["pricing_profile"]["products_cheaper_than_market"]
        )

        return aggressive["competitor_name"]

    def _find_most_reliable(self, profiles: List[Dict]) -> Optional[str]:
        """Find competitor with best stock availability"""
        if not profiles:
            return None

        reliable = max(
            profiles,
            key=lambda p: p["availability"]["avg_stock_rate"]
        )

        return reliable["competitor_name"]

    def _find_most_dynamic(self, profiles: List[Dict]) -> Optional[str]:
        """Find competitor with most frequent price changes"""
        if not profiles:
            return None

        dynamic = max(
            profiles,
            key=lambda p: p["pricing_profile"]["avg_price_changes_per_month"]
        )

        return dynamic["competitor_name"]

    def _generate_strategy_insights(self, strategies: Dict) -> List[str]:
        """Generate insights from strategy analysis"""
        insights = []

        if strategies["price_leaders"]:
            insights.append(
                f"{len(strategies['price_leaders'])} competitors use aggressive pricing"
            )

        if strategies["dynamic_pricers"]:
            insights.append(
                f"{len(strategies['dynamic_pricers'])} competitors change prices frequently"
            )

        if strategies["premium_players"]:
            insights.append(
                f"{len(strategies['premium_players'])} competitors focus on premium positioning"
            )

        if not insights:
            insights.append("Insufficient data for strategy detection")

        return insights

    def _generate_positioning_recommendations(
        self,
        positioning: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on market positioning"""
        recommendations = []
        total = sum(positioning.values())

        if total == 0:
            return ["Add competitor tracking to get recommendations"]

        expensive_ratio = positioning["expensive"] / total

        if expensive_ratio > 0.5:
            recommendations.append(
                "⚠️ You're priced higher than competitors on 50%+ of products"
            )
            recommendations.append(
                "💡 Consider reviewing pricing strategy or emphasizing value-adds"
            )

        if positioning["cheapest"] > positioning["competitive"] + positioning["expensive"]:
            recommendations.append(
                "✅ Strong price leadership position - monitor margins"
            )

        if positioning["no_competition"] > total * 0.3:
            recommendations.append(
                "🎯 30%+ of products have no competition - opportunity for premium pricing"
            )

        return recommendations


def get_competitor_intel_service(db: Session, user: User) -> CompetitorIntelService:
    """Factory function for CompetitorIntelService"""
    return CompetitorIntelService(db, user)
