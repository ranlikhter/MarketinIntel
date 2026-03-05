"""
Product Health Service
Computes review velocity and product health signals from ReviewSnapshot,
CompetitorMatch, and PriceHistory data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database.models import (
    ReviewSnapshot, SellerProfile, ListingQualitySnapshot, KeywordRank,
    CompetitorMatch, ProductMonitored, PriceHistory, User
)


class ProductHealthService:
    """
    Service for analyzing product health via review velocity and listing signals.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_product_health_summary(self, product_id: int) -> Dict[str, Any]:
        """
        For one product: review velocity (7d, 30d) per competitor,
        listing quality scores, and questions counts.

        Review velocity = latest_review_count - review_count_N_days_ago
        from ReviewSnapshot ordered by scraped_at.

        Returns dict with competitors list.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found", "product_id": product_id}

        matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()

        if not matches:
            return {
                "product_id": product_id,
                "product_title": product.title,
                "competitors": [],
                "message": "No competitors found for this product"
            }

        now = datetime.utcnow()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)

        competitors = []

        for match in matches:
            # Get all snapshots for this match ordered by scraped_at ascending
            snapshots = self.db.query(ReviewSnapshot).filter(
                ReviewSnapshot.match_id == match.id
            ).order_by(ReviewSnapshot.scraped_at).all()

            latest_snapshot = snapshots[-1] if snapshots else None
            latest_review_count = latest_snapshot.review_count if latest_snapshot else None
            latest_rating = latest_snapshot.rating if latest_snapshot else None

            # 7-day velocity: find the oldest snapshot at or before 7 days ago
            snap_7d = None
            for s in snapshots:
                if s.scraped_at <= cutoff_7d:
                    snap_7d = s
                else:
                    break

            velocity_7d = None
            if latest_review_count is not None and snap_7d is not None and snap_7d.review_count is not None:
                velocity_7d = latest_review_count - snap_7d.review_count

            # 30-day velocity
            snap_30d = None
            for s in snapshots:
                if s.scraped_at <= cutoff_30d:
                    snap_30d = s
                else:
                    break

            velocity_30d = None
            if latest_review_count is not None and snap_30d is not None and snap_30d.review_count is not None:
                velocity_30d = latest_review_count - snap_30d.review_count

            competitors.append({
                "match_id": match.id,
                "competitor_name": match.competitor_name,
                "latest_review_count": latest_review_count,
                "latest_rating": float(latest_rating) if latest_rating is not None else None,
                "review_velocity_7d": velocity_7d,
                "review_velocity_30d": velocity_30d,
                "listing_quality_score": match.listing_quality_score,
                "questions_count": match.questions_count,
                "rating_distribution": latest_snapshot.rating_distribution if latest_snapshot else None,
                "last_scraped": latest_snapshot.scraped_at.isoformat() if latest_snapshot else None,
            })

        return {
            "product_id": product_id,
            "product_title": product.title,
            "competitors": competitors,
            "generated_at": now.isoformat()
        }

    def get_portfolio_health(self) -> Dict[str, Any]:
        """
        Across all user's products: flag products where any competitor's
        7d review velocity > 20 (surging), or where rating dropped > 0.2
        in 30 days (quality concern).

        Returns summary + flagged_products list.
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        if not products:
            return {"error": "No products found", "flagged_products": []}

        now = datetime.utcnow()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)

        flagged_products = []
        total_products = len(products)
        surging_count = 0
        quality_concern_count = 0

        for product in products:
            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).all()

            flags = []

            for match in matches:
                snapshots = self.db.query(ReviewSnapshot).filter(
                    ReviewSnapshot.match_id == match.id
                ).order_by(ReviewSnapshot.scraped_at).all()

                if not snapshots:
                    continue

                latest = snapshots[-1]

                # Check 7d surging velocity
                snap_7d = None
                for s in snapshots:
                    if s.scraped_at <= cutoff_7d:
                        snap_7d = s
                    else:
                        break

                if (snap_7d is not None
                        and latest.review_count is not None
                        and snap_7d.review_count is not None):
                    velocity_7d = latest.review_count - snap_7d.review_count
                    if velocity_7d > 20:
                        flags.append({
                            "flag_type": "surging_reviews",
                            "competitor_name": match.competitor_name,
                            "velocity_7d": velocity_7d,
                            "latest_review_count": latest.review_count
                        })

                # Check 30d rating drop
                snap_30d = None
                for s in snapshots:
                    if s.scraped_at <= cutoff_30d:
                        snap_30d = s
                    else:
                        break

                if (snap_30d is not None
                        and latest.rating is not None
                        and snap_30d.rating is not None):
                    rating_drop = float(snap_30d.rating) - float(latest.rating)
                    if rating_drop > 0.2:
                        flags.append({
                            "flag_type": "rating_drop",
                            "competitor_name": match.competitor_name,
                            "rating_30d_ago": float(snap_30d.rating),
                            "rating_now": float(latest.rating),
                            "rating_drop": round(rating_drop, 2)
                        })

            if flags:
                has_surging = any(f["flag_type"] == "surging_reviews" for f in flags)
                has_quality = any(f["flag_type"] == "rating_drop" for f in flags)

                if has_surging:
                    surging_count += 1
                if has_quality:
                    quality_concern_count += 1

                flagged_products.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "flags": flags
                })

        return {
            "generated_at": now.isoformat(),
            "summary": {
                "total_products": total_products,
                "products_with_flags": len(flagged_products),
                "surging_competitor_count": surging_count,
                "quality_concern_count": quality_concern_count
            },
            "flagged_products": flagged_products
        }

    def get_review_velocity_trend(
        self,
        match_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Time series of review_count from ReviewSnapshot for a specific match.

        Returns list of {date, review_count, velocity} where velocity is
        the day-over-day change in review_count.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        snapshots = self.db.query(ReviewSnapshot).filter(
            ReviewSnapshot.match_id == match_id,
            ReviewSnapshot.scraped_at >= cutoff
        ).order_by(ReviewSnapshot.scraped_at).all()

        if not snapshots:
            return []

        result = []
        prev_count = None

        for snap in snapshots:
            review_count = snap.review_count
            if prev_count is not None and review_count is not None:
                velocity = review_count - prev_count
            else:
                velocity = None

            result.append({
                "date": snap.scraped_at.date().isoformat(),
                "review_count": review_count,
                "velocity": velocity
            })

            if review_count is not None:
                prev_count = review_count

        return result


def get_product_health_service(db: Session, user: User) -> ProductHealthService:
    """Factory function for ProductHealthService"""
    return ProductHealthService(db, user)
