"""
AI-Powered Product Matcher
Uses sentence-transformers for semantic similarity matching
"""

try:
    from sentence_transformers import SentenceTransformer, util as st_util
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment,misc]
    st_util = None  # type: ignore[assignment]
import numpy as np
from typing import List, Dict, Tuple, Optional
import re
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AIProductMatcher:
    """
    Advanced product matching using machine learning embeddings

    Features:
    - Semantic similarity (understands meaning, not just keywords)
    - Brand-aware matching
    - Multi-field comparison (title, description, specs)
    - Confidence scoring with explanation
    - Learning from user feedback
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the AI matcher

        Args:
            model_name: Hugging Face model name
                - 'all-MiniLM-L6-v2' (fast, lightweight, good accuracy) - DEFAULT
                - 'paraphrase-multilingual-mpnet-base-v2' (multilingual)
                - 'all-mpnet-base-v2' (best accuracy, slower)
        """
        try:
            logger.info(f"Loading AI model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info("AI model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load AI model: {e}")
            raise

    def preprocess_text(self, text: str) -> str:
        """
        Clean and normalize text for better matching

        Args:
            text: Raw product title or description

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove common noise words but keep important ones
        # (Don't remove too much - embeddings handle context well)
        noise_patterns = [
            r'\[.*?\]',  # Remove [brackets]
            r'\(.*?\)',  # Remove (parentheses)
            r'https?://\S+',  # Remove URLs
        ]

        for pattern in noise_patterns:
            text = re.sub(pattern, '', text)

        return text.strip()

    def extract_brand(self, text: str) -> Optional[str]:
        """
        Extract brand name from product title

        Common patterns:
        - "Apple iPhone 13"
        - "Samsung Galaxy S21"
        - "Sony WH-1000XM5"
        """
        # List of common brands (can be expanded)
        brands = [
            'apple', 'samsung', 'sony', 'lg', 'dell', 'hp', 'lenovo',
            'microsoft', 'google', 'amazon', 'nike', 'adidas', 'canon',
            'nikon', 'panasonic', 'philips', 'bosch', 'intel', 'amd',
            'nvidia', 'asus', 'acer', 'toshiba', 'bose', 'jbl'
        ]

        text_lower = text.lower()
        words = text_lower.split()

        # Check first 3 words for brand
        for word in words[:3]:
            if word in brands:
                return word

        return None

    def calculate_similarity(
        self,
        product_title: str,
        competitor_title: str,
        product_description: Optional[str] = None,
        competitor_description: Optional[str] = None
    ) -> Dict:
        """
        Calculate semantic similarity between products using AI

        Args:
            product_title: Your product title
            competitor_title: Competitor's product title
            product_description: Your product description (optional)
            competitor_description: Competitor's description (optional)

        Returns:
            Dict with:
                - score: Overall match score (0-100)
                - confidence: Confidence level ('high', 'medium', 'low')
                - title_similarity: Title-only score
                - brand_match: Boolean
                - explanation: Human-readable explanation
        """
        # Preprocess titles
        prod_clean = self.preprocess_text(product_title)
        comp_clean = self.preprocess_text(competitor_title)

        # Extract brands
        prod_brand = self.extract_brand(product_title)
        comp_brand = self.extract_brand(competitor_title)
        brand_match = (prod_brand == comp_brand) if (prod_brand and comp_brand) else None

        # Generate embeddings for titles
        prod_embedding = self.model.encode(prod_clean, convert_to_tensor=True)
        comp_embedding = self.model.encode(comp_clean, convert_to_tensor=True)

        # Calculate cosine similarity
        title_similarity = st_util.cos_sim(prod_embedding, comp_embedding).item()
        title_score = title_similarity * 100  # Convert to 0-100

        # If descriptions provided, include them
        description_score = None
        if product_description and competitor_description:
            prod_desc_clean = self.preprocess_text(product_description)
            comp_desc_clean = self.preprocess_text(competitor_description)

            prod_desc_emb = self.model.encode(prod_desc_clean, convert_to_tensor=True)
            comp_desc_emb = self.model.encode(comp_desc_clean, convert_to_tensor=True)

            desc_similarity = st_util.cos_sim(prod_desc_emb, comp_desc_emb).item()
            description_score = desc_similarity * 100

        # Calculate overall score
        if description_score is not None:
            # Weighted average: title 70%, description 30%
            overall_score = (title_score * 0.7) + (description_score * 0.3)
        else:
            overall_score = title_score

        # Brand matching boost/penalty
        if brand_match is True:
            overall_score = min(100, overall_score * 1.15)  # 15% boost
        elif brand_match is False:
            overall_score = overall_score * 0.5  # 50% penalty (different brands)

        # Determine confidence level
        if overall_score >= 85:
            confidence = 'high'
            explanation = "Strong semantic match with high confidence"
        elif overall_score >= 70:
            confidence = 'medium'
            explanation = "Good semantic similarity, likely the same product"
        elif overall_score >= 50:
            confidence = 'low'
            explanation = "Moderate similarity, manual review recommended"
        else:
            confidence = 'very_low'
            explanation = "Low similarity, likely different products"

        # Add brand info to explanation
        if brand_match is True:
            explanation += " (brands match)"
        elif brand_match is False:
            explanation += " (WARNING: different brands detected)"

        return {
            'score': round(overall_score, 2),
            'confidence': confidence,
            'title_similarity': round(title_score, 2),
            'description_similarity': round(description_score, 2) if description_score else None,
            'brand_match': brand_match,
            'product_brand': prod_brand,
            'competitor_brand': comp_brand,
            'explanation': explanation,
            'model_used': self.model_name
        }

    def batch_match(
        self,
        product_title: str,
        competitor_products: List[Dict],
        top_k: int = 5,
        min_score: float = 50.0
    ) -> List[Dict]:
        """
        Match one product against multiple competitor products

        Args:
            product_title: Your product title
            competitor_products: List of competitor products
                Each dict should have: {'title': str, 'description': str (optional)}
            top_k: Return top K matches
            min_score: Minimum score threshold

        Returns:
            List of top matches with scores, sorted by score descending
        """
        results = []

        for comp_prod in competitor_products:
            match_result = self.calculate_similarity(
                product_title=product_title,
                competitor_title=comp_prod['title'],
                product_description=None,
                competitor_description=comp_prod.get('description')
            )

            # Only include if above minimum score
            if match_result['score'] >= min_score:
                results.append({
                    'competitor_product': comp_prod,
                    'match': match_result
                })

        # Sort by score descending
        results.sort(key=lambda x: x['match']['score'], reverse=True)

        # Return top K
        return results[:top_k]

    def explain_match(self, match_result: Dict) -> str:
        """
        Generate detailed human-readable explanation

        Args:
            match_result: Result from calculate_similarity()

        Returns:
            Formatted explanation string
        """
        score = match_result['score']
        confidence = match_result['confidence']
        brand_match = match_result['brand_match']

        explanation = f"Match Score: {score:.1f}/100 (Confidence: {confidence})\n\n"

        if confidence == 'high':
            explanation += "✅ This appears to be the same product with high confidence.\n"
        elif confidence == 'medium':
            explanation += "⚠️ Likely the same product, but manual verification recommended.\n"
        elif confidence == 'low':
            explanation += "⚠️ Low confidence - these may be different products.\n"
        else:
            explanation += "❌ Very low confidence - likely different products.\n"

        explanation += f"\nTitle Similarity: {match_result['title_similarity']:.1f}%\n"

        if match_result['description_similarity']:
            explanation += f"Description Similarity: {match_result['description_similarity']:.1f}%\n"

        if brand_match is True:
            explanation += "\n✅ Brands match: Both are " + match_result['product_brand'].upper()
        elif brand_match is False:
            explanation += f"\n⚠️ Brand mismatch: {match_result['product_brand']} vs {match_result['competitor_brand']}"
        else:
            explanation += "\n⚠️ Could not detect brands from product titles"

        explanation += f"\n\nAI Model: {match_result['model_used']}"

        return explanation

    def update_from_feedback(
        self,
        product_title: str,
        competitor_title: str,
        user_confirmed: bool
    ):
        """
        Learn from user feedback (future enhancement)

        This would store user confirmations/rejections to fine-tune
        the matching algorithm over time.

        Args:
            product_title: Your product
            competitor_title: Competitor product
            user_confirmed: True if user confirmed it's a match
        """
        # Persist feedback to a JSON file alongside the data directory.
        # Over time this log can be used to:
        #   - Adjust match thresholds (e.g. if AI says 85% but user rejects)
        #   - Fine-tune or retrain the embedding model
        try:
            # Resolve feedback file relative to repo root (../../data/)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            feedback_file = os.path.join(base_dir, "..", "data", "match_feedback.json")
            feedback_file = os.path.normpath(feedback_file)

            existing: List[Dict] = []
            if os.path.exists(feedback_file):
                with open(feedback_file, "r") as f:
                    existing = json.load(f)

            # Calculate the AI score for this pair
            result = self.calculate_similarity(product_title, competitor_title)

            existing.append({
                "product_title": product_title,
                "competitor_title": competitor_title,
                "ai_score": result["score"],
                "user_confirmed": user_confirmed,
                "timestamp": datetime.utcnow().isoformat(),
            })

            os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
            with open(feedback_file, "w") as f:
                json.dump(existing, f, indent=2)

            logger.info(
                f"Feedback stored: confirmed={user_confirmed}, ai_score={result['score']:.1f}"
            )
        except Exception as e:
            logger.error(f"Failed to store match feedback: {e}")


# Singleton instance
_ai_matcher = None

def get_ai_matcher() -> AIProductMatcher:
    """Get or create AI matcher singleton"""
    global _ai_matcher
    if _ai_matcher is None:
        _ai_matcher = AIProductMatcher()
    return _ai_matcher
