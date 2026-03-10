"""
Keyword Rank Service
Tracks keyword ranking positions for monitored products, surfaces
trends, and highlights rank movements across the portfolio.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from utils.time import utcnow

from database.models import (
    ReviewSnapshot, SellerProfile, ListingQualitySnapshot, KeywordRank,
    CompetitorMatch, ProductMonitored, PriceHistory, User
)


class KeywordRankService:
    """
    Service for keyword rank tracking and analysis.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_keyword_dashboard(self, product_id: int) -> List[Dict[str, Any]]:
        """
        All keywords tracked for a product.

        For each keyword: current rank, previous rank (7 days ago), trend
        (up/down/stable), best rank ever, worst rank ever. Returns list.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return []

        cutoff_7d = utcnow() - timedelta(days=7)

        # Get all unique keywords for this product
        keywords = self.db.query(KeywordRank.keyword).filter(
            KeywordRank.product_id == product_id
        ).distinct().all()

        keywords = [row[0] for row in keywords]

        result = []

        for keyword in keywords:
            # All entries for this keyword ordered by scraped_at desc
            entries = self.db.query(KeywordRank).filter(
                KeywordRank.product_id == product_id,
                KeywordRank.keyword == keyword
            ).order_by(desc(KeywordRank.scraped_at)).all()

            if not entries:
                continue

            current_entry = entries[0]
            current_rank = current_entry.organic_rank

            # Previous rank: most recent entry older than 7 days
            previous_entry = next(
                (e for e in entries if e.scraped_at <= cutoff_7d),
                None
            )
            previous_rank = previous_entry.organic_rank if previous_entry else None

            # Trend: lower rank number = better position
            if current_rank is None or previous_rank is None:
                trend = "unknown"
            elif current_rank < previous_rank:
                trend = "up"
            elif current_rank > previous_rank:
                trend = "down"
            else:
                trend = "stable"

            # Best (lowest number) and worst (highest number) ever
            all_organic_ranks = [
                e.organic_rank for e in entries if e.organic_rank is not None
            ]
            best_rank = min(all_organic_ranks) if all_organic_ranks else None
            worst_rank = max(all_organic_ranks) if all_organic_ranks else None

            result.append({
                "keyword": keyword,
                "current_organic_rank": current_rank,
                "current_sponsored_rank": current_entry.sponsored_rank,
                "previous_organic_rank": previous_rank,
                "trend": trend,
                "rank_change": (
                    (previous_rank - current_rank)
                    if current_rank is not None and previous_rank is not None
                    else None
                ),
                "best_rank_ever": best_rank,
                "worst_rank_ever": worst_rank,
                "total_results": current_entry.total_results,
                "last_scraped": current_entry.scraped_at.isoformat() if current_entry.scraped_at else None,
            })

        # Sort by current organic rank (None values last)
        result.sort(
            key=lambda x: (x["current_organic_rank"] is None, x["current_organic_rank"] or 0)
        )

        return result

    def get_portfolio_keyword_summary(self) -> Dict[str, Any]:
        """
        Across all user's products: keywords with rank 1-3 (winning),
        ranks 4-10 (competitive), ranks > 10 (needs work).

        Returns counts and lists.
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        product_ids = [p.id for p in products]
        product_map = {p.id: p.title for p in products}

        if not product_ids:
            return {
                "winning": {"count": 0, "keywords": []},
                "competitive": {"count": 0, "keywords": []},
                "needs_work": {"count": 0, "keywords": []},
                "unranked": {"count": 0, "keywords": []},
            }

        # Get the latest entry per (product_id, keyword)
        subq = self.db.query(
            KeywordRank.product_id,
            KeywordRank.keyword,
            func.max(KeywordRank.scraped_at).label("latest_at")
        ).filter(
            KeywordRank.product_id.in_(product_ids)
        ).group_by(
            KeywordRank.product_id,
            KeywordRank.keyword
        ).subquery()

        latest_ranks = self.db.query(KeywordRank).join(
            subq,
            and_(
                KeywordRank.product_id == subq.c.product_id,
                KeywordRank.keyword == subq.c.keyword,
                KeywordRank.scraped_at == subq.c.latest_at
            )
        ).all()

        winning = []
        competitive = []
        needs_work = []
        unranked = []

        for entry in latest_ranks:
            record = {
                "product_id": entry.product_id,
                "product_title": product_map.get(entry.product_id),
                "keyword": entry.keyword,
                "organic_rank": entry.organic_rank,
                "sponsored_rank": entry.sponsored_rank,
            }

            rank = entry.organic_rank

            if rank is None:
                unranked.append(record)
            elif 1 <= rank <= 3:
                winning.append(record)
            elif 4 <= rank <= 10:
                competitive.append(record)
            else:
                needs_work.append(record)

        return {
            "winning": {
                "count": len(winning),
                "label": "Rank 1-3",
                "keywords": sorted(winning, key=lambda x: x["organic_rank"] or 0)
            },
            "competitive": {
                "count": len(competitive),
                "label": "Rank 4-10",
                "keywords": sorted(competitive, key=lambda x: x["organic_rank"] or 0)
            },
            "needs_work": {
                "count": len(needs_work),
                "label": "Rank > 10",
                "keywords": sorted(needs_work, key=lambda x: x["organic_rank"] or 0)
            },
            "unranked": {
                "count": len(unranked),
                "label": "No rank recorded",
                "keywords": unranked
            },
        }

    def get_keyword_trend(
        self,
        product_id: int,
        keyword: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Daily rank history for one keyword on one product.

        Returns list of {date, organic_rank, sponsored_rank}.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return []

        cutoff = utcnow() - timedelta(days=days)

        entries = self.db.query(KeywordRank).filter(
            KeywordRank.product_id == product_id,
            KeywordRank.keyword == keyword,
            KeywordRank.scraped_at >= cutoff
        ).order_by(KeywordRank.scraped_at).all()

        return [
            {
                "date": entry.scraped_at.date().isoformat() if entry.scraped_at else None,
                "organic_rank": entry.organic_rank,
                "sponsored_rank": entry.sponsored_rank,
                "total_results": entry.total_results,
            }
            for entry in entries
        ]

    def add_keyword(self, product_id: int, keyword: str) -> Dict[str, Any]:
        """
        Placeholder method that creates a KeywordRank entry with None ranks.

        The actual rank data will be populated by the next scrape job.
        Returns the new record as a dict.
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found", "product_id": product_id}

        new_entry = KeywordRank(
            product_id=product_id,
            keyword=keyword,
            organic_rank=None,
            sponsored_rank=None,
            total_results=None,
            scraped_at=utcnow()
        )

        self.db.add(new_entry)
        self.db.commit()
        self.db.refresh(new_entry)

        return {
            "id": new_entry.id,
            "product_id": new_entry.product_id,
            "keyword": new_entry.keyword,
            "organic_rank": new_entry.organic_rank,
            "sponsored_rank": new_entry.sponsored_rank,
            "total_results": new_entry.total_results,
            "scraped_at": new_entry.scraped_at.isoformat() if new_entry.scraped_at else None,
            "status": "pending_scrape"
        }

    def get_rank_movements(self, days: int = 7) -> Dict[str, Any]:
        """
        Across all user's products/keywords: biggest rank improvements and
        drops in the period.

        Returns {improved: [...], declined: [...]}.
        Improvements = rank number decreased (moved closer to #1).
        Declines = rank number increased (moved further from #1).
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        product_ids = [p.id for p in products]
        product_map = {p.id: p.title for p in products}

        if not product_ids:
            return {"improved": [], "declined": []}

        now = utcnow()
        cutoff_start = now - timedelta(days=days)

        # Get unique product/keyword pairs
        keyword_pairs = self.db.query(
            KeywordRank.product_id,
            KeywordRank.keyword
        ).filter(
            KeywordRank.product_id.in_(product_ids)
        ).distinct().all()

        movements = []

        for product_id, keyword in keyword_pairs:
            # Most recent entry in the period (current)
            current_entry = self.db.query(KeywordRank).filter(
                KeywordRank.product_id == product_id,
                KeywordRank.keyword == keyword,
                KeywordRank.scraped_at >= cutoff_start
            ).order_by(desc(KeywordRank.scraped_at)).first()

            if current_entry is None or current_entry.organic_rank is None:
                continue

            # Most recent entry before the period (baseline)
            baseline_entry = self.db.query(KeywordRank).filter(
                KeywordRank.product_id == product_id,
                KeywordRank.keyword == keyword,
                KeywordRank.scraped_at < cutoff_start
            ).order_by(desc(KeywordRank.scraped_at)).first()

            if baseline_entry is None or baseline_entry.organic_rank is None:
                continue

            rank_change = baseline_entry.organic_rank - current_entry.organic_rank
            # Positive rank_change = improvement (rank number went down = better)

            if rank_change != 0:
                movements.append({
                    "product_id": product_id,
                    "product_title": product_map.get(product_id),
                    "keyword": keyword,
                    "rank_before": baseline_entry.organic_rank,
                    "rank_after": current_entry.organic_rank,
                    "rank_change": rank_change,
                    "direction": "improved" if rank_change > 0 else "declined",
                    "last_scraped": current_entry.scraped_at.isoformat() if current_entry.scraped_at else None,
                })

        improved = sorted(
            [m for m in movements if m["direction"] == "improved"],
            key=lambda x: x["rank_change"],
            reverse=True
        )
        declined = sorted(
            [m for m in movements if m["direction"] == "declined"],
            key=lambda x: x["rank_change"]
        )

        return {
            "period_days": days,
            "generated_at": now.isoformat(),
            "improved": improved,
            "declined": declined,
        }


def get_keyword_rank_service(db: Session, user: User) -> KeywordRankService:
    """Factory function for KeywordRankService"""
    return KeywordRankService(db, user)
