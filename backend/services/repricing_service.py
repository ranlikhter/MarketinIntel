"""
Repricing Service
Automated pricing and bulk price management
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import hmac
import hashlib
import os
import secrets

from database.models import (
    ProductMonitored, CompetitorMatch, PriceHistory,
    RepricingRule, User, CategoryPricingProfile, PendingPriceChange
)
from services.activity_service import log_activity

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
        """Apply min/max/MAP and margin floor constraints to suggested prices."""
        # Batch-fetch products once so we can compute per-product floor prices
        product_ids = [s["product_id"] for s in suggestions if "product_id" in s]
        products: Dict[int, ProductMonitored] = {}
        if product_ids:
            products = {
                p.id: p for p in
                self.db.query(ProductMonitored).filter(ProductMonitored.id.in_(product_ids)).all()
            }

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

            # Apply margin floor (per-product)
            product = products.get(suggestion.get("product_id"))
            if product is not None:
                floor = self.compute_floor_price(product)
                if floor is not None and suggestion["suggested_price"] < floor:
                    if getattr(product, "margin_autopilot", False):
                        # Autopilot ON: pause and require approval instead of auto-applying
                        self.create_pending_change(
                            product, floor, reason="margin_floor_breach"
                        )
                        suggestion["skipped"] = True
                        suggestion["floor_breach"] = True
                    else:
                        # Autopilot OFF: silently clamp to floor and log
                        suggestion["suggested_price"] = floor
                        suggestion["floor_enforced"] = True
                        log_activity(
                            self.db, self.user.id,
                            "repricing.floor_enforced", "product",
                            f"Margin floor enforced for '{product.title}'",
                            entity_type="product", entity_id=product.id,
                            entity_name=product.title,
                            metadata={
                                "floor_price": floor,
                                "original_suggested": original_price,
                                "final_price": floor,
                            },
                            workspace_id=getattr(product, "workspace_id", None),
                        )
                    suggestion["constraint_applied"] = "margin_floor"

            # Track if constrained
            if suggestion["suggested_price"] != original_price and "original_suggested" not in suggestion:
                suggestion["original_suggested"] = original_price

        return suggestions


    def compute_floor_price(self, product: ProductMonitored) -> Optional[float]:
        """Compute the minimum price we should ever suggest for a product.

        Priority order:
        1. product.cost_price + product.target_margin_pct (most specific)
        2. CategoryPricingProfile for this product's category
        3. product.min_price / product.map_price constraints
        Returns None when no cost data is available at all.
        """
        floor: Optional[float] = None

        cost = product.cost_price
        margin = product.target_margin_pct

        if cost and cost > 0:
            if margin and 0 < margin < 100:
                floor = cost / (1 - margin / 100)
            else:
                floor = cost  # at least break even

        if floor is None and product.category:
            profile = self.db.query(CategoryPricingProfile).filter(
                CategoryPricingProfile.workspace_id == product.workspace_id,
                CategoryPricingProfile.category_name == product.category
            ).first()
            if profile:
                if profile.default_cogs_pct and product.my_price:
                    estimated_cost = (profile.default_cogs_pct / 100) * product.my_price
                    margin_pct = profile.default_target_margin_pct or 0
                    if 0 < margin_pct < 100:
                        floor = estimated_cost / (1 - margin_pct / 100)
                    else:
                        floor = estimated_cost

        hard_floor = max(
            floor or 0,
            product.min_price or 0,
            product.map_price or 0,
        )
        return hard_floor if hard_floor > 0 else None

    def compute_margin_at_price(self, product: ProductMonitored, price: float) -> Optional[float]:
        """Return projected gross margin % at a given price, or None if no cost data."""
        cost = product.cost_price
        if not cost and product.category:
            profile = self.db.query(CategoryPricingProfile).filter(
                CategoryPricingProfile.workspace_id == product.workspace_id,
                CategoryPricingProfile.category_name == product.category
            ).first()
            if profile and profile.default_cogs_pct and product.my_price:
                cost = (profile.default_cogs_pct / 100) * product.my_price
        if cost and price > 0:
            return round((price - cost) / price * 100, 1)
        return None

    def create_pending_change(
        self,
        product: ProductMonitored,
        suggested_price: float,
        reason: str,
        rule_id: Optional[int] = None,
        expires_hours: int = 24,
    ) -> Optional[PendingPriceChange]:
        """Create a PendingPriceChange after floor/MAP validation.

        Returns the new row, or None if suggestion violates floor price.
        Bundles are skipped (is_bundle=True).
        """
        if getattr(product, "is_bundle", False):
            logger.info("Skipping pending change for bundle product %s", product.id)
            return None

        floor = self.compute_floor_price(product)
        if floor and suggested_price < floor:
            logger.info(
                "Suggested price %.2f below floor %.2f for product %s — skipping",
                suggested_price, floor, product.id
            )
            return None

        existing = self.db.query(PendingPriceChange).filter(
            PendingPriceChange.product_id == product.id,
            PendingPriceChange.status == "pending",
        ).first()
        if existing:
            return existing

        margin = self.compute_margin_at_price(product, suggested_price)
        token = _generate_approval_token_raw(0)  # placeholder; update after flush

        pending = PendingPriceChange(
            product_id=product.id,
            workspace_id=product.workspace_id,
            rule_id=rule_id,
            current_price=product.my_price or 0,
            suggested_price=round(suggested_price, 2),
            reason=reason,
            margin_at_suggested=margin,
            approval_token=token,
            rollback_price=product.my_price,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        )
        self.db.add(pending)
        self.db.flush()  # get pending.id

        pending.approval_token = _generate_approval_token_raw(pending.id)
        self.db.commit()
        self.db.refresh(pending)
        return pending


def _generate_approval_token_raw(pending_id: int) -> str:
    secret = os.getenv("JWT_SECRET_KEY", "dev-secret")
    nonce = secrets.token_hex(16)
    payload = f"{pending_id}:{nonce}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_approval_token(token: str, pending_id: int) -> bool:
    """Validate HMAC-signed one-tap approval token."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False
        pid, nonce, sig = parts
        if int(pid) != pending_id:
            return False
        secret = os.getenv("JWT_SECRET_KEY", "dev-secret")
        expected = hmac.new(
            secret.encode(), f"{pid}:{nonce}".encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def get_repricing_service(db: Session, user: User) -> RepricingService:
    """Factory function for RepricingService"""
    return RepricingService(db, user)
