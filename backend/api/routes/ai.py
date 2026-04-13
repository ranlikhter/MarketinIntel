"""
AI-Powered Competitive Intelligence Routes

Endpoints:
  POST /ai/recommend/{product_id}  — Optimal price with plain-English reasoning
  POST /ai/query                   — Natural language question about your catalog
  POST /ai/narrative               — Generate weekly competitive summary (returns JSON)
  POST /ai/narrative/send          — Generate + email the narrative to the user
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from database.connection import get_db
from sqlalchemy import func
from database.models import (
    User, ProductMonitored, CompetitorMatch, PriceHistory, PriceAlert
)
from api.dependencies import get_current_user
from services.activity_service import log_activity

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_user_context(user: User, db: Session) -> dict:
    """Assemble compact catalog context for NL queries (batched — 3 queries total)."""
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).all()
    if not products:
        return {"products": [], "recent_changes": [], "metrics": {
            "total_products": 0, "total_competitors": 0,
            "cheapest_pct": 0, "expensive_pct": 0, "price_changes_last_week": 0,
        }}

    product_ids = [p.id for p in products]
    product_map = {p.id: p for p in products}

    # Batch query 1: all matches for all user products
    all_matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id.in_(product_ids)
    ).all()

    # Group matches by product; build latest_price map
    matches_by_product: dict[int, list] = {pid: [] for pid in product_ids}
    for m in all_matches:
        matches_by_product[m.monitored_product_id].append(m)

    # Batch query 2: price history in last 7 days for all matches
    cutoff = datetime.utcnow() - timedelta(days=7)
    match_ids = [m.id for m in all_matches]
    history_by_match: dict[int, list] = {m.id: [] for m in all_matches}
    if match_ids:
        hist_rows = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.match_id.in_(match_ids),
                PriceHistory.timestamp >= cutoff,
            )
            .order_by(PriceHistory.match_id, PriceHistory.timestamp.asc())
            .all()
        )
        for h in hist_rows:
            history_by_match[h.match_id].append(h)

    # Build product summaries (pure Python, no extra queries)
    prod_summaries = []
    for p in products:
        matches = matches_by_product.get(p.id, [])
        prices = [m.latest_price for m in matches if m.latest_price]
        if prices and p.my_price:
            if p.my_price <= min(prices):
                position = "cheapest"
            elif p.my_price >= max(prices):
                position = "most_expensive"
            else:
                position = "mid_range"
        else:
            position = "unknown"
        prod_summaries.append({
            "id": p.id,
            "title": p.title,
            "my_price": p.my_price,
            "competitor_count": len(matches),
            "my_position": position,
        })

    # Build recent changes (pure Python, no extra queries)
    recent_changes = []
    for match in all_matches:
        hist = history_by_match.get(match.id, [])
        if len(hist) >= 2 and hist[0].price != hist[-1].price:
            p = product_map[match.monitored_product_id]
            recent_changes.append({
                "product": p.title,
                "competitor": match.competitor_name,
                "old_price": hist[0].price,
                "new_price": hist[-1].price,
                "changed_at": hist[-1].timestamp.isoformat(),
            })

    # Simple position metrics
    positions = [p["my_position"] for p in prod_summaries]
    total = len(positions) or 1
    cheapest_pct = round(positions.count("cheapest") / total * 100)
    expensive_pct = round(positions.count("most_expensive") / total * 100)

    total_competitors = sum(p["competitor_count"] for p in prod_summaries)

    return {
        "products": prod_summaries,
        "recent_changes": recent_changes,
        "metrics": {
            "total_products": len(products),
            "total_competitors": total_competitors,
            "cheapest_pct": cheapest_pct,
            "expensive_pct": expensive_pct,
            "price_changes_last_week": len(recent_changes),
        },
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/recommend/{product_id}")
async def ai_pricing_recommendation(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get an AI-generated optimal price recommendation for a product.

    Claude analyses:
    - Your current price and cost margin
    - All competitor prices and stock status
    - 30-day price history trends
    - Your inventory level

    Returns a recommended price, confidence level, plain-English reasoning,
    and a trigger condition for when to reprice again.
    """
    from services.ai_service import get_pricing_recommendation

    product = db.query(ProductMonitored).filter(
        ProductMonitored.id == product_id,
        ProductMonitored.user_id == current_user.id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id == product.id
    ).all()

    # Build competitor list
    competitors = []
    for m in matches:
        competitors.append({
            "name": m.competitor_name,
            "price": m.latest_price,
            "stock_status": m.stock_status,
            "is_prime": m.is_prime,
            "last_scraped": m.last_scraped_at.isoformat() if m.last_scraped_at else None,
        })

    # 30-day price history
    cutoff = datetime.utcnow() - timedelta(days=30)
    history = []
    for m in matches:
        rows = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.match_id == m.id,
                PriceHistory.timestamp >= cutoff,
            )
            .order_by(PriceHistory.timestamp.asc())
            .all()
        )
        for row in rows:
            history.append({
                "competitor": m.competitor_name,
                "price": row.price,
                "timestamp": row.timestamp.isoformat(),
            })

    try:
        result = get_pricing_recommendation(
            product={
                "title": product.title,
                "sku": product.sku,
                "my_price": product.my_price,
                "cost_price": product.cost_price,
                "category": product.category,
            },
            competitors=competitors,
            price_history=history,
            inventory=product.inventory_quantity,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    log_activity(
        db, current_user.id, "ai.recommend", "product",
        f"AI pricing recommendation for '{product.title}'",
        entity_type="product", entity_id=product_id, entity_name=product.title,
        metadata={"recommended_price": result.get("recommended_price"),
                  "confidence": result.get("confidence")},
    )
    db.commit()

    return {
        "success": True,
        "product_id": product_id,
        "product_title": product.title,
        "current_price": product.my_price,
        "recommendation": result,
        "generated_at": datetime.utcnow().isoformat(),
    }


class QueryRequest(BaseModel):
    question: str
    max_products_in_context: int = 30


@router.post("/query")
async def ai_competitive_query(
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask any question about your competitive landscape in plain English.

    Examples:
    - *"Which of my products am I losing to Amazon?"*
    - *"Where do I have the most pricing power?"*
    - *"Which products should I reprice this week?"*
    - *"Are any of my competitors running promotions?"*
    - *"What's happening with my headphone category?"*

    Returns a conversational answer referencing specific products and prices
    from your catalog.
    """
    from services.ai_service import answer_competitive_query

    if not body.question or not body.question.strip():
        raise HTTPException(status_code=422, detail="question cannot be empty")

    if len(body.question) > 500:
        raise HTTPException(status_code=422, detail="question must be under 500 characters")

    context = _build_user_context(current_user, db)

    try:
        result = answer_competitive_query(body.question, context)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    log_activity(
        db, current_user.id, "ai.query", "user",
        f"AI query: {body.question[:80]}",
        metadata={"question_length": len(body.question)},
    )
    db.commit()

    return {
        "success": True,
        "question": body.question,
        "answer": result["answer"],
        "related_product_ids": result.get("related_product_ids", []),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/narrative")
async def generate_narrative(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate an AI-written weekly competitive intelligence narrative.

    Returns a 3-paragraph executive summary covering:
    1. What happened in the market this week (price movements)
    2. The biggest opportunity to act on
    3. The biggest threat to monitor

    Also returns an email-ready HTML version and subject line.
    Use `POST /ai/narrative/send` to deliver this directly to the user's email.
    """
    from services.ai_service import generate_weekly_narrative
    from services.insights_service import get_insights_service

    insights_svc = get_insights_service(db, current_user)
    context = _build_user_context(current_user, db)
    metrics = context["metrics"]
    metrics["alerts_fired"] = db.query(PriceAlert).filter(
        PriceAlert.user_id == current_user.id,
        PriceAlert.last_triggered_at >= datetime.utcnow() - timedelta(days=7),
    ).count()

    # Pull insights for narrative context
    try:
        opportunities = insights_svc.get_opportunities()
        threats = insights_svc.get_threats()
        top_opp = [{"title": o["title"], "description": o.get("description", "")}
                   for o in (opportunities or [])[:3]]
        top_threat = [{"title": t["title"], "description": t.get("description", "")}
                      for t in (threats or [])[:3]]
    except Exception:
        top_opp, top_threat = [], []

    # Top price changes for the week — batched (3 queries, not O(P×M×H))
    top_changes = []
    cutoff = datetime.utcnow() - timedelta(days=7)
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id
    ).all()
    _product_map = {p.id: p for p in products}
    _pid_list = [p.id for p in products]
    _all_matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id.in_(_pid_list)
    ).all() if _pid_list else []
    _mid_list = [m.id for m in _all_matches]
    _hist_rows = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.match_id.in_(_mid_list),
            PriceHistory.timestamp >= cutoff,
        )
        .order_by(PriceHistory.match_id.asc(), PriceHistory.timestamp.asc())
        .all()
    ) if _mid_list else []
    from collections import defaultdict as _dd
    _hist_by_match: dict = _dd(list)
    for _row in _hist_rows:
        _hist_by_match[_row.match_id].append(_row)
    for match in _all_matches:
        hist = _hist_by_match.get(match.id, [])
        if len(hist) >= 2:
            old_p, new_p = hist[0].price, hist[-1].price
            if old_p and new_p and old_p != new_p:
                change_pct = round(abs(new_p - old_p) / old_p * 100, 1)
                p = _product_map[match.monitored_product_id]
                top_changes.append({
                    "product": p.title,
                    "competitor": match.competitor_name,
                    "old_price": old_p,
                    "new_price": new_p,
                    "change_pct": change_pct,
                    "drop": new_p < old_p,
                })
    # Sort by magnitude
    top_changes.sort(key=lambda x: -x["change_pct"])
    top_changes = top_changes[:5]

    user_name = current_user.full_name or current_user.email.split("@")[0]

    try:
        narrative = generate_weekly_narrative(
            user_name=user_name,
            metrics=metrics,
            top_changes=top_changes,
            top_opportunities=top_opp,
            top_threats=top_threat,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    return {
        "success": True,
        "narrative": narrative,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/narrative/send")
async def send_narrative_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate the AI weekly narrative and send it to the user's email address.

    Combines narrative generation with email delivery in one call.
    Returns the generated narrative plus delivery status.
    """
    from services.email_service import email_service

    # Reuse narrative generation
    narrative_response = await generate_narrative(current_user=current_user, db=db)
    narrative = narrative_response["narrative"]

    try:
        sent = email_service.send_email(
            to_email=current_user.email,
            subject=narrative["subject"],
            html_content=narrative["html"],
            text_content=narrative["plain_text"],
        )
        delivery_status = "sent" if sent else "failed"
    except Exception as e:
        delivery_status = f"error: {str(e)}"
        sent = False

    log_activity(
        db, current_user.id, "ai.narrative.send", "user",
        f"AI narrative email {'sent' if sent else 'failed'} to {current_user.email}",
        metadata={"subject": narrative.get("subject"), "delivery_status": delivery_status},
    )
    db.commit()

    return {
        "success": sent,
        "delivery_status": delivery_status,
        "email": current_user.email,
        "subject": narrative.get("subject"),
        "narrative": narrative,
        "generated_at": narrative_response["generated_at"],
    }
