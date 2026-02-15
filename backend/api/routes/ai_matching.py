"""
AI Matching API Endpoints
Manage AI-powered product matching and review
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, CompetitorWebsite
from matchers.ai_matcher import get_ai_matcher

router = APIRouter(prefix="/ai-matching", tags=["AI Matching"])


# Pydantic models
class MatchRequest(BaseModel):
    product_title: str
    competitor_title: str
    product_description: Optional[str] = None
    competitor_description: Optional[str] = None


class BatchMatchRequest(BaseModel):
    product_id: int
    competitor_products: List[dict]
    top_k: int = 5
    min_score: float = 50.0


class MatchReview(BaseModel):
    match_id: int
    approved: bool
    notes: Optional[str] = None


class MatchResponse(BaseModel):
    score: float
    confidence: str
    title_similarity: float
    description_similarity: Optional[float]
    brand_match: Optional[bool]
    product_brand: Optional[str]
    competitor_brand: Optional[str]
    explanation: str
    model_used: str


# ============================================
# AI Matching Endpoints
# ============================================

@router.post("/compare", response_model=MatchResponse)
async def compare_products(request: MatchRequest):
    """
    Compare two product titles using AI semantic similarity

    - **product_title**: Your product title
    - **competitor_title**: Competitor's product title
    - **product_description**: Optional description for better accuracy
    - **competitor_description**: Optional competitor description

    Returns match score (0-100) with confidence level and explanation
    """
    try:
        matcher = get_ai_matcher()

        result = matcher.calculate_similarity(
            product_title=request.product_title,
            competitor_title=request.competitor_title,
            product_description=request.product_description,
            competitor_description=request.competitor_description
        )

        return MatchResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI matching failed: {str(e)}")


@router.post("/batch-match")
async def batch_match_products(
    request: BatchMatchRequest,
    db: Session = Depends(get_db)
):
    """
    Match one product against multiple competitor products

    - **product_id**: Your product ID
    - **competitor_products**: List of competitor products to match against
    - **top_k**: Return top K matches (default: 5)
    - **min_score**: Minimum score threshold (default: 50.0)

    Returns top matches sorted by score
    """
    # Get product
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == request.product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        matcher = get_ai_matcher()

        results = matcher.batch_match(
            product_title=product.title,
            competitor_products=request.competitor_products,
            top_k=request.top_k,
            min_score=request.min_score
        )

        return {
            'success': True,
            'product_id': product.id,
            'product_title': product.title,
            'matches_found': len(results),
            'matches': results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch matching failed: {str(e)}")


@router.post("/rematch/{product_id}")
async def rematch_product_with_ai(
    product_id: int,
    min_score: float = 70.0,
    db: Session = Depends(get_db)
):
    """
    Re-calculate match scores for existing competitor matches using AI

    - **product_id**: Product to re-match
    - **min_score**: Update only if new score is above this threshold

    Updates match_score for all existing CompetitorMatch records
    """
    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.product_id == product_id
    ).all()

    if not matches:
        return {
            'success': True,
            'message': 'No existing matches to re-calculate',
            'updated': 0
        }

    try:
        matcher = get_ai_matcher()
        updated = 0

        for match in matches:
            # Calculate new AI score
            result = matcher.calculate_similarity(
                product_title=product.title,
                competitor_title=match.competitor_product_title
            )

            new_score = result['score']

            # Update if above threshold
            if new_score >= min_score:
                match.match_score = new_score
                match.last_scraped_at = datetime.utcnow()
                updated += 1
            else:
                # Optionally delete low-confidence matches
                # db.delete(match)
                pass

        db.commit()

        return {
            'success': True,
            'product_id': product_id,
            'matches_checked': len(matches),
            'updated': updated,
            'message': f'Updated {updated} matches with AI scores'
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Rematch failed: {str(e)}")


@router.get("/pending-review")
async def get_pending_matches(
    min_score: float = 50.0,
    max_score: float = 85.0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get matches that need manual review

    - **min_score**: Minimum match score (default: 50)
    - **max_score**: Maximum match score (default: 85)
    - **limit**: Max results to return

    Returns matches with medium confidence that need human verification
    """
    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.match_score >= min_score,
        CompetitorMatch.match_score <= max_score
    ).order_by(CompetitorMatch.match_score.desc()).limit(limit).all()

    results = []
    for match in matches:
        product = db.query(ProductMonitored).filter(
            ProductMonitored.id == match.product_id
        ).first()

        results.append({
            'match_id': match.id,
            'product_id': match.product_id,
            'product_title': product.title if product else "Unknown",
            'competitor_name': match.competitor_name,
            'competitor_title': match.competitor_product_title,
            'competitor_url': match.competitor_url,
            'match_score': match.match_score,
            'latest_price': match.latest_price,
            'last_scraped': match.last_scraped_at.isoformat() if match.last_scraped_at else None
        })

    return {
        'success': True,
        'pending_count': len(results),
        'matches': results
    }


