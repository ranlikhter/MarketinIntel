"""
Insights Service
Analyzes product and competitor data to provide actionable recommendations
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory,
    PriceAlert, User, CompetitorWebsite
)


class InsightsService:
    """Service for generating actionable insights and recommendations"""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_dashboard_insights(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard insights for the user
        Returns priority actions, opportunities, and key metrics
        """
        return {
            "priorities": self.get_today_priorities(),
            "opportunities": self.get_opportunities(),
            "threats": self.get_threats(),
            "key_metrics": self.get_key_metrics(),
            "trending": self.get_trending_products(),
        }

    def get_today_priorities(self) -> List[Dict[str, Any]]:
        """
        Get today's top priority actions the user should take
        """
        priorities = []

        # Priority 1: Products where user is most expensive
        overpriced = self._get_overpriced_products()
        if overpriced:
            priorities.append({
                "type": "price_too_high",
                "severity": "high",
                "title": f"{len(overpriced)} products where you're most expensive",
                "description": "You're losing sales because competitors are cheaper",
                "action": "Lower prices to stay competitive",
                "products": overpriced[:5],
                "count": len(overpriced)
            })

        # Priority 2: Competitors out of stock (opportunity!)
        out_of_stock_opportunities = self._get_out_of_stock_opportunities()
        if out_of_stock_opportunities:
            priorities.append({
                "type": "competitor_out_of_stock",
                "severity": "medium",
                "title": f"{len(out_of_stock_opportunities)} competitors are out of stock",
                "description": "Opportunity to capture sales or raise prices",
                "action": "Consider raising prices temporarily",
                "products": out_of_stock_opportunities[:5],
                "count": len(out_of_stock_opportunities)
            })

        # Priority 3: Price war detected
        price_wars = self._detect_price_wars()
        if price_wars:
            priorities.append({
                "type": "price_war",
                "severity": "high",
                "title": f"{len(price_wars)} products in active price wars",
                "description": "Multiple competitors dropped prices in last 24h",
                "action": "Review and adjust pricing strategy",
                "products": price_wars[:5],
                "count": len(price_wars)
            })

        # Priority 4: New competitors detected
        new_competitors = self._get_new_competitors()
        if new_competitors:
            priorities.append({
                "type": "new_competitors",
                "severity": "medium",
                "title": f"{len(new_competitors)} new competitors found",
                "description": "New sellers are competing for your products",
                "action": "Review their pricing and strategy",
                "products": new_competitors[:5],
                "count": len(new_competitors)
            })

        # Priority 5: Products with no recent data
        stale_products = self._get_stale_products()
        if stale_products:
            priorities.append({
                "type": "stale_data",
                "severity": "low",
                "title": f"{len(stale_products)} products need scraping",
                "description": "Data is older than 48 hours",
                "action": "Trigger a scrape to get fresh data",
                "products": stale_products[:5],
                "count": len(stale_products)
            })

        return sorted(priorities, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])

    def get_opportunities(self) -> List[Dict[str, Any]]:
        """
        Get business opportunities based on market analysis
        """
        opportunities = []

        # Opportunity 1: Products where you're cheapest (can raise price)
        underpriced = self._get_underpriced_products()
        if underpriced:
            opportunities.append({
                "type": "raise_price",
                "title": "You're cheapest on these products",
                "description": f"You could raise prices on {len(underpriced)} products and still be competitive",
                "potential_revenue": sum(p.get("potential_gain", 0) for p in underpriced),
                "products": underpriced[:10]
            })

        # Opportunity 2: High-demand products with few competitors
        low_competition = self._get_low_competition_products()
        if low_competition:
            opportunities.append({
                "type": "pricing_power",
                "title": "Low competition products",
                "description": f"{len(low_competition)} products have limited competition",
                "products": low_competition[:10]
            })

        # Opportunity 3: Bundling opportunities
        bundling_opps = self._get_bundling_opportunities()
        if bundling_opps:
            opportunities.append({
                "type": "bundling",
                "title": "Bundling opportunities",
                "description": "Competitors are bundling products you sell separately",
                "products": bundling_opps[:10]
            })

        return opportunities

    def get_threats(self) -> List[Dict[str, Any]]:
        """
        Get competitive threats and market risks
        """
        threats = []

        # Threat 1: Aggressive competitors
        aggressive = self._get_aggressive_competitors()
        if aggressive:
            threats.append({
                "type": "aggressive_competition",
                "severity": "high",
                "title": "Aggressive price competition",
                "description": f"{len(aggressive)} competitors are consistently undercutting you",
                "competitors": aggressive[:5]
            })

        # Threat 2: Market price declining
        declining_markets = self._get_declining_price_products()
        if declining_markets:
            threats.append({
                "type": "declining_prices",
                "severity": "medium",
                "title": "Market prices are declining",
                "description": f"{len(declining_markets)} products showing downward price trend",
                "products": declining_markets[:10]
            })

        # Threat 3: Lost competitive position
        lost_position = self._get_lost_position_products()
        if lost_position:
            threats.append({
                "type": "lost_position",
                "severity": "high",
                "title": "Lost competitive position",
                "description": "You were cheapest but competitors undercut you",
                "products": lost_position[:10]
            })

        return threats

    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Get key performance metrics
        """
        # Get all user's products
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        total_products = len(products)
        total_matches = sum(len(p.competitor_matches) for p in products)

        # Calculate competitive position
        cheapest_count = 0
        most_expensive_count = 0
        mid_range_count = 0

        for product in products:
            position = self._get_price_position(product)
            if position == "cheapest":
                cheapest_count += 1
            elif position == "most_expensive":
                most_expensive_count += 1
            else:
                mid_range_count += 1

        # Active alerts
        active_alerts = self.db.query(PriceAlert).filter(
            and_(
                PriceAlert.user_id == self.user.id,
                PriceAlert.enabled == True
            )
        ).count()

        # Recent price changes (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_changes = self.db.query(PriceHistory).join(
            CompetitorMatch
        ).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id,
            PriceHistory.timestamp >= week_ago
        ).count()

        return {
            "total_products": total_products,
            "total_competitors": total_matches,
            "competitive_position": {
                "cheapest": cheapest_count,
                "mid_range": mid_range_count,
                "most_expensive": most_expensive_count,
                "cheapest_pct": round((cheapest_count / total_products * 100) if total_products > 0 else 0, 1)
            },
            "active_alerts": active_alerts,
            "price_changes_last_week": recent_changes,
            "avg_competitors_per_product": round(total_matches / total_products, 1) if total_products > 0 else 0
        }

    def get_trending_products(self) -> List[Dict[str, Any]]:
        """
        Get products with interesting trends (frequent price changes, new competitors, etc.)
        """
        trending = []

        # Products with most price changes in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)

        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        for product in products[:20]:  # Limit to top 20
            change_count = self.db.query(PriceHistory).join(
                CompetitorMatch
            ).filter(
                CompetitorMatch.monitored_product_id == product.id,
                PriceHistory.timestamp >= week_ago
            ).count()

            if change_count >= 5:  # Threshold for "trending"
                trending.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "change_count": change_count,
                    "reason": f"{change_count} price changes in last 7 days"
                })

        return sorted(trending, key=lambda x: x["change_count"], reverse=True)[:10]

    def calculate_opportunity_score(self, product_id: int) -> int:
        """
        Calculate opportunity score (0-100) for a product
        Higher score = more opportunity for profit/action
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return 0

        score = 50  # Base score

        # Factor 1: Price position (+20 if cheapest, -20 if most expensive)
        position = self._get_price_position(product)
        if position == "cheapest":
            score += 20  # Opportunity to raise price
        elif position == "most_expensive":
            score -= 20  # Need to lower price

        # Factor 2: Competitor count (-10 for high competition)
        competitor_count = len(product.competitor_matches)
        if competitor_count > 5:
            score -= 10
        elif competitor_count < 2:
            score += 10  # Low competition = opportunity

        # Factor 3: Recent price volatility (+15 if volatile)
        week_ago = datetime.utcnow() - timedelta(days=7)
        changes = self.db.query(PriceHistory).join(
            CompetitorMatch
        ).filter(
            CompetitorMatch.monitored_product_id == product.id,
            PriceHistory.timestamp >= week_ago
        ).count()

        if changes >= 5:
            score += 15  # High activity = opportunity

        # Factor 4: Competitors out of stock (+25 bonus)
        out_of_stock = sum(
            1 for m in product.competitor_matches
            if self._get_latest_price(m.id) and not self._get_latest_price(m.id).in_stock
        )
        if out_of_stock > 0:
            score += 25

        return max(0, min(100, score))  # Clamp to 0-100

    # Helper methods
    def _get_overpriced_products(self) -> List[Dict[str, Any]]:
        """Get products where user is most expensive"""
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        overpriced = []
        for product in products:
            if self._get_price_position(product) == "most_expensive":
                overpriced.append({
                    "product_id": product.id,
                    "title": product.title,
                    "competitor_count": len(product.competitor_matches)
                })

        return overpriced

    def _get_out_of_stock_opportunities(self) -> List[Dict[str, Any]]:
        """Get products where competitors are out of stock"""
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        opportunities = []
        for product in products:
            out_of_stock_count = 0
            for match in product.competitor_matches:
                latest = self._get_latest_price(match.id)
                if latest and not latest.in_stock:
                    out_of_stock_count += 1

            if out_of_stock_count > 0:
                opportunities.append({
                    "product_id": product.id,
                    "title": product.title,
                    "out_of_stock_count": out_of_stock_count,
                    "total_competitors": len(product.competitor_matches)
                })

        return opportunities

    def _detect_price_wars(self) -> List[Dict[str, Any]]:
        """Detect products in active price wars (3+ price drops in 24h)"""
        yesterday = datetime.utcnow() - timedelta(hours=24)
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        price_wars = []
        for product in products:
            # Count price drops in last 24h
            drops = 0
            for match in product.competitor_matches:
                recent_prices = self.db.query(PriceHistory).filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= yesterday
                ).order_by(PriceHistory.timestamp).all()

                # Check for price drops
                for i in range(1, len(recent_prices)):
                    if recent_prices[i].price < recent_prices[i-1].price:
                        drops += 1

            if drops >= 3:
                price_wars.append({
                    "product_id": product.id,
                    "title": product.title,
                    "price_drops": drops
                })

        return price_wars

    def _get_new_competitors(self) -> List[Dict[str, Any]]:
        """Get newly detected competitors (added in last 7 days)"""
        week_ago = datetime.utcnow() - timedelta(days=7)

        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        new_comps = []
        for product in products:
            new_matches = [m for m in product.competitor_matches if m.created_at >= week_ago]
            if new_matches:
                new_comps.append({
                    "product_id": product.id,
                    "title": product.title,
                    "new_competitor_count": len(new_matches)
                })

        return new_comps

    def _get_stale_products(self) -> List[Dict[str, Any]]:
        """Get products with stale data (no updates in 48h)"""
        threshold = datetime.utcnow() - timedelta(hours=48)

        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        stale = []
        for product in products:
            # Check last crawl time
            if product.competitor_matches:
                last_crawl = max(m.last_crawled_at for m in product.competitor_matches if m.last_crawled_at)
                if last_crawl < threshold:
                    stale.append({
                        "product_id": product.id,
                        "title": product.title,
                        "last_update": last_crawl
                    })

        return stale

    def _get_underpriced_products(self) -> List[Dict[str, Any]]:
        """Get products where user is cheapest (could raise price)"""
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        underpriced = []
        for product in products:
            if self._get_price_position(product) == "cheapest":
                # Calculate potential gain
                prices = [self._get_latest_price(m.id).price for m in product.competitor_matches
                         if self._get_latest_price(m.id)]
                if prices:
                    second_lowest = sorted(prices)[1] if len(prices) > 1 else prices[0]
                    # Assume current price is in prices (simplified)
                    potential_gain = second_lowest - min(prices) if len(prices) > 1 else 0

                    underpriced.append({
                        "product_id": product.id,
                        "title": product.title,
                        "potential_gain": potential_gain
                    })

        return underpriced

    def _get_low_competition_products(self) -> List[Dict[str, Any]]:
        """Get products with few competitors (< 3)"""
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        return [
            {
                "product_id": p.id,
                "title": p.title,
                "competitor_count": len(p.competitor_matches)
            }
            for p in products if len(p.competitor_matches) < 3
        ]

    def _get_bundling_opportunities(self) -> List[Dict[str, Any]]:
        """Identify bundling opportunities (placeholder - needs more complex logic)"""
        # TODO: Implement bundle detection logic
        return []

    def _get_aggressive_competitors(self) -> List[Dict[str, Any]]:
        """Get competitors who consistently undercut"""
        # TODO: Implement aggressive competitor detection
        return []

    def _get_declining_price_products(self) -> List[Dict[str, Any]]:
        """Get products with declining price trends"""
        # TODO: Implement trend analysis
        return []

    def _get_lost_position_products(self) -> List[Dict[str, Any]]:
        """Get products where we lost competitive position"""
        # TODO: Implement position tracking
        return []

    def _get_price_position(self, product: ProductMonitored) -> str:
        """Determine if product is cheapest, most expensive, or mid-range"""
        if not product.competitor_matches:
            return "no_data"

        prices = []
        for match in product.competitor_matches:
            latest = self._get_latest_price(match.id)
            if latest and latest.in_stock:
                prices.append(latest.price)

        if not prices:
            return "no_data"

        # Simplified - assumes user has a price (would need user's actual price in real implementation)
        min_price = min(prices)
        max_price = max(prices)

        # This is a placeholder - in reality you'd compare user's price
        if len(prices) == 1:
            return "mid_range"

        # Return based on price distribution
        return "cheapest" if prices[0] == min_price else "most_expensive" if prices[0] == max_price else "mid_range"

    def _get_latest_price(self, match_id: int) -> PriceHistory:
        """Get the most recent price for a competitor match"""
        return self.db.query(PriceHistory).filter(
            PriceHistory.match_id == match_id
        ).order_by(desc(PriceHistory.timestamp)).first()


# Singleton-like access
def get_insights_service(db: Session, user: User) -> InsightsService:
    """Factory function to get insights service"""
    return InsightsService(db, user)
