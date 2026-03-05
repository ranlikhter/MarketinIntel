"""
Competitor Strategy DNA API

Exposes competitor pricing personality profiles, predictive strike alerts,
real-time change classification, and repricing simulation.

Endpoints:
  GET  /competitor-dna/profiles                       — All competitor DNA profiles
  GET  /competitor-dna/profiles/{competitor_name}     — Single competitor's full DNA
  GET  /competitor-dna/strike-predictions             — Next 7-day strike forecast
  POST /competitor-dna/classify                       — HOLD / RESPOND / IGNORE classifier
  POST /competitor-dna/simulate                       — "Before You Reprice" simulation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.connection import get_db
from database.models import User
from api.dependencies import get_current_user
from services.competitor_dna_service import get_competitor_dna_service

router = APIRouter(prefix="/competitor-dna", tags=["Competitor Strategy DNA"])


# ─── Request models ───────────────────────────────────────────────────────────

class ClassifyChangeRequest(BaseModel):
    competitor_name: str
    product_id: int
    old_price: float
    new_price: float


class SimulateRepriceRequest(BaseModel):
    product_id: int
    proposed_price: float


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/profiles")
async def get_all_dna_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return DNA profiles for every competitor you monitor.

    A DNA profile reveals a competitor's pricing *personality*:
    - **Strike patterns** — which days and hours they typically change prices
    - **Revert rate** — what % of their price drops are temporary promos vs permanent cuts
    - **Aggression score** — how often they hold the lowest price (0–100)
    - **Response lag** — how fast they react when market prices shift
    - **Strike prediction** — probability they'll move this week + most likely window
    - **AI summary** — plain-English personality description

    Profiles with fewer than 3 historical price changes are flagged
    as `sufficient_data: false` — more scrape history is needed.
    """
    svc = get_competitor_dna_service(db, current_user)
    try:
        return svc.get_all_profiles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{competitor_name}")
async def get_dna_profile(
    competitor_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the full DNA profile for a single competitor.

    Returns all strike pattern data, revert analysis, response lag,
    aggression score, and an AI-written personality summary.

    Example competitor names: `Amazon`, `Best Buy`, `Walmart`
    (must match the competitor name stored in your matches).
    """
    svc = get_competitor_dna_service(db, current_user)
    try:
        profile = svc.get_competitor_dna(competitor_name)
        if not profile.get("sufficient_data") and "error" not in profile:
            return profile  # Return partial profile with message rather than 404
        if "error" in profile:
            raise HTTPException(status_code=404, detail=profile["error"])
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strike-predictions")
async def get_strike_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Predict upcoming price changes across all your competitors for the next 7 days.

    Returns:
    - **predictions** — ranked list of competitors likely to move, with probability score
    - **calendar** — grouped by most-likely day for a visual calendar view

    Each prediction includes:
    - Probability (0–100%)
    - Most likely strike window (day + UTC hours)
    - Expected drop magnitude
    - Whether the expected strike is a promo (likely to revert) or permanent

    Only competitors with ≥20% strike probability are included.
    """
    svc = get_competitor_dna_service(db, current_user)
    try:
        return svc.get_strike_predictions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify")
async def classify_price_change(
    body: ClassifyChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Classify a detected price change as **HOLD**, **RESPOND**, or **IGNORE**.

    Call this endpoint the moment you detect a competitor price change to get
    an instant, data-driven recommendation:

    - **HOLD** — This is almost certainly a temporary promo. Don't reprice.
      Wait 48–72 h and check again.
    - **RESPOND** — This is a permanent competitive move. Review and act.
    - **IGNORE** — This is a price raise or an outlier. No action needed.

    The classification is based on:
    1. Live promo signals (lightning deal badges, coupons, strike-through prices)
    2. The competitor's historical revert rate from their DNA profile
    3. Whether today matches their typical strike day
    4. The magnitude of the change vs their historical average

    An AI narrative explains the reasoning in plain English.
    """
    svc = get_competitor_dna_service(db, current_user)
    try:
        return svc.classify_price_change(
            competitor_name=body.competitor_name,
            product_id=body.product_id,
            old_price=body.old_price,
            new_price=body.new_price,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate")
async def simulate_reprice(
    body: SimulateRepriceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    **"Before You Reprice"** — simulate how competitors will respond if you
    change your price to `proposed_price`.

    Returns a projected market state at T+24h, T+48h, and T+72h showing:
    - Which competitors are likely to react and when
    - Their projected prices after reacting
    - Your projected rank in the market at each time horizon
    - Whether you'll still be the cheapest after the dust settles

    Also returns an AI recommendation: should you proceed with this reprice?

    This prevents the most common e-commerce pricing mistake: dropping your
    price only to trigger a race to the bottom where you end up at the same
    relative position but with lower margins for everyone.
    """
    svc = get_competitor_dna_service(db, current_user)
    try:
        return svc.simulate_reprice(
            product_id=body.product_id,
            proposed_price=body.proposed_price,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
