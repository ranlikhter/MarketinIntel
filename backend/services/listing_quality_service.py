"""
Listing Quality Service
Provides listing quality intelligence by scoring and comparing competitor
listings using ListingQualitySnapshot and CompetitorMatch data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database.models import (
    ReviewSnapshot, SellerProfile, ListingQualitySnapshot, KeywordRank,
    CompetitorMatch, ProductMonitored, PriceHistory, User
)


class ListingQualityService:
    """
    Service for computing and comparing listing quality scores.

    Score formula (0-100):
      image_count:       min(image_count, 7) / 7 * 20       (max 20 pts)
      has_video:         15 pts if True
      has_aplus_content: 20 pts if True
      has_brand_story:   10 pts if True
      bullet_point_count: min(bullet_point_count, 5) / 5 * 15  (max 15 pts)
      title_char_count:  10 if 80-200 chars, 5 if 50-80 or 200-250, 0 otherwise
      questions_count:   min(questions_count, 50) / 50 * 10  (max 10 pts)
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def compute_listing_score(self, match: CompetitorMatch) -> int:
        """
        Compute listing quality score (0-100) from a CompetitorMatch object.

        Returns int 0-100. Handles None field values gracefully.
        """
        score = 0.0

        # Image count: max 20 pts
        image_count = match.image_count or 0
        score += min(image_count, 7) / 7 * 20

        # Video: 15 pts
        if match.has_video:
            score += 15

        # A+ content: 20 pts
        if match.has_aplus_content:
            score += 20

        # Brand story: 10 pts
        if match.has_brand_story:
            score += 10

        # Bullet points: max 15 pts
        bullet_count = match.bullet_point_count or 0
        score += min(bullet_count, 5) / 5 * 15

        # Title char count: 10 / 5 / 0 pts
        title_chars = match.title_char_count or 0
        if 80 <= title_chars <= 200:
            score += 10
        elif (50 <= title_chars < 80) or (200 < title_chars <= 250):
            score += 5

        # Questions count: max 10 pts
        questions = match.questions_count or 0
        score += min(questions, 50) / 50 * 10

        return int(round(score))

    def _score_breakdown(self, match: CompetitorMatch) -> Dict[str, Any]:
        """Return per-component score breakdown for a CompetitorMatch."""
        image_count = match.image_count or 0
        bullet_count = match.bullet_point_count or 0
        title_chars = match.title_char_count or 0
        questions = match.questions_count or 0

        image_pts = round(min(image_count, 7) / 7 * 20, 1)
        video_pts = 15 if match.has_video else 0
        aplus_pts = 20 if match.has_aplus_content else 0
        brand_pts = 10 if match.has_brand_story else 0
        bullet_pts = round(min(bullet_count, 5) / 5 * 15, 1)

        if 80 <= title_chars <= 200:
            title_pts = 10
        elif (50 <= title_chars < 80) or (200 < title_chars <= 250):
            title_pts = 5
        else:
            title_pts = 0

        questions_pts = round(min(questions, 50) / 50 * 10, 1)

        total = int(round(image_pts + video_pts + aplus_pts + brand_pts + bullet_pts + title_pts + questions_pts))

        return {
            "total_score": total,
            "breakdown": {
                "image_count_pts": image_pts,
                "video_pts": video_pts,
                "aplus_content_pts": aplus_pts,
                "brand_story_pts": brand_pts,
                "bullet_points_pts": bullet_pts,
                "title_length_pts": title_pts,
                "questions_pts": questions_pts,
            },
            "raw_values": {
                "image_count": image_count,
                "has_video": bool(match.has_video),
                "has_aplus_content": bool(match.has_aplus_content),
                "has_brand_story": bool(match.has_brand_story),
                "bullet_point_count": bullet_count,
                "title_char_count": title_chars,
                "questions_count": questions,
            },
        }

    def get_listing_comparison(self, product_id: int) -> Dict[str, Any]:
        """
        Compare all competitor listing scores for one product.

        Returns each competitor's score breakdown. Includes the monitored
        product's own listing fields if available on its match records.
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

        competitors = []
        for match in matches:
            breakdown = self._score_breakdown(match)
            competitors.append({
                "match_id": match.id,
                "competitor_name": match.competitor_name,
                "stored_listing_quality_score": match.listing_quality_score,
                **breakdown,
            })

        # Sort by computed total_score descending
        competitors.sort(key=lambda x: x["total_score"], reverse=True)

        scores = [c["total_score"] for c in competitors]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        return {
            "product_id": product_id,
            "product_title": product.title,
            "average_competitor_score": avg_score,
            "max_competitor_score": max(scores) if scores else None,
            "min_competitor_score": min(scores) if scores else None,
            "competitors": competitors,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_portfolio_listing_gaps(self) -> List[Dict[str, Any]]:
        """
        Across all products: find competitors with listing_quality_score > 80
        while other competitors on the same product are < 60.

        These are "listing quality threats". Returns list sorted by score gap desc.
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        threats = []

        for product in products:
            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).all()

            if len(matches) < 2:
                continue

            # Score each match using stored score if available, else compute
            scored = []
            for match in matches:
                score = (
                    match.listing_quality_score
                    if match.listing_quality_score is not None
                    else self.compute_listing_score(match)
                )
                scored.append((match, score))

            high_scorers = [(m, s) for m, s in scored if s > 80]
            low_scorers = [(m, s) for m, s in scored if s < 60]

            if not high_scorers or not low_scorers:
                continue

            max_high_score = max(s for _, s in high_scorers)
            min_low_score = min(s for _, s in low_scorers)
            gap = max_high_score - min_low_score

            threats.append({
                "product_id": product.id,
                "product_title": product.title,
                "score_gap": gap,
                "high_quality_competitors": [
                    {"competitor_name": m.competitor_name, "score": s}
                    for m, s in high_scorers
                ],
                "low_quality_competitors": [
                    {"competitor_name": m.competitor_name, "score": s}
                    for m, s in low_scorers
                ],
            })

        threats.sort(key=lambda x: x["score_gap"], reverse=True)
        return threats

    def get_listing_trends(
        self,
        match_id: int,
        days: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Time series from ListingQualitySnapshot showing how a competitor's
        listing quality has changed over time.

        Returns list of {date, score, image_count, has_video, has_aplus_content}.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        snapshots = self.db.query(ListingQualitySnapshot).filter(
            ListingQualitySnapshot.match_id == match_id,
            ListingQualitySnapshot.scraped_at >= cutoff
        ).order_by(ListingQualitySnapshot.scraped_at).all()

        result = []
        for snap in snapshots:
            result.append({
                "date": snap.scraped_at.date().isoformat(),
                "score": snap.listing_score,
                "image_count": snap.image_count,
                "has_video": snap.has_video,
                "has_aplus_content": snap.has_aplus_content,
                "has_brand_story": snap.has_brand_story,
                "bullet_point_count": snap.bullet_point_count,
                "title_char_count": snap.title_char_count,
                "questions_count": snap.questions_count,
            })

        return result


def get_listing_quality_service(db: Session, user: User) -> ListingQualityService:
    """Factory function for ListingQualityService"""
    return ListingQualityService(db, user)
