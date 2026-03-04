from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import stripe
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import User, SubscriptionTier, SubscriptionStatus
from api.dependencies import get_current_user

router = APIRouter()

# ── Stripe webhook idempotency cache ──────────────────────────────────────────
# Stripe retries webhooks on 5xx responses.  We track processed event IDs for
# 24 h (Stripe's retry window) so we can return 200 without reprocessing.
# For multi-worker deployments this should move to Redis; this in-process dict
# is correct for single-worker setups and degrades gracefully (one duplicate
# per worker restart at worst, which Stripe's retry window makes rare).
_PROCESSED_EVENTS: OrderedDict = OrderedDict()  # event_id -> timestamp
_PROCESSED_EVENTS_LOCK = threading.Lock()
_EVENT_TTL = 86_400   # 24 hours
_EVENT_MAX_SIZE = 5_000


def _is_event_processed(event_id: str) -> bool:
    """Return True if already processed; False + register if new."""
    now = time.time()
    with _PROCESSED_EVENTS_LOCK:
        # Evict stale entries (OrderedDict keeps insertion order)
        while _PROCESSED_EVENTS:
            oldest_id, ts = next(iter(_PROCESSED_EVENTS.items()))
            if now - ts > _EVENT_TTL:
                _PROCESSED_EVENTS.popitem(last=False)
            else:
                break
        if event_id in _PROCESSED_EVENTS:
            return True
        while len(_PROCESSED_EVENTS) >= _EVENT_MAX_SIZE:
            _PROCESSED_EVENTS.popitem(last=False)
        _PROCESSED_EVENTS[event_id] = now
        return False

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Stripe Price IDs (you'll need to create these in Stripe Dashboard)
STRIPE_PRICES = {
    "PRO_MONTHLY": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly"),
    "PRO_YEARLY": os.getenv("STRIPE_PRICE_PRO_YEARLY", "price_pro_yearly"),
    "BUSINESS_MONTHLY": os.getenv("STRIPE_PRICE_BUSINESS_MONTHLY", "price_business_monthly"),
    "BUSINESS_YEARLY": os.getenv("STRIPE_PRICE_BUSINESS_YEARLY", "price_business_yearly"),
    "ENTERPRISE_MONTHLY": os.getenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", "price_enterprise_monthly"),
    "ENTERPRISE_YEARLY": os.getenv("STRIPE_PRICE_ENTERPRISE_YEARLY", "price_enterprise_yearly"),
}

# Pydantic Models
class CheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: Optional[str] = "http://localhost:3000/dashboard?success=true"
    cancel_url: Optional[str] = "http://localhost:3000/pricing?canceled=true"

class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str

class PortalSessionRequest(BaseModel):
    return_url: Optional[str] = "http://localhost:3000/settings"

class PortalSessionResponse(BaseModel):
    url: str

class SubscriptionInfo(BaseModel):
    tier: str
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription upgrade
    """
    try:
        # Create or retrieve Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={
                    "user_id": str(current_user.id),
                }
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        else:
            customer = stripe.Customer.retrieve(current_user.stripe_customer_id)

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": request.price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": str(current_user.id),
            }
        )

        return CheckoutSessionResponse(
            session_id=checkout_session.id,
            url=checkout_session.url
        )

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    request: PortalSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session for managing subscription
    """
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No subscription found. Please subscribe to a plan first."
        )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=request.return_url,
        )

        return PortalSessionResponse(url=portal_session.url)

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


