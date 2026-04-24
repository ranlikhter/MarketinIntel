"""
Simple Product Matcher
Basic product matching logic with tiered scoring:

  Tier 1 (score = 1.00) — Exact UPC/EAN barcode match  → definitively same product
  Tier 2 (score = 0.95) — Exact MPN match              → almost certainly same product
  Tier 3 (weighted)     — Title + brand + description   → fuzzy similarity fallback
  Tier 4 (image boost)  — CLIP cosine similarity        → second-pass for ambiguous scores

Image boost activates when text score is in the ambiguous zone (0.70–0.85).
It blends 60 % text + 40 % image and records both scores in match_confidence_detail.
Falls back silently to text-only when images are unavailable.
"""

from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

# Ambiguous text-score range where image matching adds the most value
_IMAGE_BOOST_LOW  = 0.70
_IMAGE_BOOST_HIGH = 0.85
# Weight split when both signals are available
_TEXT_WEIGHT  = 0.60
_IMAGE_WEIGHT = 0.40


class SimpleProductMatcher:
    """
    Product matching that uses exact identifiers first, then falls back to
    text similarity across title, brand, and description.  When a text score
    lands in the ambiguous zone, a CLIP image embedding comparison is used
    as a tiebreaker.
    """

    def __init__(self, threshold: float = 0.6):
        """
        Args:
            threshold: Minimum similarity score (0.0-1.0) to consider a match.
                       Exact identifier matches always exceed this threshold.
        """
        self.threshold = threshold

    def match(
        self,
        product: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        use_image: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Find best matching product from candidates.

        Args:
            product:    Product dict with 'title', 'brand', 'description',
                        'mpn', 'upc_ean', optionally 'image_url'.
            candidates: List of candidate products to match against,
                        each optionally containing 'image_url'.
            use_image:  Enable CLIP image second-pass for ambiguous scores.
                        Disabled by default to keep unit tests fast.

        Returns:
            Best matching candidate (with 'match_score' and
            'match_confidence_detail' keys added), or None.
        """
        if not candidates:
            return None

        best_match = None
        best_score = 0.0
        best_text_score = 0.0
        best_image_score: Optional[float] = None

        for candidate in candidates:
            text_score = self._calculate_similarity(product, candidate)
            score = text_score
            image_score: Optional[float] = None

            if use_image and _IMAGE_BOOST_LOW <= text_score <= _IMAGE_BOOST_HIGH:
                image_score = self._image_similarity(
                    product.get("image_url"),
                    candidate.get("image_url"),
                )
                if image_score is not None:
                    score = text_score * _TEXT_WEIGHT + image_score * _IMAGE_WEIGHT

            if score > best_score and score >= self.threshold:
                best_score = score
                best_match = candidate
                best_text_score = text_score
                best_image_score = image_score

        if best_match:
            best_match["match_score"] = best_score
            best_match["match_confidence_detail"] = {
                "text": round(best_text_score, 3),
                "image": round(best_image_score, 3) if best_image_score is not None else None,
                "method": "text+image" if best_image_score is not None else "text_only",
            }

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

    @staticmethod
    def _image_similarity(url1: Optional[str], url2: Optional[str]) -> Optional[float]:
        """
        Return CLIP cosine similarity [0, 1] between the two image URLs.
        Returns None if either image is unavailable or the model fails.
        """
        if not url1 or not url2:
            return None
        try:
            from matchers.image_matcher import compare_urls
            return compare_urls(url1, url2)
        except Exception:
            return None

    def batch_match(
        self,
        products: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        use_image: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Match multiple products against candidates.

        Returns:
            List of dicts: {'product': ..., 'match': ..., 'score': float}
        """
        matches = []
        for product in products:
            match = self.match(product, candidates, use_image=use_image)
            if match:
                matches.append({
                    'product': product,
                    'match': match,
                    'score': match.get('match_score', 0.0)
                })
        return matches
