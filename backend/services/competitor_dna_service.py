"""
Competitor Strategy DNA Service

Extracts each competitor's pricing "personality" from historical data:
  - WHEN they typically change prices (day-of-week + hour-of-day strike patterns)
  - HOW HARD they hit (average drop magnitude)
  - WHETHER a drop is a promo or permanent (revert rate analysis)
  - HOW FAST they react to market changes (response lag)
  - WHAT HAPPENS if you reprice (simulation based on their DNA)

This turns reactive monitoring into proactive strategy.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from database.models import (
    User, ProductMonitored, CompetitorMatch, PriceHistory, MyPriceHistory,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_DNA_LOOKBACK_DAYS      = 90     # Days of history to build DNA from
_REVERT_WINDOW_HOURS    = 72     # Hours to wait to call a drop "promotional"
_REVERT_TOLERANCE_PCT   = 3.0    # Price must come back within 3% to count as reversion
_MIN_CHANGES_FOR_DNA    = 3      # Minimum price changes needed to compute a pattern
_RESPONSE_LAG_WINDOW    = 7      # Days after your price change to look for competitor reaction

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Core service ──────────────────────────────────────────────────────────────

class CompetitorDNAService:
    """
    Analyses competitor pricing behaviour patterns across all products
    a user monitors.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self._cutoff = datetime.utcnow() - timedelta(days=_DNA_LOOKBACK_DAYS)

    # ─────────────────────────────────────────────────────────────────────────
    # Public methods
    # ─────────────────────────────────────────────────────────────────────────

    def get_all_profiles(self) -> dict:
        """Return DNA profiles for every competitor this user monitors."""
        names = (
            self.db.query(CompetitorMatch.competitor_name)
            .join(ProductMonitored,
                  ProductMonitored.id == CompetitorMatch.monitored_product_id)
            .filter(ProductMonitored.user_id == self.user.id)
            .distinct()
            .all()
        )
        profiles = []
        for (name,) in names:
            p = self.get_competitor_dna(name)
            if p.get("sufficient_data"):
                profiles.append(p)
            else:
                profiles.append({
                    "competitor_name": name,
                    "sufficient_data": False,
                    "message": p.get("message", "Insufficient data"),
                })
        profiles.sort(key=lambda x: -x.get("data_points", 0))
        return {"total_competitors": len(profiles), "profiles": profiles}

    def get_competitor_dna(self, competitor_name: str) -> dict:
        """
        Build the full DNA profile for one competitor.

        Returns:
          strike_patterns, revert_rate, aggression_score, response_lag,
          avg_drop_pct, avg_raise_pct, ai_summary, strike_prediction, ...
        """
        matches = self._get_user_matches(competitor_name)
        if not matches:
            return {"competitor_name": competitor_name, "sufficient_data": False,
                    "message": "Competitor not found in your catalog"}

        all_changes = self._collect_price_changes(matches)
        if len(all_changes) < _MIN_CHANGES_FOR_DNA:
            return {
                "competitor_name": competitor_name,
                "sufficient_data": False,
                "data_points": len(all_changes),
                "message": f"Need at least {_MIN_CHANGES_FOR_DNA} price changes to build a DNA profile. "
                           f"Only {len(all_changes)} found in the last {_DNA_LOOKBACK_DAYS} days.",
            }

        strike_patterns = self._build_strike_patterns(all_changes)
        drops   = [c for c in all_changes if c["change_pct"] < 0]
        raises  = [c for c in all_changes if c["change_pct"] > 0]
        revert_analysis = self._analyse_reversions(matches, drops)
        aggression = self._compute_aggression_score(matches)
        response_lag = self._compute_response_lag(competitor_name, matches)

        avg_drop_pct  = round(abs(sum(c["change_pct"] for c in drops)  / len(drops)),  2) if drops  else None
        avg_raise_pct = round(abs(sum(c["change_pct"] for c in raises) / len(raises)), 2) if raises else None

        strike_prediction = self._predict_next_strike(strike_patterns, revert_analysis)
        ai_summary = self._generate_ai_summary(
            competitor_name=competitor_name,
            strike_patterns=strike_patterns,
            revert_analysis=revert_analysis,
            aggression=aggression,
            response_lag=response_lag,
            avg_drop_pct=avg_drop_pct,
            strike_prediction=strike_prediction,
        )

        return {
            "competitor_name": competitor_name,
            "sufficient_data": True,
            "products_tracked": len(matches),
            "data_points": len(all_changes),
            "lookback_days": _DNA_LOOKBACK_DAYS,
            "aggression_score": aggression,
            "strike_patterns": strike_patterns,
            "revert_analysis": revert_analysis,
            "response_lag": response_lag,
            "avg_drop_pct": avg_drop_pct,
            "avg_raise_pct": avg_raise_pct,
            "total_drops": len(drops),
            "total_raises": len(raises),
            "strike_prediction": strike_prediction,
            "ai_summary": ai_summary,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_strike_predictions(self) -> dict:
        """
        Predict upcoming price changes across all competitors for the next 7 days.
        Returns a timeline of expected strikes with probability scores.
        """
        names = (
            self.db.query(CompetitorMatch.competitor_name)
            .join(ProductMonitored,
                  ProductMonitored.id == CompetitorMatch.monitored_product_id)
            .filter(ProductMonitored.user_id == self.user.id)
            .distinct()
            .all()
        )

        predictions = []
        for (name,) in names:
            dna = self.get_competitor_dna(name)
            if not dna.get("sufficient_data"):
                continue
            pred = dna["strike_prediction"]
            if pred.get("probability", 0) >= 20:
                predictions.append({
                    "competitor": name,
                    "aggression_score": dna["aggression_score"],
                    "prediction": pred,
                    "revert_rate": dna["revert_analysis"].get("revert_rate_pct", 0),
                    "avg_expected_drop": dna["avg_drop_pct"],
                })

        predictions.sort(key=lambda x: -x["prediction"]["probability"])

        # Group by day for calendar view
        calendar: dict = {}
        for p in predictions:
            day = p["prediction"].get("most_likely_day", "Unknown")
            if day not in calendar:
                calendar[day] = []
            calendar[day].append({
                "competitor": p["competitor"],
                "probability": p["prediction"]["probability"],
                "expected_drop_pct": p["avg_expected_drop"],
                "likely_promo": p["revert_rate"] >= 60,
            })

        return {
            "predictions": predictions,
            "calendar": calendar,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def classify_price_change(
        self,
        competitor_name: str,
        product_id: int,
        old_price: float,
        new_price: float,
    ) -> dict:
        """
        When a price change is detected, classify it as:
          HOLD   — likely a temporary promo; don't reprice
          RESPOND — permanent competitive move; action needed
          IGNORE  — outlier / noise; monitor and wait

        Uses the competitor's DNA profile + product-specific context.
        """
        change_pct = round((new_price - old_price) / old_price * 100, 2)
        is_drop = change_pct < 0

        dna = self.get_competitor_dna(competitor_name)
        sufficient = dna.get("sufficient_data", False)

        # Pull product context
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id,
        ).first()

        match = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id,
            func.lower(CompetitorMatch.competitor_name) == competitor_name.lower(),
        ).first()

        # Check for promo markers in latest price history
        promo_signals = []
        if match:
            latest = (
                self.db.query(PriceHistory)
                .filter(PriceHistory.match_id == match.id)
                .order_by(desc(PriceHistory.timestamp))
                .first()
            )
            if latest:
                if latest.is_lightning_deal:
                    promo_signals.append("Active lightning deal detected")
                if latest.promotion_label:
                    promo_signals.append(f"Promotion label: '{latest.promotion_label}'")
                if latest.coupon_pct or latest.coupon_value:
                    promo_signals.append("Active coupon detected")
                if latest.was_price and latest.was_price > new_price:
                    promo_signals.append(f"Strike-through price: ${latest.was_price:.2f}")

        # Build classification
        classification = "RESPOND"
        confidence = "medium"
        reasoning_parts = []
        recommended_action = ""

        if promo_signals:
            classification = "HOLD"
            confidence = "high"
            reasoning_parts.append(
                f"Promo markers detected: {'; '.join(promo_signals)}. "
                "This is almost certainly temporary."
            )
            recommended_action = (
                "Do not reprice. Monitor for the next 48–72 h. "
                "If price doesn't revert, reassess with 'RESPOND'."
            )

        elif is_drop and sufficient:
            revert_rate = dna["revert_analysis"].get("revert_rate_pct", 0)
            patterns    = dna["strike_patterns"]

            # Check if today matches their typical strike day
            today_name = DAYS[datetime.utcnow().weekday()]
            top_day = patterns.get("most_active_day", "")
            day_match = today_name == top_day

            if revert_rate >= 70:
                classification = "HOLD"
                confidence = "high"
                reasoning_parts.append(
                    f"{competitor_name} reverts {revert_rate}% of price drops within 72 h — "
                    "this is almost certainly a promotional price."
                )
                if day_match:
                    reasoning_parts.append(
                        f"Today ({today_name}) is their most common strike day, "
                        "which further supports a short-lived promo."
                    )
                recommended_action = (
                    f"Hold your price. If {competitor_name} hasn't reverted within 72 h, "
                    "come back and reclassify."
                )

            elif revert_rate >= 40:
                classification = "RESPOND"
                confidence = "medium"
                reasoning_parts.append(
                    f"{competitor_name} reverts {revert_rate}% of drops — mixed signal. "
                    "Could be promo or permanent."
                )
                if abs(change_pct) > (dna.get("avg_drop_pct") or 0) * 1.5:
                    reasoning_parts.append(
                        f"This drop ({abs(change_pct):.1f}%) is {1.5:.0f}× larger than their "
                        f"average drop ({dna.get('avg_drop_pct', '?')}%) — more likely permanent."
                    )
                    classification = "RESPOND"
                    confidence = "medium"
                recommended_action = (
                    "Consider a partial price move (match but don't undercut). "
                    "Reassess in 48 h once the pattern is clearer."
                )

            else:
                classification = "RESPOND"
                confidence = "high"
                reasoning_parts.append(
                    f"{competitor_name} only reverts {revert_rate}% of drops — "
                    "this is highly likely to be a permanent price reduction."
                )
                recommended_action = (
                    "This appears permanent. Review your margin at the new price and "
                    "decide whether to match, undercut, or hold based on your strategy."
                )

        elif not is_drop:
            # Price raise by competitor
            classification = "IGNORE"
            confidence = "high"
            reasoning_parts.append(
                f"{competitor_name} raised their price by {change_pct:.1f}%. "
                "This is an opportunity — you may be able to raise yours too."
            )
            recommended_action = (
                "Consider a small price increase if your position allows. "
                f"{competitor_name} raising reduces competitive pressure."
            )

        else:
            # No DNA data
            classification = "RESPOND"
            confidence = "low"
            reasoning_parts.append(
                "Insufficient historical data to classify this change. "
                "Treating as a potential permanent move."
            )
            recommended_action = (
                "Check competitor page manually for promo badges. "
                "If no obvious promo, treat as permanent."
            )

        # AI narrative
        ai_narrative = self._classify_with_ai(
            competitor_name=competitor_name,
            product_title=product.title if product else "Unknown",
            old_price=old_price,
            new_price=new_price,
            change_pct=change_pct,
            classification=classification,
            promo_signals=promo_signals,
            dna=dna,
        )

        return {
            "classification": classification,
            "confidence": confidence,
            "change_pct": change_pct,
            "is_drop": is_drop,
            "promo_signals": promo_signals,
            "reasoning": " ".join(reasoning_parts),
            "recommended_action": recommended_action,
            "ai_narrative": ai_narrative,
            "competitor_dna_available": sufficient,
        }

    def simulate_reprice(
        self,
        product_id: int,
        proposed_price: float,
    ) -> dict:
        """
        "Before You Reprice" — simulate what competitors are likely to do
        if you change your price to proposed_price.

        Returns a projected market state at T+24h, T+48h, T+72h.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id,
        ).first()
        if not product:
            return {"error": "Product not found"}

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id,
        ).all()

        current_price = product.my_price
        price_delta_pct = (
            (proposed_price - current_price) / current_price * 100
            if current_price else 0
        )

        competitor_projections = []
        for match in matches:
            if not match.latest_price:
                continue

            dna = self.get_competitor_dna(match.competitor_name)
            projected = self._project_competitor_response(
                dna=dna,
                competitor_name=match.competitor_name,
                competitor_current_price=match.latest_price,
                your_proposed_price=proposed_price,
                price_delta_pct=price_delta_pct,
            )
            competitor_projections.append(projected)

        # Market state projections
        def _market_state(hours: int) -> dict:
            competing_prices = []
            for proj in competitor_projections:
                if hours >= proj.get("expected_response_hours", 9999):
                    competing_prices.append(proj["projected_price"])
                else:
                    competing_prices.append(proj["current_price"])

            all_prices = [proposed_price] + competing_prices
            if not all_prices:
                return {}

            cheapest = min(all_prices)
            my_rank = sorted(all_prices).index(proposed_price) + 1
            return {
                "hour": hours,
                "your_price": proposed_price,
                "lowest_competitor": min(competing_prices) if competing_prices else None,
                "avg_competitor": round(sum(competing_prices) / len(competing_prices), 2) if competing_prices else None,
                "your_rank": f"{my_rank} of {len(all_prices)}",
                "you_are_cheapest": proposed_price <= cheapest,
            }

        projections_24h = _market_state(24)
        projections_48h = _market_state(48)
        projections_72h = _market_state(72)

        # Recommendation
        revenue_impact = None
        if current_price and current_price != proposed_price:
            revenue_impact = round(
                (proposed_price - current_price) / current_price * 100, 1
            )

        ai_simulation = self._simulate_with_ai(
            product_title=product.title,
            current_price=current_price,
            proposed_price=proposed_price,
            competitor_projections=competitor_projections,
            projections_72h=projections_72h,
        )

        return {
            "product_id": product_id,
            "product_title": product.title,
            "current_price": current_price,
            "proposed_price": proposed_price,
            "price_change_pct": round(price_delta_pct, 2),
            "revenue_impact_pct": revenue_impact,
            "competitor_projections": competitor_projections,
            "market_state": {
                "t_plus_24h": projections_24h,
                "t_plus_48h": projections_48h,
                "t_plus_72h": projections_72h,
            },
            "ai_recommendation": ai_simulation,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_user_matches(self, competitor_name: str) -> list:
        return (
            self.db.query(CompetitorMatch)
            .join(ProductMonitored,
                  ProductMonitored.id == CompetitorMatch.monitored_product_id)
            .filter(
                ProductMonitored.user_id == self.user.id,
                func.lower(CompetitorMatch.competitor_name) == competitor_name.lower(),
            )
            .all()
        )

    def _collect_price_changes(self, matches: list) -> list:
        """
        Walk all price history for the given matches and extract
        each price-change event (timestamp, day, hour, magnitude).
        """
        changes = []
        for match in matches:
            rows = (
                self.db.query(PriceHistory)
                .filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= self._cutoff,
                )
                .order_by(PriceHistory.timestamp.asc())
                .all()
            )
            for i in range(1, len(rows)):
                prev, curr = rows[i - 1], rows[i]
                if prev.price and curr.price and prev.price != curr.price:
                    change_pct = (curr.price - prev.price) / prev.price * 100
                    changes.append({
                        "match_id": match.id,
                        "product_id": match.monitored_product_id,
                        "timestamp": curr.timestamp,
                        "day_of_week": curr.timestamp.weekday(),  # 0=Mon
                        "day_name": DAYS[curr.timestamp.weekday()],
                        "hour": curr.timestamp.hour,
                        "old_price": prev.price,
                        "new_price": curr.price,
                        "change_pct": round(change_pct, 2),
                        "is_drop": change_pct < 0,
                        "has_promo_label": bool(curr.promotion_label),
                        "is_lightning_deal": bool(curr.is_lightning_deal),
                        "has_coupon": bool(curr.coupon_pct or curr.coupon_value),
                    })
        return changes

    def _build_strike_patterns(self, changes: list) -> dict:
        """
        Build day-of-week and hour-of-day frequency distributions
        weighted slightly toward recent events.
        """
        now = datetime.utcnow()
        day_counts: dict[int, float] = defaultdict(float)
        hour_counts: dict[int, float] = defaultdict(float)

        for c in changes:
            # Linear weight: more recent = higher weight (range 0.5 → 1.5)
            days_ago = (now - c["timestamp"]).days
            weight = max(0.5, 1.5 - (days_ago / _DNA_LOOKBACK_DAYS))
            day_counts[c["day_of_week"]] += weight
            hour_counts[c["hour"]] += weight

        # Normalise to percentages
        total_day = sum(day_counts.values()) or 1
        total_hour = sum(hour_counts.values()) or 1

        day_dist = {
            DAYS[d]: round(day_counts[d] / total_day * 100, 1)
            for d in range(7)
        }
        hour_dist = {
            f"{h:02d}:00": round(hour_counts[h] / total_hour * 100, 1)
            for h in range(24)
        }

        top_day = max(day_counts, key=day_counts.get, default=None)
        top_hour = max(hour_counts, key=hour_counts.get, default=None)

        # Peak window (top 3 consecutive hours)
        sorted_hours = sorted(hour_counts.keys(), key=lambda h: -hour_counts[h])
        peak_hours = sorted(sorted_hours[:3])
        peak_window = (
            f"{peak_hours[0]:02d}:00–{peak_hours[-1]+1:02d}:00 UTC"
            if peak_hours else "Unknown"
        )

        return {
            "most_active_day": DAYS[top_day] if top_day is not None else "Unknown",
            "most_active_hour": top_hour,
            "peak_window_utc": peak_window,
            "day_distribution": day_dist,
            "hour_distribution": hour_dist,
            "total_changes_analysed": len(changes),
        }

    def _analyse_reversions(self, matches: list, drops: list) -> dict:
        """
        For every price drop, check if the price reverted within 72h.
        revert_rate_pct = % of drops that came back.
        """
        if not drops:
            return {"revert_rate_pct": 0, "reverted_count": 0, "total_drops": 0,
                    "avg_revert_hours": None, "interpretation": "No price drops in lookback window"}

        reverted = 0
        revert_hours_list = []

        # Build a lookup: match_id → sorted price history
        history_map: dict[int, list] = {}
        for match in matches:
            history_map[match.id] = (
                self.db.query(PriceHistory)
                .filter(
                    PriceHistory.match_id == match.id,
                    PriceHistory.timestamp >= self._cutoff,
                )
                .order_by(PriceHistory.timestamp.asc())
                .all()
            )

        for drop in drops:
            rows = history_map.get(drop["match_id"], [])
            drop_ts = drop["timestamp"]
            revert_deadline = drop_ts + timedelta(hours=_REVERT_WINDOW_HOURS)
            original_price = drop["old_price"]

            # Find first price after the drop within the revert window
            for row in rows:
                if row.timestamp <= drop_ts:
                    continue
                if row.timestamp > revert_deadline:
                    break
                if row.price and abs(row.price - original_price) / original_price * 100 <= _REVERT_TOLERANCE_PCT:
                    reverted += 1
                    hours = (row.timestamp - drop_ts).total_seconds() / 3600
                    revert_hours_list.append(hours)
                    break

        revert_rate = round(reverted / len(drops) * 100, 1) if drops else 0
        avg_revert_h = round(sum(revert_hours_list) / len(revert_hours_list), 1) if revert_hours_list else None

        if revert_rate >= 70:
            interpretation = "Primarily promotional pricer — most drops are temporary. Hold before reacting."
        elif revert_rate >= 40:
            interpretation = "Mixed signals — roughly half of drops are promos, half are permanent. Verify each case."
        else:
            interpretation = "Permanent pricer — drops rarely revert. Act promptly when they drop."

        return {
            "revert_rate_pct": revert_rate,
            "reverted_count": reverted,
            "total_drops": len(drops),
            "avg_revert_hours": avg_revert_h,
            "interpretation": interpretation,
        }

    def _compute_aggression_score(self, matches: list) -> int:
        """
        Aggression score 0–100: how often this competitor holds the lowest price
        across all products where we have multiple competitors.
        """
        lowest_count = 0
        total_compared = 0

        for match in matches:
            all_matches_for_product = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == match.monitored_product_id,
            ).all()

            prices = {m.competitor_name: m.latest_price for m in all_matches_for_product
                      if m.latest_price}
            if len(prices) < 2:
                continue

            total_compared += 1
            min_price = min(prices.values())
            if prices.get(match.competitor_name) == min_price:
                lowest_count += 1

        if total_compared == 0:
            return 0
        return round(lowest_count / total_compared * 100)

    def _compute_response_lag(self, competitor_name: str, matches: list) -> dict:
        """
        Estimate how quickly this competitor reacts when prices change in the market.

        Heuristic: after any significant price change in the category (across all
        competitors), how many hours before this competitor also changed?
        """
        lags = []
        for match in matches:
            sibling_matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == match.monitored_product_id,
                func.lower(CompetitorMatch.competitor_name) != competitor_name.lower(),
            ).all()

            for sib in sibling_matches:
                sib_changes = (
                    self.db.query(PriceHistory)
                    .filter(
                        PriceHistory.match_id == sib.id,
                        PriceHistory.timestamp >= self._cutoff,
                    )
                    .order_by(PriceHistory.timestamp.asc())
                    .all()
                )
                for i in range(1, len(sib_changes)):
                    if sib_changes[i].price == sib_changes[i - 1].price:
                        continue
                    change_ts = sib_changes[i].timestamp
                    # Find this competitor's next price change after that
                    our_next = (
                        self.db.query(PriceHistory)
                        .filter(
                            PriceHistory.match_id == match.id,
                            PriceHistory.timestamp > change_ts,
                            PriceHistory.timestamp <= change_ts + timedelta(days=_RESPONSE_LAG_WINDOW),
                        )
                        .order_by(PriceHistory.timestamp.asc())
                        .first()
                    )
                    if our_next:
                        prev_ours = (
                            self.db.query(PriceHistory)
                            .filter(
                                PriceHistory.match_id == match.id,
                                PriceHistory.timestamp <= change_ts,
                            )
                            .order_by(PriceHistory.timestamp.desc())
                            .first()
                        )
                        if prev_ours and our_next.price != prev_ours.price:
                            lag_h = (our_next.timestamp - change_ts).total_seconds() / 3600
                            lags.append(lag_h)

        if not lags:
            return {"avg_response_hours": None, "interpretation": "Insufficient data to measure response lag"}

        avg_lag = round(sum(lags) / len(lags), 1)
        if avg_lag < 6:
            interp = "Lightning-fast reactor — responds within hours. Watch closely."
        elif avg_lag < 24:
            interp = "Same-day reactor — usually responds within 24 h."
        elif avg_lag < 72:
            interp = "Moderate reactor — typically adjusts within 2-3 days."
        else:
            interp = "Slow reactor or independent pricer — doesn't closely follow the market."

        return {
            "avg_response_hours": avg_lag,
            "sample_size": len(lags),
            "interpretation": interp,
        }

    def _predict_next_strike(self, strike_patterns: dict, revert_analysis: dict) -> dict:
        """
        Predict the most likely day/window for the next price change.
        Returns probability (0–100) and interpretation.
        """
        top_day = strike_patterns.get("most_active_day", "Unknown")
        peak_window = strike_patterns.get("peak_window_utc", "Unknown")
        day_dist = strike_patterns.get("day_distribution", {})
        total_changes = strike_patterns.get("total_changes_analysed", 0)
        revert_rate = revert_analysis.get("revert_rate_pct", 0)

        if top_day == "Unknown" or total_changes < _MIN_CHANGES_FOR_DNA:
            return {"probability": 0, "most_likely_day": "Unknown", "interpretation": "Insufficient data"}

        # Probability is based on how concentrated the distribution is
        top_day_pct = day_dist.get(top_day, 0)
        # Scale: if they change 40%+ of the time on one day → high probability
        probability = min(95, int(top_day_pct * 2.2))

        promo_note = ""
        if revert_rate >= 60:
            promo_note = (
                f" If they do strike, there's a {revert_rate}% chance it's a temporary promo "
                f"(avg revert time: {revert_analysis.get('avg_revert_hours', '?')} h)."
            )

        interpretation = (
            f"Based on {total_changes} price changes over {_DNA_LOOKBACK_DAYS} days, "
            f"this competitor most often strikes on {top_day} "
            f"(~{top_day_pct:.0f}% of changes) during {peak_window}.{promo_note}"
        )

        return {
            "probability": probability,
            "most_likely_day": top_day,
            "peak_window_utc": peak_window,
            "top_day_frequency_pct": top_day_pct,
            "interpretation": interpretation,
        }

    def _project_competitor_response(
        self,
        dna: dict,
        competitor_name: str,
        competitor_current_price: float,
        your_proposed_price: float,
        price_delta_pct: float,
    ) -> dict:
        """
        Given your proposed price change, project how a competitor will respond.
        """
        will_respond = False
        expected_response_hours = None
        projected_price = competitor_current_price
        response_confidence = "low"
        reasoning = ""

        if not dna.get("sufficient_data"):
            reasoning = "Insufficient DNA data — response unknown."
        else:
            lag = dna["response_lag"].get("avg_response_hours")
            aggression = dna.get("aggression_score", 0)

            if price_delta_pct < 0:
                # You're dropping — aggressive competitors will follow
                if aggression >= 70:
                    will_respond = True
                    response_confidence = "high"
                    expected_response_hours = lag or 24
                    drop_magnitude = dna.get("avg_drop_pct") or abs(price_delta_pct)
                    projected_price = round(
                        competitor_current_price * (1 - drop_magnitude / 100), 2
                    )
                    reasoning = (
                        f"{competitor_name} is highly aggressive (score {aggression}/100). "
                        f"Expected to match your drop within ~{expected_response_hours:.0f} h."
                    )
                elif aggression >= 40:
                    will_respond = True
                    response_confidence = "medium"
                    expected_response_hours = lag or 48
                    projected_price = round(your_proposed_price * 0.99, 2)  # slight undercut
                    reasoning = (
                        f"{competitor_name} is moderately aggressive. "
                        f"May respond within ~{expected_response_hours:.0f} h if the gap is large."
                    )
                else:
                    will_respond = False
                    response_confidence = "medium"
                    reasoning = (
                        f"{competitor_name} has a low aggression score ({aggression}/100). "
                        "Unlikely to react to your price move."
                    )
            else:
                # You're raising — competitors rarely follow raises
                will_respond = False
                response_confidence = "high"
                reasoning = (
                    f"Competitors almost never raise prices in response to a seller raising theirs. "
                    f"{competitor_name} will likely hold at ${competitor_current_price:.2f}."
                )

        return {
            "competitor": competitor_name,
            "current_price": competitor_current_price,
            "will_respond": will_respond,
            "response_confidence": response_confidence,
            "expected_response_hours": expected_response_hours,
            "projected_price": projected_price,
            "reasoning": reasoning,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # AI narrative generators
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_ai_summary(self, *, competitor_name, strike_patterns, revert_analysis,
                              aggression, response_lag, avg_drop_pct, strike_prediction) -> str:
        """Ask Claude to write a 2-sentence personality summary for this competitor."""
        try:
            from services.ai_service import _call, _FAST_MODEL
            top_day = strike_patterns.get("most_active_day", "?")
            peak_window = strike_patterns.get("peak_window_utc", "?")
            revert_rate = revert_analysis.get("revert_rate_pct", "?")
            avg_revert_h = revert_analysis.get("avg_revert_hours", "?")
            lag = response_lag.get("avg_response_hours", "?")
            prob = strike_prediction.get("probability", 0)

            prompt = (
                f"Summarise this competitor's pricing DNA in exactly 2 sentences. "
                f"Be specific and use the numbers provided. "
                f"Do not start with 'Based on' or 'According to'.\n\n"
                f"Competitor: {competitor_name}\n"
                f"Aggression score: {aggression}/100\n"
                f"Most active strike day: {top_day} during {peak_window}\n"
                f"Avg price drop when they strike: {avg_drop_pct}%\n"
                f"Revert rate (promo rate): {revert_rate}% of drops revert within {avg_revert_h} h\n"
                f"Avg response lag to market changes: {lag} h\n"
                f"Next-strike probability this week: {prob}%"
            )
            return _call(_FAST_MODEL, "You are a competitive intelligence analyst.", prompt, max_tokens=120)
        except Exception as e:
            logger.debug("AI summary skipped: %s", e)
            return ""

    def _classify_with_ai(self, *, competitor_name, product_title, old_price, new_price,
                           change_pct, classification, promo_signals, dna) -> str:
        """Ask Claude to narrate the classification decision in one paragraph."""
        try:
            from services.ai_service import _call, _FAST_MODEL
            revert_rate = dna.get("revert_analysis", {}).get("revert_rate_pct", "unknown") if dna.get("sufficient_data") else "unknown"
            prompt = (
                f"Write one short paragraph (3-4 sentences) explaining this pricing intelligence decision. "
                f"Be direct and practical. Use dollar amounts.\n\n"
                f"Product: {product_title}\n"
                f"Competitor: {competitor_name}\n"
                f"Price change: ${old_price:.2f} → ${new_price:.2f} ({change_pct:+.1f}%)\n"
                f"Classification: {classification}\n"
                f"Promo signals detected: {', '.join(promo_signals) if promo_signals else 'None'}\n"
                f"Competitor's historical revert rate: {revert_rate}%\n"
                f"Explain why this classification makes sense and what the seller should do."
            )
            return _call(_FAST_MODEL, "You are a competitive pricing analyst.", prompt, max_tokens=150)
        except Exception as e:
            logger.debug("AI classification narrative skipped: %s", e)
            return ""

    def _simulate_with_ai(self, *, product_title, current_price, proposed_price,
                           competitor_projections, projections_72h) -> str:
        """Ask Claude for a one-paragraph reprice recommendation."""
        try:
            from services.ai_service import _call, _SMART_MODEL
            responders = [p for p in competitor_projections if p.get("will_respond")]
            non_responders = [p for p in competitor_projections if not p.get("will_respond")]

            proj_lines = []
            for p in responders[:3]:
                proj_lines.append(
                    f"  - {p['competitor']}: expected to match in ~{p.get('expected_response_hours', '?')}h "
                    f"→ projected ${p['projected_price']:.2f}"
                )
            for p in non_responders[:3]:
                proj_lines.append(f"  - {p['competitor']}: will NOT respond, stays at ${p['current_price']:.2f}")

            rank_72h = projections_72h.get("your_rank", "?")
            prompt = (
                f"Give a 2-3 sentence recommendation. Use specific numbers. "
                f"Tell the seller plainly whether to proceed with this reprice or not.\n\n"
                f"Product: {product_title}\n"
                f"Current price: ${current_price:.2f}\n"
                f"Proposed price: ${proposed_price:.2f}\n"
                f"Competitor responses expected:\n"
                + "\n".join(proj_lines) + f"\n"
                f"Your projected market rank at T+72h: {rank_72h}\n"
            )
            return _call(_SMART_MODEL, "You are a senior pricing strategist.", prompt, max_tokens=150)
        except Exception as e:
            logger.debug("AI simulation narrative skipped: %s", e)
            return ""


def get_competitor_dna_service(db: Session, user: User) -> CompetitorDNAService:
    return CompetitorDNAService(db, user)