@router.get("/subscription", response_model=SubscriptionInfo)
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's subscription information
    """
    return SubscriptionInfo(
        tier=current_user.subscription_tier.value,
        status=current_user.subscription_status.value if current_user.subscription_status else "inactive",
        current_period_end=current_user.subscription_current_period_end,
        cancel_at_period_end=current_user.subscription_cancel_at_period_end or False,
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency guard — Stripe retries on 5xx, so skip already-processed events
    if _is_event_processed(event["id"]):
        return {"status": "already_processed"}

    # Handle different event types
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session, db)

    elif event["type"] == "customer.subscription.created":
        subscription = event["data"]["object"]
        await handle_subscription_created(subscription, db)

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        await handle_subscription_updated(subscription, db)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_deleted(subscription, db)

    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        await handle_payment_succeeded(invoice, db)

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await handle_payment_failed(invoice, db)

    return {"status": "success"}


# Webhook Helper Functions
async def handle_checkout_completed(session, db: Session):
    """Handle successful checkout session"""
    user_id = session.get("metadata", {}).get("user_id")
    if not user_id:
        return

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return

    # Update user with Stripe customer ID
    user.stripe_customer_id = session.get("customer")
    db.commit()


async def handle_subscription_created(subscription, db: Session):
    """Handle new subscription creation"""
    customer_id = subscription.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        return

    # Determine tier from price ID
    price_id = subscription["items"]["data"][0]["price"]["id"]
    tier = get_tier_from_price_id(price_id)

    # Update user subscription
    user.stripe_subscription_id = subscription["id"]
    user.subscription_tier = tier
    user.subscription_status = SubscriptionStatus.ACTIVE
    user.subscription_current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
    user.subscription_cancel_at_period_end = subscription.get("cancel_at_period_end", False)

    # Update usage limits based on tier
    update_usage_limits(user, tier)

    db.commit()


async def handle_subscription_updated(subscription, db: Session):
    """Handle subscription updates"""
    customer_id = subscription.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        return

    # Determine tier from price ID
    price_id = subscription["items"]["data"][0]["price"]["id"]
    tier = get_tier_from_price_id(price_id)

    # Update subscription info
    user.subscription_tier = tier
    user.subscription_status = SubscriptionStatus.ACTIVE if subscription["status"] == "active" else SubscriptionStatus.CANCELLED
    user.subscription_current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
    user.subscription_cancel_at_period_end = subscription.get("cancel_at_period_end", False)

    # Update usage limits
    update_usage_limits(user, tier)

    db.commit()


async def handle_subscription_deleted(subscription, db: Session):
    """Handle subscription cancellation"""
    customer_id = subscription.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        return

    # Downgrade to FREE tier
    user.subscription_tier = SubscriptionTier.FREE
    user.subscription_status = SubscriptionStatus.CANCELLED
    user.stripe_subscription_id = None
    user.subscription_cancel_at_period_end = False

    # Reset to FREE tier limits
    update_usage_limits(user, SubscriptionTier.FREE)

    db.commit()


async def handle_payment_succeeded(invoice, db: Session):
    """Handle successful payment"""
    customer_id = invoice.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        return

    # Update subscription status to active
    user.subscription_status = SubscriptionStatus.ACTIVE
    db.commit()


async def handle_payment_failed(invoice, db: Session):
    """Handle failed payment"""
    customer_id = invoice.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        return

    # Update subscription status to past_due
    user.subscription_status = SubscriptionStatus.PAST_DUE
    db.commit()


def get_tier_from_price_id(price_id: str) -> SubscriptionTier:
    """Map Stripe price ID to subscription tier"""
    if price_id in [STRIPE_PRICES["PRO_MONTHLY"], STRIPE_PRICES["PRO_YEARLY"]]:
        return SubscriptionTier.PRO
    elif price_id in [STRIPE_PRICES["BUSINESS_MONTHLY"], STRIPE_PRICES["BUSINESS_YEARLY"]]:
        return SubscriptionTier.BUSINESS
    elif price_id in [STRIPE_PRICES["ENTERPRISE_MONTHLY"], STRIPE_PRICES["ENTERPRISE_YEARLY"]]:
        return SubscriptionTier.ENTERPRISE
    return SubscriptionTier.FREE


def update_usage_limits(user: User, tier: SubscriptionTier):
    """Update user usage limits based on subscription tier"""
    limits = {
        SubscriptionTier.FREE: {
            "products_limit": 5,
            "matches_limit": 10,
            "alerts_limit": 1,
        },
        SubscriptionTier.PRO: {
            "products_limit": 50,
            "matches_limit": 100,
            "alerts_limit": 10,
        },
        SubscriptionTier.BUSINESS: {
            "products_limit": 200,
            "matches_limit": 500,
            "alerts_limit": 50,
        },
        SubscriptionTier.ENTERPRISE: {
            "products_limit": 9999,
            "matches_limit": 9999,
            "alerts_limit": 9999,
        },
    }

    tier_limits = limits.get(tier, limits[SubscriptionTier.FREE])
    user.products_limit = tier_limits["products_limit"]
    user.matches_limit = tier_limits["matches_limit"]
    user.alerts_limit = tier_limits["alerts_limit"]
