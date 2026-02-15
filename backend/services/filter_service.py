"""
Filter Service
Advanced filtering and search for products
"""

from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory, User
)


class FilterService:
    """
    Service for advanced product filtering and search
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def apply_filters(
        self,
        filters: Dict[str, Any],
        base_query: Optional[Query] = None
    ) -> Query:
        """
        Apply multiple filters to product query

        Supported filters:
        - price_position: "cheapest", "most_expensive", "mid_range"
        - competition_level: "high", "medium", "low", "none"
        - activity: "price_dropped", "new_competitor", "out_of_stock", "trending"
        - opportunity_score: {"min": 0, "max": 100}
        - price_range: {"min": 0, "max": 1000}
        - brand: "string"
        - sku: "string"
        - date_added: {"from": "2024-01-01", "to": "2024-12-31"}
        - has_alerts: true/false
        - search: "fuzzy search term"
        """
        if base_query is None:
            query = self.db.query(ProductMonitored).filter(
                ProductMonitored.user_id == self.user.id
            )
        else:
            query = base_query

        # Price Position Filter
        if "price_position" in filters:
            query = self._filter_by_price_position(query, filters["price_position"])

        # Competition Level Filter
        if "competition_level" in filters:
            query = self._filter_by_competition(query, filters["competition_level"])

        # Activity Filter
        if "activity" in filters:
            query = self._filter_by_activity(query, filters["activity"])

        # Opportunity Score Filter
        if "opportunity_score" in filters:
            query = self._filter_by_opportunity_score(
                query,
                filters["opportunity_score"].get("min", 0),
                filters["opportunity_score"].get("max", 100)
            )

        # Price Range Filter
        if "price_range" in filters:
            query = self._filter_by_price_range(
                query,
                filters["price_range"].get("min"),
                filters["price_range"].get("max")
            )

        # Brand Filter
        if "brand" in filters and filters["brand"]:
            query = query.filter(
                func.lower(ProductMonitored.brand).like(f"%{filters['brand'].lower()}%")
            )

        # SKU Filter
        if "sku" in filters and filters["sku"]:
            query = query.filter(
                func.lower(ProductMonitored.sku).like(f"%{filters['sku'].lower()}%")
            )

        # Date Added Filter
        if "date_added" in filters:
            date_filter = filters["date_added"]
            if "from" in date_filter:
                query = query.filter(ProductMonitored.created_at >= date_filter["from"])
            if "to" in date_filter:
                query = query.filter(ProductMonitored.created_at <= date_filter["to"])

        # Has Alerts Filter
        if "has_alerts" in filters:
            if filters["has_alerts"]:
                query = query.filter(ProductMonitored.alerts.any())
            else:
                query = query.filter(~ProductMonitored.alerts.any())

        # Search (fuzzy)
        if "search" in filters and filters["search"]:
            search_term = filters["search"].lower()
            query = query.filter(
                or_(
                    func.lower(ProductMonitored.title).like(f"%{search_term}%"),
                    func.lower(ProductMonitored.brand).like(f"%{search_term}%"),
                    func.lower(ProductMonitored.sku).like(f"%{search_term}%")
                )
            )

        return query

    def _filter_by_price_position(self, query: Query, position: str) -> Query:
        """Filter by price position (cheapest, most_expensive, mid_range)"""
        # This would need complex subqueries to compare prices
        # For now, return as-is (TODO: implement price comparison logic)
        return query

    def _filter_by_competition(self, query: Query, level: str) -> Query:
        """Filter by competition level"""
        if level == "none":
            # No competitors
            query = query.filter(
                ~ProductMonitored.competitor_matches.any()
            )
        elif level == "low":
            # 1-2 competitors
            # This requires a subquery to count matches
            pass  # TODO: Implement with subquery
        elif level == "medium":
            # 3-5 competitors
            pass  # TODO: Implement with subquery
        elif level == "high":
            # 6+ competitors
            pass  # TODO: Implement with subquery

        return query

    def _filter_by_activity(self, query: Query, activity: str) -> Query:
        """Filter by recent activity"""
        week_ago = datetime.utcnow() - timedelta(days=7)

        if activity == "price_dropped":
            # Products with price drops in last 7 days
            # Requires price history analysis
            pass  # TODO: Implement

        elif activity == "new_competitor":
            # Products with new competitors in last 7 days
            query = query.filter(
                ProductMonitored.competitor_matches.any(
                    CompetitorMatch.created_at >= week_ago
                )
            )

        elif activity == "out_of_stock":
            # Products where competitors are out of stock
            pass  # TODO: Implement

        elif activity == "trending":
            # Products with high price change frequency
            pass  # TODO: Implement

        return query

    def _filter_by_opportunity_score(
        self,
        query: Query,
        min_score: int,
        max_score: int
    ) -> Query:
        """Filter by opportunity score range"""
        # Would need to calculate scores for all products
        # Or store scores in database
        # For now, return as-is
        return query

    def _filter_by_price_range(
        self,
        query: Query,
        min_price: Optional[float],
        max_price: Optional[float]
    ) -> Query:
        """Filter by price range (based on competitor prices)"""
        # Would need to join with price history and calculate ranges
        # For now, return as-is
        return query

    def search_products(self, search_term: str, limit: int = 50) -> List[ProductMonitored]:
        """
        Fuzzy search across products

        Searches in: title, brand, SKU
        Returns ranked results
        """
        search_lower = search_term.lower()

        # Exact matches first, then partial matches
        exact_matches = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id,
            or_(
                func.lower(ProductMonitored.title) == search_lower,
                func.lower(ProductMonitored.sku) == search_lower
            )
        ).all()

        partial_matches = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id,
            or_(
                func.lower(ProductMonitored.title).like(f"%{search_lower}%"),
                func.lower(ProductMonitored.brand).like(f"%{search_lower}%"),
                func.lower(ProductMonitored.sku).like(f"%{search_lower}%")
            )
        ).filter(
            ~ProductMonitored.id.in_([p.id for p in exact_matches])
        ).limit(limit - len(exact_matches)).all()

        return exact_matches + partial_matches

    def get_filter_options(self) -> Dict[str, Any]:
        """
        Get available filter options based on user's data

        Returns counts and available values for filters
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        # Get unique brands
        brands = list(set([p.brand for p in products if p.brand]))

        # Count by competition level
        competition_counts = {
            "none": 0,
            "low": 0,
            "medium": 0,
            "high": 0
        }

        for product in products:
            comp_count = len(product.competitor_matches)
            if comp_count == 0:
                competition_counts["none"] += 1
            elif comp_count <= 2:
                competition_counts["low"] += 1
            elif comp_count <= 5:
                competition_counts["medium"] += 1
            else:
                competition_counts["high"] += 1

        # Recent activity counts
        week_ago = datetime.utcnow() - timedelta(days=7)
        activity_counts = {
            "new_competitor": 0,
            "price_dropped": 0,
            "out_of_stock": 0,
            "trending": 0
        }

        for product in products:
            # New competitors
            new_comps = [m for m in product.competitor_matches if m.created_at >= week_ago]
            if new_comps:
                activity_counts["new_competitor"] += 1

        return {
            "brands": sorted(brands),
            "total_products": len(products),
            "competition_levels": competition_counts,
            "recent_activity": activity_counts,
            "date_range": {
                "earliest": min([p.created_at for p in products]) if products else None,
                "latest": max([p.created_at for p in products]) if products else None
            }
        }


def get_filter_service(db: Session, user: User) -> FilterService:
    """Factory function for FilterService"""
    return FilterService(db, user)
