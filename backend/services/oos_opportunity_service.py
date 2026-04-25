"""
Out-of-Stock Opportunity Service

Detects when competitor products go out of stock and surfaces a price-raise
opportunity for the user. If the product has oos_response_enabled=True and
margin_autopilot=True, the price is raised automatically and reverted when
the competitor restocks.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.models import (
    CompetitorMatch,
    MyPriceHistory,
    PriceHistory,
    ProductMonitored,
    StockOpportunity,
)

logger = logging.getLogger(__name__)

_DEFAULT_RAISE_PCT = 10.0  # % to raise when no product-specific value is set
_MAX_RAISE_PCT = 25.0       # cap — never suggest more than 25% above current price


class OosOpportunityService:
    def __init__(self, db: Session):
        self.db = db

    # ── Public entry point ────────────────────────────────────────────────────

    def check_match_for_oos_transition(
        self,
        match: CompetitorMatch,
        product: ProductMonitored,
    ) -> None:
        """Called after each scrape. Detects in-stock → OOS and OOS → in-stock."""
        last_two = (
            self.db.query(PriceHistory)
            .filter(PriceHistory.match_id == match.id)
            .order_by(desc(PriceHistory.timestamp))
            .limit(2)
            .all()
        )

        if len(last_two) < 2:
            return

        latest, previous = last_two[0], last_two[1]

        if previous.in_stock and not latest.in_stock:
            self._on_competitor_went_oos(match, product)
        elif not previous.in_stock and latest.in_stock:
            self._on_competitor_restocked(match, product)

    # ── Transition handlers ───────────────────────────────────────────────────

    def _on_competitor_went_oos(
        self,
        match: CompetitorMatch,
        product: ProductMonitored,
    ) -> None:
        # If an open opportunity already exists, just add this match to it.
        existing = (
            self.db.query(StockOpportunity)
            .filter(
                StockOpportunity.product_id == product.id,
                StockOpportunity.status == "open",
            )
            .first()
        )

        if existing:
            ids = list(existing.oos_match_ids or [])
            if match.id not in ids:
                existing.oos_match_ids = ids + [match.id]
                existing.oos_competitor_count = len(existing.oos_match_ids)
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()
            return

        current_price = product.my_price or 0.0
        raise_pct = min(
            float(product.oos_price_raise_pct or _DEFAULT_RAISE_PCT),
            _MAX_RAISE_PCT,
        )
        suggested_price = round(current_price * (1 + raise_pct / 100), 2)

        # Don't suggest below the margin floor.
        floor = self._compute_floor(product)
        if floor and suggested_price < floor:
            suggested_price = round(floor, 2)

        opp = StockOpportunity(
            product_id=product.id,
            workspace_id=product.workspace_id,
            oos_match_ids=[match.id],
            oos_competitor_count=1,
            price_before=current_price,
            price_suggested=suggested_price,
            raise_pct=raise_pct,
            revenue_captured_estimate=round(suggested_price - current_price, 2) if current_price else None,
        )
        self.db.add(opp)

        auto_apply = (
            bool(getattr(product, "oos_response_enabled", False))
            and bool(getattr(product, "margin_autopilot", False))
            and current_price > 0
            and suggested_price > current_price
        )

        if auto_apply:
            product.my_price = suggested_price
            self.db.add(MyPriceHistory(
                product_id=product.id,
                workspace_id=product.workspace_id,
                old_price=current_price,
                new_price=suggested_price,
                note=f"OOS autopilot: {match.competitor_name or 'competitor'} went out of stock",
            ))
            opp.status = "applied"
            opp.price_applied = suggested_price

        try:
            self.db.commit()
            logger.info(
                "OOS opportunity %s for product %d (match %d, +%.1f%%)",
                opp.status, product.id, match.id, raise_pct,
            )
        except Exception:
            self.db.rollback()
            logger.exception("Failed to record OOS opportunity for product %d", product.id)

    def _on_competitor_restocked(
        self,
        match: CompetitorMatch,
        product: ProductMonitored,
    ) -> None:
        existing = (
            self.db.query(StockOpportunity)
            .filter(
                StockOpportunity.product_id == product.id,
                StockOpportunity.status.in_(["open", "applied"]),
            )
            .first()
        )

        if not existing:
            return

        ids = list(existing.oos_match_ids or [])
        if match.id in ids:
            ids.remove(match.id)
        existing.oos_match_ids = ids
        existing.oos_competitor_count = max(len(ids), 0)

        if existing.oos_competitor_count == 0:
            was_applied = existing.price_applied is not None
            existing.status = "closed"
            existing.closed_at = datetime.utcnow()

            if (
                was_applied
                and bool(getattr(product, "oos_response_enabled", False))
                and existing.price_before is not None
            ):
                product.my_price = existing.price_before
                self.db.add(MyPriceHistory(
                    product_id=product.id,
                    workspace_id=product.workspace_id,
                    old_price=existing.price_applied,
                    new_price=existing.price_before,
                    note=f"OOS revert: {match.competitor_name or 'competitor'} back in stock",
                ))

        try:
            self.db.commit()
            logger.info(
                "OOS opportunity closed for product %d (%d competitors still OOS)",
                product.id, existing.oos_competitor_count,
            )
        except Exception:
            self.db.rollback()
            logger.exception("Failed to close OOS opportunity for product %d", product.id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_floor(self, product: ProductMonitored) -> Optional[float]:
        """Inline floor calculation — avoids full RepricingService instantiation."""
        cost = getattr(product, "cost_price", None)
        margin = getattr(product, "target_margin_pct", None)
        if cost and margin and 0 < margin < 100:
            return cost / (1 - margin / 100)
        candidates = [
            p for p in [
                getattr(product, "min_price", None),
                getattr(product, "map_price", None),
            ] if p
        ]
        return max(candidates) if candidates else None


def get_oos_opportunity_service(db: Session) -> OosOpportunityService:
    return OosOpportunityService(db)
