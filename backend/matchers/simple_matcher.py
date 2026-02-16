"""
Simple Product Matcher
Basic product matching logic
"""

from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher


class SimpleProductMatcher:
    """
    Simple product matching based on title/brand similarity
    """

    def __init__(self, threshold: float = 0.6):
        """
        Initialize matcher

        Args:
            threshold: Minimum similarity score (0.0-1.0) to consider a match
        """
        self.threshold = threshold

    def match(self, product: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find best matching product from candidates

        Args:
            product: Product dict with 'title', 'brand', etc.
            candidates: List of candidate products to match against

        Returns:
            Best matching candidate or None if no good match found
        """
        if not candidates:
            return None

        best_match = None
        best_score = 0.0

        product_title = product.get('title', '').lower()
        product_brand = product.get('brand', '').lower()

        for candidate in candidates:
            score = self._calculate_similarity(
                product_title,
                product_brand,
                candidate.get('title', '').lower(),
                candidate.get('brand', '').lower()
            )

            if score > best_score and score >= self.threshold:
                best_score = score
                best_match = candidate

        if best_match:
            best_match['match_score'] = best_score

        return best_match

    def _calculate_similarity(
        self,
        title1: str,
        brand1: str,
        title2: str,
        brand2: str
    ) -> float:
        """
        Calculate similarity score between two products

        Returns:
            Score between 0.0 and 1.0
        """
        # Title similarity (70% weight)
        title_sim = SequenceMatcher(None, title1, title2).ratio()

        # Brand similarity (30% weight)
        brand_sim = SequenceMatcher(None, brand1, brand2).ratio() if brand1 and brand2 else 0.5

        # Weighted average
        score = (title_sim * 0.7) + (brand_sim * 0.3)

        return score

    def batch_match(
        self,
        products: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match multiple products against candidates

        Returns:
            List of matches with scores
        """
        matches = []

        for product in products:
            match = self.match(product, candidates)
            if match:
                matches.append({
                    'product': product,
                    'match': match,
                    'score': match.get('match_score', 0.0)
                })

        return matches
