"""
Filter Service
Advanced filtering and search for products
"""

from sqlalchemy.orm import Session, Query
from sqlalchemy import or_, func, select
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from database.models import (
    ProductMonitored, CompetitorMatch, User
)
from services.product_catalog_service import fetch_latest_price_snapshots, fetch_price_history_rows


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

        # Competition Level Filter
        if "competition_level" in filters:
            query = self._filter_by_competition(query, filters["competition_level"])

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

        snapshot = None
        if any(key in filters for key in ("price_position", "activity", "opportunity_score")):
            snapshot = self._build_filter_snapshot(query)

        # Price Position Filter
        if "price_position" in filters:
            query = self._filter_by_price_position(query, filters["price_position"], snapshot=snapshot)

        # Activity Filter
        if "activity" in filters:
            query = self._filter_by_activity(query, filters["activity"], snapshot=snapshot)

        # Opportunity Score Filter
        if "opportunity_score" in filters:
            query = self._filter_by_opportunity_score(
                query,
                filters["opportunity_score"].get("min", 0),
                filters["opportunity_score"].get("max", 100),
                snapshot=snapshot,
            )

        return query

    def _build_filter_snapshot(self, query: Query) -> Dict[str, Any]:
        week_ago = datetime.utcnow() - timedelta(days=7)
        products = query.all()
        product_ids = [product.id for product in products]

        if not product_ids:
            return {
                "products": [],
                "matches_by_product": {},
                "latest_prices_by_match": {},
                "recent_history_by_match": {},
            }

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id.in_(product_ids)
        ).all()

        matches_by_product: Dict[int, List[CompetitorMatch]] = defaultdict(list)
        match_ids = []
        for match in matches:
            matches_by_product[match.monitored_product_id].append(match)
            match_ids.append(match.id)

        return {
            "products": products,
            "matches_by_product": matches_by_product,
            "latest_prices_by_match": fetch_latest_price_snapshots(self.db, match_ids),
            "recent_history_by_match": fetch_price_history_rows(
                self.db,
                match_ids,
                since=week_ago,
            ),
        }

    def _filter_by_price_position(
        self,
        query: Query,
        position: str,
        *,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Query:
        """Filter by price position relative to competitors (cheapest, most_expensive, mid_range)"""
        snapshot = snapshot or self._build_filter_snapshot(query)
        all_products = snapshot["products"]
        matching_ids = []

        for product in all_products:
            if not product.my_price:
                continue

            competitor_prices = []
            for match in snapshot["matches_by_product"].get(product.id, []):
                latest = snapshot["latest_prices_by_match"].get(match.id)
                if latest and latest.in_stock:
                    competitor_prices.append(latest.price)

            if not competitor_prices:
                continue

            min_comp = min(competitor_prices)
            max_comp = max(competitor_prices)
            my = product.my_price

            if position == "cheapest" and my <= min_comp:
                matching_ids.append(product.id)
            elif position == "most_expensive" and my >= max_comp:
                matching_ids.append(product.id)
            elif position == "mid_range" and min_comp < my < max_comp:
                matching_ids.append(product.id)

        return query.filter(ProductMonitored.id.in_(matching_ids))

    def _filter_by_competition(self, query: Query, level: str) -> Query:
        """Filter by competition level using a count subquery"""
        # Subquery: number of competitor matches per product
        match_count_sq = (
            select(
                CompetitorMatch.monitored_product_id,
                func.count(CompetitorMatch.id).label("match_count"),
            )
            .group_by(CompetitorMatch.monitored_product_id)
            .subquery()
        )

        if level == "none":
            query = query.filter(~ProductMonitored.competitor_matches.any())
        elif level == "low":
            query = (
                query
                .join(match_count_sq, ProductMonitored.id == match_count_sq.c.monitored_product_id)
                .filter(match_count_sq.c.match_count.between(1, 2))
            )
        elif level == "medium":
            query = (
                query
                .join(match_count_sq, ProductMonitored.id == match_count_sq.c.monitored_product_id)
                .filter(match_count_sq.c.match_count.between(3, 5))
            )
        elif level == "high":
            query = (
                query
                .join(match_count_sq, ProductMonitored.id == match_count_sq.c.monitored_product_id)
                .filter(match_count_sq.c.match_count >= 6)
            )

        return query

    def _filter_by_activity(
        self,
        query: Query,
        activity: str,
        *,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Query:
        """Filter by recent activity"""
        week_ago = datetime.utcnow() - timedelta(days=7)
        snapshot = snapshot or self._build_filter_snapshot(query)

        if activity == "price_dropped":
            # Products where any competitor dropped price in last 7 days
            matching_ids = []
            for product in snapshot["products"]:
                for match in snapshot["matches_by_product"].get(product.id, []):
                    recent = snapshot["recent_history_by_match"].get(match.id, [])
                    if len(recent) >= 2 and recent[-1].price < recent[0].price:
                        matching_ids.append(product.id)
                        break
            query = query.filter(ProductMonitored.id.in_(matching_ids))

        elif activity == "new_competitor":
            # Products with new competitors in last 7 days
            matching_ids = [
                product.id
                for product in snapshot["products"]
                if any(
                    match.created_at and match.created_at >= week_ago
                    for match in snapshot["matches_by_product"].get(product.id, [])
                )
            ]
            query = query.filter(ProductMonitored.id.in_(matching_ids))

        elif activity == "out_of_stock":
            # Products where any competitor is currently out of stock
            matching_ids = []
            for product in snapshot["products"]:
                for match in snapshot["matches_by_product"].get(product.id, []):
                    latest = snapshot["latest_prices_by_match"].get(match.id)
                    if latest and not latest.in_stock:
                        matching_ids.append(product.id)
                        break
            query = query.filter(ProductMonitored.id.in_(matching_ids))

        elif activity == "trending":
            # Products with 5+ price changes in last 7 days
            matching_ids = []
            for product in snapshot["products"]:
                change_count = sum(
                    len(snapshot["recent_history_by_match"].get(match.id, []))
                    for match in snapshot["matches_by_product"].get(product.id, [])
                )
                if change_count >= 5:
                    matching_ids.append(product.id)
            query = query.filter(ProductMonitored.id.in_(matching_ids))

        return query

    def _filter_by_opportunity_score(
        self,
        query: Query,
        min_score: int,
        max_score: int,
        *,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Query:
        """Filter by opportunity score range (calculated in Python)"""
        from services.insights_service import InsightsService
        insights = InsightsService(self.db, self.user)
        snapshot = snapshot or self._build_filter_snapshot(query)
        all_products = snapshot["products"]
        matching_ids = [
            p.id for p in all_products
            if min_score <= insights.calculate_opportunity_score(p.id) <= max_score
        ]
        return query.filter(ProductMonitored.id.in_(matching_ids))

    def _filter_by_price_range(
        self,
        query: Query,
        min_price: Optional[float],
        max_price: Optional[float]
    ) -> Query:
        """Filter by the user's own price range (my_price field)"""
        if min_price is not None:
            query = query.filter(ProductMonitored.my_price >= min_price)
        if max_price is not None:
            query = query.filter(ProductMonitored.my_price <= max_price)
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
        product_ids = [product.id for product in products]
        match_counts = {
            product_id: count
            for product_id, count in self.db.query(
                CompetitorMatch.monitored_product_id,
                func.count(CompetitorMatch.id),
            ).filter(
                CompetitorMatch.monitored_product_id.in_(product_ids or [-1])
            ).group_by(
                CompetitorMatch.monitored_product_id
            ).all()
        }

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
            comp_count = match_counts.get(product.id, 0)
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
        snapshot = self._build_filter_snapshot(
            self.db.query(ProductMonitored).filter(
                ProductMonitored.id.in_(product_ids or [-1])
            )
        )
        activity_counts = {
            "new_competitor": 0,
            "price_dropped": 0,
            "out_of_stock": 0,
            "trending": 0
        }

        for product in snapshot["products"]:
            matches = snapshot["matches_by_product"].get(product.id, [])
            if any(match.created_at and match.created_at >= week_ago for match in matches):
                activity_counts["new_competitor"] += 1

            if any(
                len(snapshot["recent_history_by_match"].get(match.id, [])) >= 2
                and snapshot["recent_history_by_match"][match.id][-1].price
                < snapshot["recent_history_by_match"][match.id][0].price
                for match in matches
            ):
                activity_counts["price_dropped"] += 1

            if any(
                (latest := snapshot["latest_prices_by_match"].get(match.id)) is not None
                and not latest.in_stock
                for match in matches
            ):
                activity_counts["out_of_stock"] += 1

            if sum(
                len(snapshot["recent_history_by_match"].get(match.id, []))
                for match in matches
            ) >= 5:
                activity_counts["trending"] += 1

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
