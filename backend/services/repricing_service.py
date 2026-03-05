"""
Repricing Service
Automated pricing and bulk price management
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory,
    RepricingRule, User
)

logger = logging.getLogger(__name__)


class RepricingService:
    """
    Service for automated repricing and bulk price actions
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    # Bulk Actions

    def match_lowest_competitor(
        self,
        product_ids: List[int],
        margin_amount: float = 0,
        margin_pct: float = 0
    ) -> Dict[str, Any]:
        """
        Match lowest competitor price with optional margin

        Args:
            product_ids: List of product IDs to reprice
            margin_amount: Stay this much below lowest (e.g., 0.50)
            margin_pct: Stay this percentage below lowest (e.g., 5.0 for 5%)

        Returns:
            Dictionary with suggested price changes
        """
        suggestions = []

        for product_id in product_ids:
            product = self._get_user_product(product_id)
            if not product:
                continue

            lowest_price = self._get_lowest_competitor_price(product)
            if not lowest_price:
                continue

            # Calculate suggested price
            suggested_price = lowest_price
            if margin_amount:
                suggested_price -= margin_amount
            if margin_pct:
                suggested_price -= (lowest_price * (margin_pct / 100))
            suggested_price = max(0.01, suggested_price)  # Never go negative

            suggestions.append({
                "product_id": product.id,
                "product_title": product.title,
                "current_lowest": lowest_price,
                "suggested_price": round(suggested_price, 2),
                "change_amount": None,  # Would need current user price
                "change_pct": None
            })

        return {
            "action": "match_lowest",
            "products_processed": len(suggestions),
            "suggestions": suggestions
        }

    def undercut_all_competitors(
        self,
        product_ids: List[int],
        undercut_amount: Optional[float] = None,
        undercut_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Price below all competitors by fixed amount or percentage

        Args:
            product_ids: List of product IDs to reprice
            undercut_amount: Price this much below lowest (e.g., 1.00)
            undercut_pct: Price this percentage below lowest (e.g., 10.0 for 10%)
        """
        if not undercut_amount and not undercut_pct:
            undercut_amount = 0.50  # Default to $0.50 below

        suggestions = []

        for product_id in product_ids:
            product = self._get_user_product(product_id)
            if not product:
                continue

            lowest_price = self._get_lowest_competitor_price(product)
            if not lowest_price:
                continue

            # Calculate undercut price
            suggested_price = lowest_price
            if undercut_amount:
                suggested_price -= undercut_amount
            if undercut_pct:
                suggested_price -= (lowest_price * (undercut_pct / 100))
            suggested_price = max(0.01, suggested_price)  # Never go negative

            suggestions.append({
                "product_id": product.id,
                "product_title": product.title,
                "lowest_competitor": lowest_price,
                "suggested_price": round(suggested_price, 2),
                "undercut_by": round(lowest_price - suggested_price, 2)
            })

        return {
            "action": "undercut",
            "products_processed": len(suggestions),
            "suggestions": suggestions
        }

    def set_margin_based_pricing(
        self,
        product_ids: List[int],
        cost_price: float,
        margin_pct: float
    ) -> Dict[str, Any]:
        """
        Set price based on cost + margin percentage

        Args:
            product_ids: List of product IDs
            cost_price: Product cost
            margin_pct: Desired profit margin percentage (e.g., 40 for 40%)
        """
        suggestions = []

        for product_id in product_ids:
            product = self._get_user_product(product_id)
            if not product:
                continue

            suggested_price = cost_price * (1 + (margin_pct / 100))

            suggestions.append({
                "product_id": product.id,
                "product_title": product.title,
                "cost": cost_price,
                "margin_pct": margin_pct,
                "suggested_price": round(suggested_price, 2),
                "profit": round(suggested_price - cost_price, 2)
            })

        return {
            "action": "margin_based",
            "products_processed": len(suggestions),
            "suggestions": suggestions
        }

    def apply_dynamic_adjustment(
        self,
        product_ids: List[int],
        conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply dynamic pricing based on multiple factors

        Conditions can include:
        - stock_level: Adjust based on inventory
        - time_of_day: Weekend/holiday pricing
        - competition_count: Adjust based on # of competitors
        - demand: Trending products
        """
        suggestions = []

        for product_id in product_ids:
            product = self._get_user_product(product_id)
            if not product:
                continue

            base_price = self._get_lowest_competitor_price(product)
            if not base_price:
                continue

            adjustment_pct = 0

            # Apply conditions
            if "low_stock_increase" in conditions:
                # Increase price if low stock
                adjustment_pct += conditions["low_stock_increase"]

            if "high_competition_decrease" in conditions:
                comp_count = len(product.competitor_matches)
                if comp_count > 5:
                    adjustment_pct -= conditions["high_competition_decrease"]

            if "weekend_increase" in conditions:
                # Weekend pricing (would check datetime)
                pass

            suggested_price = base_price * (1 + (adjustment_pct / 100))

            suggestions.append({
                "product_id": product.id,
                "product_title": product.title,
                "base_price": base_price,
                "adjustment_pct": adjustment_pct,
                "suggested_price": round(suggested_price, 2)
            })

        return {
            "action": "dynamic",
            "products_processed": len(suggestions),
            "suggestions": suggestions
        }

    def check_map_compliance(
        self,
        product_ids: List[int],
        map_prices: Dict[int, float]
    ) -> Dict[str, Any]:
        """
        Check if suggested prices violate Minimum Advertised Price

        Args:
            product_ids: Products to check
            map_prices: Dict of {product_id: map_price}

        Returns:
            Products that would violate MAP
        """
        violations = []

        for product_id in product_ids:
            if product_id not in map_prices:
                continue

            product = self._get_user_product(product_id)
            if not product:
                continue

            lowest_price = self._get_lowest_competitor_price(product)
            map_price = map_prices[product_id]

            if lowest_price and lowest_price < map_price:
                violations.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "lowest_competitor": lowest_price,
                    "map_price": map_price,
                    "violation_amount": round(map_price - lowest_price, 2),
                    "warning": "Competitor is violating MAP"
                })

        return {
            "violations_found": len(violations),
            "violations": violations
        }

    # Repricing Rules

    def create_repricing_rule(
        self,
        rule_data: Dict[str, Any]
    ) -> RepricingRule:
        """
        Create a new repricing rule

        Args:
            rule_data: {
                "name": "Match Amazon",
                "rule_type": "match_lowest",
                "config": {"margin_amount": 0.5},
                "product_id": 123,  # Optional, null = all products
                "min_price": 10.0,
                "max_price": 100.0,
                "auto_apply": false
            }
        """
        rule = RepricingRule(
            user_id=self.user.id,
            product_id=rule_data.get("product_id"),
            rule_type=rule_data["rule_type"],
            name=rule_data["name"],
            description=rule_data.get("description"),
            config=rule_data["config"],
            min_price=rule_data.get("min_price"),
            max_price=rule_data.get("max_price"),
            map_price=rule_data.get("map_price"),
            priority=rule_data.get("priority", 0),
            auto_apply=rule_data.get("auto_apply", False),
            requires_approval=rule_data.get("requires_approval", True)
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        return rule

    def apply_repricing_rule(
        self,
        rule_id: int,
        product_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Apply a repricing rule to products

        Args:
            rule_id: ID of repricing rule to apply
            product_ids: Optional list of specific products (overrides rule's product_id)

        Returns:
            Suggested price changes
        """
        rule = self.db.query(RepricingRule).filter(
            RepricingRule.id == rule_id,
            RepricingRule.user_id == self.user.id
        ).first()

        if not rule:
            return {"error": "Rule not found"}

        if not rule.enabled:
            return {"error": "Rule is disabled"}

        # Determine which products to apply to
        if product_ids:
            target_products = product_ids
        elif rule.product_id:
            target_products = [rule.product_id]
        else:
            # Apply to all user's products
            all_products = self.db.query(ProductMonitored).filter(
                ProductMonitored.user_id == self.user.id
            ).all()
            target_products = [p.id for p in all_products]

        # Apply rule based on type
        if rule.rule_type == "match_lowest":
            result = self.match_lowest_competitor(
                target_products,
                margin_amount=rule.config.get("margin_amount", 0),
                margin_pct=rule.config.get("margin_pct", 0)
            )
        elif rule.rule_type == "undercut":
            result = self.undercut_all_competitors(
                target_products,
                undercut_amount=rule.config.get("amount"),
                undercut_pct=rule.config.get("percentage")
            )
        elif rule.rule_type == "margin_based":
            result = self.set_margin_based_pricing(
                target_products,
                cost_price=rule.config.get("cost", 0),
                margin_pct=rule.config.get("margin_pct", 0)
            )
        elif rule.rule_type == "dynamic":
            result = self.apply_dynamic_adjustment(
                target_products,
                conditions=rule.config.get("conditions", {})
            )
        else:
            return {"error": f"Unknown rule type: {rule.rule_type}"}

        # Apply constraints
        result["suggestions"] = self._apply_constraints(
            result["suggestions"],
            rule.min_price,
            rule.max_price,
            rule.map_price
        )

        # Update rule stats
        rule.last_applied_at = datetime.utcnow()
        rule.application_count += 1
        self.db.commit()

        return result

    def get_active_rules(self, product_id: Optional[int] = None) -> List[RepricingRule]:
        """Get all active repricing rules for user"""
        query = self.db.query(RepricingRule).filter(
            RepricingRule.user_id == self.user.id,
            RepricingRule.enabled == True
        )

        if product_id:
            query = query.filter(
                (RepricingRule.product_id == product_id) |
                (RepricingRule.product_id == None)  # Global rules
            )

        return query.order_by(desc(RepricingRule.priority)).all()

    # Helper Methods

    def _get_user_product(self, product_id: int) -> Optional[ProductMonitored]:
        """Get product if it belongs to current user"""
        return self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

    def _get_lowest_competitor_price(self, product: ProductMonitored) -> Optional[float]:
        """Get lowest in-stock effective competitor price for product.

        Uses effective_price (price after coupons/Subscribe & Save) when
        available so repricing decisions reflect what customers actually pay,
        not just the listed base price.
        """
        if not product.competitor_matches:
            return None

        prices = []
        for match in product.competitor_matches:
            latest = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(desc(PriceHistory.timestamp)).first()

            if latest and latest.in_stock and latest.price:
                # Prefer effective_price (post-coupon/subscribe-and-save);
                # fall back to the listed base price.
                effective = latest.effective_price or latest.price
                prices.append(effective)

        return min(prices) if prices else None

    def _apply_constraints(
        self,
        suggestions: List[Dict],
        min_price: Optional[float],
        max_price: Optional[float],
        map_price: Optional[float]
    ) -> List[Dict]:
        """Apply min/max/MAP constraints to suggested prices"""
        for suggestion in suggestions:
            original_price = suggestion["suggested_price"]

            # Apply minimum price
            if min_price is not None and suggestion["suggested_price"] < min_price:
                suggestion["suggested_price"] = min_price
                suggestion["constraint_applied"] = "min_price"

            # Apply maximum price
            if max_price is not None and suggestion["suggested_price"] > max_price:
                suggestion["suggested_price"] = max_price
                suggestion["constraint_applied"] = "max_price"

            # Apply MAP
            if map_price is not None and suggestion["suggested_price"] < map_price:
                suggestion["suggested_price"] = map_price
                suggestion["constraint_applied"] = "map_protection"
                suggestion["map_warning"] = f"Price adjusted to MAP: ${map_price}"

            # Track if constrained
            if suggestion["suggested_price"] != original_price:
                suggestion["original_suggested"] = original_price

        return suggestions


def get_repricing_service(db: Session, user: User) -> RepricingService:
    """Factory function for RepricingService"""
    return RepricingService(db, user)
