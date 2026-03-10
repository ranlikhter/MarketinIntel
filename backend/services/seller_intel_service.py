"""
Seller Intelligence Service
Surfaces seller identity intelligence including 1P threats,
seller profiles, and buy-box volatility analysis.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from utils.time import utcnow
from collections import defaultdict

from database.models import (
    ReviewSnapshot, SellerProfile, ListingQualitySnapshot, KeywordRank,
    CompetitorMatch, ProductMonitored, PriceHistory, User
)


class SellerIntelService:
    """
    Service for analyzing seller identity and buy-box intelligence.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_seller_overview(self) -> List[Dict[str, Any]]:
        """
        All unique sellers across the user's competitor matches.

        For each seller: name, amazon_is_1p, feedback stats, and how many
        of the user's products they compete on. Sorted by product_count desc.
        """
        # Get all matches for this user's products
        matches = self.db.query(CompetitorMatch).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        # Aggregate per seller_name
        seller_map: Dict[str, Dict[str, Any]] = {}

        for match in matches:
            seller_name = match.seller_name
            if not seller_name:
                continue

            if seller_name not in seller_map:
                seller_map[seller_name] = {
                    "seller_name": seller_name,
                    "product_ids": set(),
                    "competitor_names": set(),
                    "amazon_is_seller": False,
                    "feedback_counts": [],
                    "positive_feedback_pcts": [],
                }

            entry = seller_map[seller_name]
            entry["product_ids"].add(match.monitored_product_id)
            entry["competitor_names"].add(match.competitor_name)

            if match.amazon_is_seller:
                entry["amazon_is_seller"] = True

            if match.seller_feedback_count is not None:
                entry["feedback_counts"].append(match.seller_feedback_count)

            if match.seller_positive_feedback_pct is not None:
                entry["positive_feedback_pcts"].append(match.seller_positive_feedback_pct)

        # Enrich with SellerProfile data where available
        seller_profiles = {
            sp.seller_name: sp
            for sp in self.db.query(SellerProfile).filter(
                SellerProfile.seller_name.in_(list(seller_map.keys()))
            ).all()
        }

        result = []
        for seller_name, entry in seller_map.items():
            profile = seller_profiles.get(seller_name)

            feedback_count = (
                profile.feedback_count
                if profile and profile.feedback_count is not None
                else (max(entry["feedback_counts"]) if entry["feedback_counts"] else None)
            )
            positive_feedback_pct = (
                float(profile.positive_feedback_pct)
                if profile and profile.positive_feedback_pct is not None
                else (
                    round(sum(entry["positive_feedback_pcts"]) / len(entry["positive_feedback_pcts"]), 1)
                    if entry["positive_feedback_pcts"] else None
                )
            )
            feedback_rating = (
                float(profile.feedback_rating) if profile and profile.feedback_rating is not None else None
            )

            result.append({
                "seller_name": seller_name,
                "amazon_is_1p": profile.amazon_is_1p if profile else entry["amazon_is_seller"],
                "feedback_rating": feedback_rating,
                "feedback_count": feedback_count,
                "positive_feedback_pct": positive_feedback_pct,
                "product_count": len(entry["product_ids"]),
                "competitor_names": sorted(entry["competitor_names"]),
                "storefront_url": profile.storefront_url if profile else None,
                "first_seen_at": profile.first_seen_at.isoformat() if profile and profile.first_seen_at else None,
            })

        result.sort(key=lambda x: x["product_count"], reverse=True)
        return result

    def get_amazon_1p_threats(self) -> List[Dict[str, Any]]:
        """
        Products where competitor_match.amazon_is_seller is True.

        Returns list with product_title, competitor_name, competitor_url,
        latest_price, and since (first scrape with amazon_is_seller).
        """
        matches = self.db.query(CompetitorMatch).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id,
            CompetitorMatch.amazon_is_seller == True  # noqa: E712
        ).all()

        threats = []

        for match in matches:
            product = self.db.query(ProductMonitored).filter(
                ProductMonitored.id == match.monitored_product_id
            ).first()

            # Approximate "since" as the earliest PriceHistory entry for this match
            earliest_entry = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id
            ).order_by(PriceHistory.timestamp).first()

            threats.append({
                "product_id": match.monitored_product_id,
                "product_title": product.title if product else None,
                "competitor_name": match.competitor_name,
                "competitor_url": getattr(match, "competitor_url", None),
                "latest_price": float(match.latest_price) if match.latest_price is not None else None,
                "since": earliest_entry.timestamp.isoformat() if earliest_entry else None,
            })

        threats.sort(key=lambda x: x["product_title"] or "")
        return threats

    def get_seller_profile(self, seller_name: str) -> Dict[str, Any]:
        """
        Detailed profile for one seller.

        Includes their SellerProfile record, associated competitor listings,
        and products they compete on.
        """
        profile = self.db.query(SellerProfile).filter(
            func.lower(SellerProfile.seller_name) == seller_name.lower()
        ).first()

        matches = self.db.query(CompetitorMatch).join(
            ProductMonitored
        ).filter(
            ProductMonitored.user_id == self.user.id,
            func.lower(CompetitorMatch.seller_name) == seller_name.lower()
        ).all()

        if not profile and not matches:
            return {"error": "Seller not found", "seller_name": seller_name}

        products = []
        for match in matches:
            product = self.db.query(ProductMonitored).filter(
                ProductMonitored.id == match.monitored_product_id
            ).first()

            products.append({
                "match_id": match.id,
                "product_id": match.monitored_product_id,
                "product_title": product.title if product else None,
                "competitor_name": match.competitor_name,
                "latest_price": float(match.latest_price) if match.latest_price is not None else None,
                "amazon_is_seller": match.amazon_is_seller,
                "seller_feedback_count": match.seller_feedback_count,
                "seller_positive_feedback_pct": (
                    float(match.seller_positive_feedback_pct)
                    if match.seller_positive_feedback_pct is not None else None
                ),
            })

        return {
            "seller_name": seller_name,
            "amazon_is_1p": profile.amazon_is_1p if profile else None,
            "feedback_rating": float(profile.feedback_rating) if profile and profile.feedback_rating else None,
            "feedback_count": profile.feedback_count if profile else None,
            "positive_feedback_pct": (
                float(profile.positive_feedback_pct)
                if profile and profile.positive_feedback_pct is not None else None
            ),
            "storefront_url": profile.storefront_url if profile else None,
            "first_seen_at": profile.first_seen_at.isoformat() if profile and profile.first_seen_at else None,
            "last_updated_at": profile.last_updated_at.isoformat() if profile and profile.last_updated_at else None,
            "competing_products": products,
            "total_competing_products": len(products),
        }

    def get_buybox_volatility(self, product_id: int) -> Dict[str, Any]:
        """
        For a product, analyze seller_name changes in PriceHistory over last 30 days.

        High volatility = many different sellers winning the buy-box = unstable pricing.
        Returns {product_id, seller_changes, unique_sellers, volatility_score (0-100), timeline}.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found", "product_id": product_id}

        cutoff = utcnow() - timedelta(days=30)

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()

        # Collect all price history entries with seller info across all matches
        all_entries = []
        for match in matches:
            entries = self.db.query(PriceHistory).filter(
                PriceHistory.match_id == match.id,
                PriceHistory.timestamp >= cutoff
            ).order_by(PriceHistory.timestamp).all()

            for entry in entries:
                seller = getattr(entry, "seller_name", None) or match.seller_name
                if seller:
                    all_entries.append({
                        "timestamp": entry.timestamp,
                        "seller_name": seller,
                        "price": float(entry.price) if entry.price is not None else None,
                        "competitor_name": match.competitor_name,
                    })

        all_entries.sort(key=lambda x: x["timestamp"])

        # Count seller changes and unique sellers
        seller_changes = 0
        prev_seller = None
        unique_sellers = set()
        timeline = []

        for entry in all_entries:
            seller = entry["seller_name"]
            unique_sellers.add(seller)

            if prev_seller is not None and seller != prev_seller:
                seller_changes += 1

            timeline.append({
                "timestamp": entry["timestamp"].isoformat(),
                "seller_name": seller,
                "price": entry["price"],
                "competitor_name": entry["competitor_name"],
            })

            prev_seller = seller

        total_entries = len(all_entries)
        unique_seller_count = len(unique_sellers)

        # Volatility score: 0-100 based on change rate and unique seller count
        if total_entries <= 1:
            volatility_score = 0
        else:
            change_rate = seller_changes / (total_entries - 1)  # 0-1
            diversity_factor = min(unique_seller_count / 5.0, 1.0)  # cap at 5 sellers = 1.0
            raw_score = (change_rate * 0.7 + diversity_factor * 0.3) * 100
            volatility_score = round(min(raw_score, 100), 1)

        return {
            "product_id": product_id,
            "product_title": product.title,
            "period_days": 30,
            "total_observations": total_entries,
            "seller_changes": seller_changes,
            "unique_sellers": sorted(unique_sellers),
            "unique_seller_count": unique_seller_count,
            "volatility_score": volatility_score,
            "volatility_label": (
                "high" if volatility_score >= 66
                else "medium" if volatility_score >= 33
                else "low"
            ),
            "timeline": timeline,
        }


def get_seller_intel_service(db: Session, user: User) -> SellerIntelService:
    """Factory function for SellerIntelService"""
    return SellerIntelService(db, user)
