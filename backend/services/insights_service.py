"""
Insights Service
Analyzes product and competitor data to provide actionable recommendations
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory,
    PriceAlert, User
)
from services.product_catalog_service import PriceSnapshot, fetch_latest_price_snapshots
from services.workspace_service import build_scope_predicate


class InsightsService:
    """Service for generating actionable insights and recommendations"""

    def __init__(self, db: Session, user: User, workspace_id: int | None = None):
        self.db = db
        self.user = user
        self.workspace_id = workspace_id if workspace_id is not None else getattr(user, "default_workspace_id", None)
        self._snapshot_loaded = False
        self._products: List[ProductMonitored] = []
        self._products_by_id: Dict[int, ProductMonitored] = {}
        self._matches_by_product: Dict[int, List[CompetitorMatch]] = defaultdict(list)
        self._latest_prices_by_match: Dict[int, PriceSnapshot] = {}
        self._historical_prices_by_match: Dict[int, PriceSnapshot] = {}
        self._recent_history_by_match: Dict[int, List[PriceHistory]] = defaultdict(list)
        self._active_alerts_count = 0
        self._recent_price_change_count = 0

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
        products = self._get_user_products()

        total_products = len(products)
        total_matches = sum(len(self._get_product_matches(p.id)) for p in products)

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

        return {
            "total_products": total_products,
            "total_competitors": total_matches,
            "competitive_position": {
                "cheapest": cheapest_count,
                "mid_range": mid_range_count,
                "most_expensive": most_expensive_count,
                "cheapest_pct": round((cheapest_count / total_products * 100) if total_products > 0 else 0, 1)
            },
            "active_alerts": self._active_alerts_count,
            "price_changes_last_week": self._recent_price_change_count,
            "avg_competitors_per_product": round(total_matches / total_products, 1) if total_products > 0 else 0
        }

    def get_trending_products(self) -> List[Dict[str, Any]]:
        """
        Get products with interesting trends (frequent price changes, new competitors, etc.)
        """
        trending = []

        # Products with most price changes in last 7 days
        products = self._get_user_products()

        for product in products[:20]:  # Limit to top 20
            change_count = sum(
                len(self._get_recent_history(match.id))
                for match in self._get_product_matches(product.id)
            )

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
        product = self._get_product_by_id(product_id)

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
        competitor_matches = self._get_product_matches(product.id)
        competitor_count = len(competitor_matches)
        if competitor_count > 5:
            score -= 10
        elif competitor_count < 2:
            score += 10  # Low competition = opportunity

        # Factor 3: Recent price volatility (+15 if volatile)
        changes = sum(
            len(self._get_recent_history(match.id))
            for match in competitor_matches
        )

        if changes >= 5:
            score += 15  # High activity = opportunity

        # Factor 4: Competitors out of stock (+25 bonus)
        out_of_stock = 0
        for m in competitor_matches:
            lp = self._get_latest_price(m.id)
            if lp and not lp.in_stock:
                out_of_stock += 1
        if out_of_stock > 0:
            score += 25

        return max(0, min(100, score))  # Clamp to 0-100

    def _ensure_catalog_snapshot(self) -> None:
        if self._snapshot_loaded:
            return

        week_ago = datetime.utcnow() - timedelta(days=7)
        self._products = self.db.query(ProductMonitored).filter(
            build_scope_predicate(
                ProductMonitored,
                workspace_id=self.workspace_id,
                user_id=self.user.id,
            )
        ).all()
        self._products_by_id = {product.id: product for product in self._products}

        self._active_alerts_count = self.db.query(PriceAlert).filter(
            and_(
                build_scope_predicate(
                    PriceAlert,
                    workspace_id=self.workspace_id,
                    user_id=self.user.id,
                ),
                PriceAlert.enabled == True,
            )
        ).count()

        product_ids = list(self._products_by_id.keys())
        if not product_ids:
            self._snapshot_loaded = True
            return

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id.in_(product_ids)
        ).all()

        match_ids = []
        for match in matches:
            self._matches_by_product[match.monitored_product_id].append(match)
            match_ids.append(match.id)

        if match_ids:
            self._latest_prices_by_match = fetch_latest_price_snapshots(self.db, match_ids)
            self._historical_prices_by_match = fetch_latest_price_snapshots(
                self.db,
                match_ids,
                before=week_ago,
            )
            recent_history_rows = self.db.query(PriceHistory).filter(
                PriceHistory.match_id.in_(match_ids),
                PriceHistory.timestamp >= week_ago,
            ).order_by(
                PriceHistory.match_id.asc(),
                PriceHistory.timestamp.asc(),
            ).all()

            self._recent_price_change_count = len(recent_history_rows)
            for row in recent_history_rows:
                self._recent_history_by_match[row.match_id].append(row)

        self._snapshot_loaded = True

    def _get_user_products(self) -> List[ProductMonitored]:
        self._ensure_catalog_snapshot()
        return self._products

    def _get_product_by_id(self, product_id: int) -> ProductMonitored | None:
        self._ensure_catalog_snapshot()
        return self._products_by_id.get(product_id)

    def _get_product_matches(self, product_id: int) -> List[CompetitorMatch]:
        self._ensure_catalog_snapshot()
        return self._matches_by_product.get(product_id, [])

    def _get_recent_history(self, match_id: int) -> List[PriceHistory]:
        self._ensure_catalog_snapshot()
        return self._recent_history_by_match.get(match_id, [])

    def _get_historical_price(self, match_id: int) -> PriceSnapshot | None:
        self._ensure_catalog_snapshot()
        return self._historical_prices_by_match.get(match_id)

    # Helper methods
    def _get_overpriced_products(self) -> List[Dict[str, Any]]:
        """Get products where user is most expensive"""
        products = self._get_user_products()

        overpriced = []
        for product in products:
            if self._get_price_position(product) == "most_expensive":
                overpriced.append({
                    "product_id": product.id,
                    "title": product.title,
                    "competitor_count": len(self._get_product_matches(product.id))
                })

        return overpriced

    def _get_out_of_stock_opportunities(self) -> List[Dict[str, Any]]:
        """Get products where competitors are out of stock"""
        products = self._get_user_products()

        opportunities = []
        for product in products:
            out_of_stock_count = 0
            matches = self._get_product_matches(product.id)
            for match in matches:
                latest = self._get_latest_price(match.id)
                if latest and not latest.in_stock:
                    out_of_stock_count += 1

            if out_of_stock_count > 0:
                opportunities.append({
                    "product_id": product.id,
                    "title": product.title,
                    "out_of_stock_count": out_of_stock_count,
                    "total_competitors": len(matches)
                })

        return opportunities

    def _detect_price_wars(self) -> List[Dict[str, Any]]:
        """Detect products in active price wars (3+ price drops in 24h)"""
        yesterday = datetime.utcnow() - timedelta(hours=24)
        products = self._get_user_products()

        price_wars = []
        for product in products:
            # Count price drops in last 24h
            drops = 0
            for match in self._get_product_matches(product.id):
                recent_prices = [
                    row for row in self._get_recent_history(match.id)
                    if row.timestamp >= yesterday
                ]

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

        products = self._get_user_products()

        new_comps = []
        for product in products:
            new_matches = [
                match
                for match in self._get_product_matches(product.id)
                if match.created_at and match.created_at >= week_ago
            ]
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

        products = self._get_user_products()

        stale = []
        for product in products:
            # Check last crawl time
            product_matches = self._get_product_matches(product.id)
            if product_matches:
                crawl_times = [m.last_scraped_at for m in product_matches if m.last_scraped_at]
                if not crawl_times:
                    stale.append({
                        "product_id": product.id,
                        "title": product.title,
                        "last_update": None
                    })
                    continue
                last_crawl = max(crawl_times)
                if last_crawl < threshold:
                    stale.append({
                        "product_id": product.id,
                        "title": product.title,
                        "last_update": last_crawl
                    })

        return stale

    def _get_underpriced_products(self) -> List[Dict[str, Any]]:
        """Get products where user is cheapest (could raise price)"""
        products = self._get_user_products()

        underpriced = []
        for product in products:
            if self._get_price_position(product) == "cheapest":
                # Calculate potential gain
                latest_prices = [
                    (match, self._get_latest_price(match.id))
                    for match in self._get_product_matches(product.id)
                ]
                prices = [lp.price for m, lp in latest_prices if lp]
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
        products = self._get_user_products()

        return [
            {
                "product_id": p.id,
                "title": p.title,
                "competitor_count": len(self._get_product_matches(p.id))
            }
            for p in products if len(self._get_product_matches(p.id)) < 3
        ]

    def _get_bundling_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify products where competitors appear to be selling bundles/kits
        while we sell individual items (detected via title keywords).
        """
        bundle_keywords = {"bundle", "kit", "set", "pack", "combo", "collection", "multipack"}
        products = self._get_user_products()

        opportunities = []
        for product in products:
            # Check if any competitor title contains bundle keywords
            bundled_competitors = [
                m.competitor_name
                for m in self._get_product_matches(product.id)
                if m.competitor_product_title and
                any(kw in m.competitor_product_title.lower() for kw in bundle_keywords)
            ]
            if bundled_competitors:
                opportunities.append({
                    "product_id": product.id,
                    "title": product.title,
                    "bundled_by": list(set(bundled_competitors)),
                    "bundle_count": len(bundled_competitors),
                })

        return opportunities

    def _get_aggressive_competitors(self) -> List[Dict[str, Any]]:
        """
        Find competitors who dropped their price 3+ times in the last 7 days
        across any of the user's products.
        """
        products = self._get_user_products()

        competitor_drop_counts: Dict[str, int] = {}

        for product in products:
            for match in self._get_product_matches(product.id):
                prices = self._get_recent_history(match.id)

                drops = sum(
                    1 for i in range(1, len(prices))
                    if prices[i].price < prices[i - 1].price
                )
                if drops:
                    competitor_drop_counts[match.competitor_name] = (
                        competitor_drop_counts.get(match.competitor_name, 0) + drops
                    )

        aggressive = [
            {"competitor_name": name, "price_drops_last_7d": count}
            for name, count in competitor_drop_counts.items()
            if count >= 3
        ]
        return sorted(aggressive, key=lambda x: x["price_drops_last_7d"], reverse=True)

    def _get_declining_price_products(self) -> List[Dict[str, Any]]:
        """
        Find products where the average competitor price declined over the last 7 days.
        """
        products = self._get_user_products()

        declining = []
        for product in products:
            old_prices, new_prices = [], []
            for match in self._get_product_matches(product.id):
                history = [row for row in self._get_recent_history(match.id) if row.in_stock]

                if len(history) >= 2:
                    old_prices.append(history[0].price)
                    new_prices.append(history[-1].price)

            if not old_prices:
                continue

            old_avg = sum(old_prices) / len(old_prices)
            new_avg = sum(new_prices) / len(new_prices)
            trend_pct = ((new_avg - old_avg) / old_avg) * 100 if old_avg else 0

            if trend_pct < -2:  # Declined more than 2 %
                declining.append({
                    "product_id": product.id,
                    "title": product.title,
                    "price_trend_pct": round(trend_pct, 2),
                    "avg_price_now": round(new_avg, 2),
                })

        return sorted(declining, key=lambda x: x["price_trend_pct"])

    def _get_lost_position_products(self) -> List[Dict[str, Any]]:
        """
        Find products where we were cheapest 7 days ago but are no longer the cheapest now.
        Requires my_price to be set on the product.
        """
        products = self._get_user_products()

        lost = []
        for product in products:
            if not product.my_price:
                continue

            # Were we cheapest a week ago?
            old_comp_prices = []
            new_comp_prices = []
            for match in self._get_product_matches(product.id):
                old_ph = self._get_historical_price(match.id)

                new_ph = self._get_latest_price(match.id)

                if old_ph and old_ph.in_stock:
                    old_comp_prices.append(old_ph.price)
                if new_ph and new_ph.in_stock:
                    new_comp_prices.append(new_ph.price)

            if not old_comp_prices or not new_comp_prices:
                continue

            was_cheapest = product.my_price <= min(old_comp_prices)
            is_still_cheapest = product.my_price <= min(new_comp_prices)

            if was_cheapest and not is_still_cheapest:
                lost.append({
                    "product_id": product.id,
                    "title": product.title,
                    "my_price": product.my_price,
                    "cheapest_competitor_now": round(min(new_comp_prices), 2),
                })

        return lost

    def _get_price_position(self, product: ProductMonitored) -> str:
        """Determine if product is cheapest, most expensive, or mid-range"""
        product_matches = self._get_product_matches(product.id)
        if not product_matches:
            return "no_data"

        prices = []
        for match in product_matches:
            latest = self._get_latest_price(match.id)
            if latest and latest.in_stock:
                prices.append(latest.price)

        if not prices:
            return "no_data"

        min_price = min(prices)
        max_price = max(prices)

        # Compare user's own price against competitor prices
        if product.my_price is not None:
            if product.my_price <= min_price:
                return "cheapest"
            elif product.my_price >= max_price:
                return "most_expensive"
            else:
                return "mid_range"

        # Fallback when my_price is not set
        return "mid_range"

    def _get_latest_price(self, match_id: int) -> PriceSnapshot | None:
        """Get the most recent price for a competitor match"""
        self._ensure_catalog_snapshot()
        return self._latest_prices_by_match.get(match_id)


# Singleton-like access
def get_insights_service(
    db: Session,
    user: User,
    workspace_id: int | None = None,
) -> InsightsService:
    """Factory function to get insights service"""
    return InsightsService(db, user, workspace_id=workspace_id)
