"""
Simple Product Matcher
Basic product matching logic with tiered scoring:

  Tier 1 (score = 1.00) — Exact UPC/EAN barcode match  → definitively same product
  Tier 2 (score = 0.95) — Exact MPN match              → almost certainly same product
  Tier 3 (weighted)     — Title + brand + description   → fuzzy similarity fallback
"""

from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher


class SimpleProductMatcher:
    """
    Product matching that uses exact identifiers first, then falls back to
    text similarity across title, brand, and description.
    """

    def __init__(self, threshold: float = 0.6):
        """
        Initialize matcher.

        Args:
            threshold: Minimum similarity score (0.0-1.0) to consider a match.
                       Exact identifier matches always exceed this threshold.
        """
        self.threshold = threshold

    def match(self, product: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find best matching product from candidates.

        Args:
            product: Product dict with 'title', 'brand', 'description',
                     'mpn', 'upc_ean', etc.
            candidates: List of candidate products to match against.

        Returns:
            Best matching candidate (with 'match_score' key added), or None.
        """
        if not candidates:
            return None

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self._calculate_similarity(product, candidate)
            if score > best_score and score >= self.threshold:
                best_score = score
                best_match = candidate

        if best_match:
            best_match['match_score'] = best_score

        return best_match

    def _calculate_similarity(self, p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
        """
        Calculate similarity score between two products using tiered logic.

        Tier 1 — Exact UPC/EAN: returns 1.0 immediately (same barcode = same product).
        Tier 2 — Exact MPN:     returns 0.95 immediately (manufacturer part number match).
        Tier 3 — Text similarity across title (55%), brand (25%), description (20%).

        Returns:
            Score between 0.0 and 1.0.
        """
        # --- Tier 1: Exact barcode match ---
        upc1 = (p1.get('upc_ean') or '').strip()
        upc2 = (p2.get('upc_ean') or '').strip()
        if upc1 and upc2 and upc1 == upc2:
            return 1.0

        # --- Tier 2: Exact MPN match (case-insensitive) ---
        mpn1 = (p1.get('mpn') or '').strip().upper()
        mpn2 = (p2.get('mpn') or '').strip().upper()
        if mpn1 and mpn2 and mpn1 == mpn2:
            return 0.95

        # --- Tier 3: Weighted text similarity ---
        title1 = (p1.get('title') or '').lower()
        title2 = (p2.get('title') or '').lower()
        brand1 = (p1.get('brand') or '').lower()
        brand2 = (p2.get('brand') or '').lower()
        desc1 = (p1.get('description') or '').lower()
        desc2 = (p2.get('description') or '').lower()

        title_sim = SequenceMatcher(None, title1, title2).ratio()

        # Brand: full score when both provided, neutral 0.5 when one is missing
        if brand1 and brand2:
            brand_sim = SequenceMatcher(None, brand1, brand2).ratio()
        else:
            brand_sim = 0.5

        # Description: full similarity when both non-empty, neutral 0.5 otherwise
        if desc1 and desc2:
            # Compare first 300 chars to keep matching fast
            desc_sim = SequenceMatcher(None, desc1[:300], desc2[:300]).ratio()
        else:
            desc_sim = 0.5

        score = (title_sim * 0.55) + (brand_sim * 0.25) + (desc_sim * 0.20)
        return score

    def batch_match(
        self,
        products: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match multiple products against candidates.

        Returns:
            List of dicts: {'product': ..., 'match': ..., 'score': float}
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