@router.post("/review")
async def review_match(review: MatchReview, db: Session = Depends(get_db)):
    """
    Approve or reject a match (provides feedback to AI)

    - **match_id**: ID of the match to review
    - **approved**: True to approve, False to reject
    - **notes**: Optional notes about the decision

    This feedback helps improve future AI matching accuracy
    """
    match = db.query(CompetitorMatch).filter(
        CompetitorMatch.id == review.match_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == match.product_id
    ).first()

    try:
        matcher = get_ai_matcher()

        if review.approved:
            # User confirmed - boost confidence
            match.match_score = min(100, match.match_score * 1.1)

            # Record feedback for learning
            matcher.update_from_feedback(
                product_title=product.title,
                competitor_title=match.competitor_product_title,
                user_confirmed=True
            )

            message = "Match approved and confidence boosted"

        else:
            # User rejected - delete match or mark as rejected
            db.delete(match)

            # Record negative feedback
            matcher.update_from_feedback(
                product_title=product.title,
                competitor_title=match.competitor_product_title,
                user_confirmed=False
            )

            message = "Match rejected and removed"

        db.commit()

        return {
            'success': True,
            'match_id': review.match_id,
            'approved': review.approved,
            'message': message
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


@router.get("/stats")
async def get_matching_stats(db: Session = Depends(get_db)):
    """
    Get AI matching statistics

    Returns overall matching accuracy and distribution
    """
    from sqlalchemy import func

    total_matches = db.query(CompetitorMatch).count()

    # Count by confidence level
    high_confidence = db.query(CompetitorMatch).filter(
        CompetitorMatch.match_score >= 85
    ).count()

    medium_confidence = db.query(CompetitorMatch).filter(
        CompetitorMatch.match_score >= 70,
        CompetitorMatch.match_score < 85
    ).count()

    low_confidence = db.query(CompetitorMatch).filter(
        CompetitorMatch.match_score >= 50,
        CompetitorMatch.match_score < 70
    ).count()

    very_low = db.query(CompetitorMatch).filter(
        CompetitorMatch.match_score < 50
    ).count()

    # Average score
    avg_score = db.query(func.avg(CompetitorMatch.match_score)).scalar() or 0

    return {
        'total_matches': total_matches,
        'average_score': round(avg_score, 2),
        'distribution': {
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'very_low': very_low
        },
        'percentages': {
            'high': round((high_confidence / total_matches * 100), 1) if total_matches else 0,
            'medium': round((medium_confidence / total_matches * 100), 1) if total_matches else 0,
            'low': round((low_confidence / total_matches * 100), 1) if total_matches else 0,
            'very_low': round((very_low / total_matches * 100), 1) if total_matches else 0
        }
    }


@router.post("/explain/{match_id}")
async def explain_match(match_id: int, db: Session = Depends(get_db)):
    """
    Get detailed explanation of why AI matched these products

    - **match_id**: ID of the match to explain

    Returns human-readable explanation with confidence factors
    """
    match = db.query(CompetitorMatch).filter(
        CompetitorMatch.id == match_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == match.product_id
    ).first()

    try:
        matcher = get_ai_matcher()

        # Re-calculate to get detailed explanation
        result = matcher.calculate_similarity(
            product_title=product.title,
            competitor_title=match.competitor_product_title
        )

        explanation = matcher.explain_match(result)

        return {
            'success': True,
            'match_id': match_id,
            'product_title': product.title,
            'competitor_title': match.competitor_product_title,
            'current_score': match.match_score,
            'recalculated_score': result['score'],
            'explanation': explanation,
            'detailed_result': result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")
