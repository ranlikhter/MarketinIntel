"""
Server-Sent Events (SSE) — Real-time price change feed

GET /api/events
  → Streams JSON events to the browser using the SSE protocol.
  → The frontend connects via EventSource and shows toast notifications
    whenever a competitor changes their price on any monitored product.

Event format:
  data: {"type": "price_change", "product_id": 1, "product_title": "...",
         "competitor": "Amazon", "old_price": 99.99, "new_price": 89.99,
         "change_pct": -10.0, "timestamp": "2026-02-22T08:00:00"}

  data: {"type": "ping"}   ← keepalive every 20 seconds

The endpoint polls for new PriceHistory rows with a high-water-mark approach
(last seen PriceHistory.id), creating a fresh DB session on each poll so the
long-lived HTTP connection does not hold a stale transaction.
"""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from database.connection import get_db, SessionLocal
from database.models import PriceHistory, CompetitorMatch, ProductMonitored, User
from api.dependencies import get_current_user

router = APIRouter(prefix="/events", tags=["Real-time Events"])
logger = logging.getLogger(__name__)

# How often (seconds) to poll the DB for new price changes
POLL_INTERVAL = 15

SECRET_KEY = "your-secret-key"  # pulled from env below
ALGORITHM = "HS256"


def _get_user_id_from_token(token: str) -> int | None:
    """Decode a JWT and return the user_id, or None if invalid."""
    import os
    secret = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        user_id = payload.get("sub") or payload.get("user_id")
        return int(user_id) if user_id else None
    except Exception:
        return None


@router.get("")
async def price_event_stream(
    request: Request,
    token: str = Query(..., description="JWT access token (EventSource can't set headers)"),
):
    """
    GET /api/events

    Server-Sent Events stream for real-time price change notifications.

    Connect with:
        const es = new EventSource('/api/events', { withCredentials: true });
        es.onmessage = (e) => { const ev = JSON.parse(e.data); ... };

    The stream yields a 'ping' every ~20s to keep proxies alive,
    and a 'price_change' event whenever a competitor updates their price
    on any product owned by the authenticated user.
    """
    user_id = _get_user_id_from_token(token)
    if not user_id:
        async def _deny():
            yield _sse("error", {"message": "Unauthorized"})
        return StreamingResponse(_deny(), media_type="text/event-stream")

    async def generate():
        # Seed the high-water mark: start from the latest existing PriceHistory id
        # so we don't replay old data on connect.
        last_seen_id = _get_latest_price_history_id(user_id)

        # Send initial ping so the browser knows the connection is live
        yield _sse("ping", {"ts": datetime.utcnow().isoformat()})

        ping_counter = 0

        while True:
            # Check if the client disconnected
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected (user {user_id})")
                break

            await asyncio.sleep(POLL_INTERVAL)
            ping_counter += POLL_INTERVAL

            # Fetch new price history rows in a fresh session
            new_rows, last_seen_id = _fetch_new_price_changes(user_id, last_seen_id)

            for row in new_rows:
                yield _sse("price_change", row)

            # Keepalive ping every ~60s regardless of activity
            if ping_counter >= 60:
                yield _sse("ping", {"ts": datetime.utcnow().isoformat()})
                ping_counter = 0

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # nginx: disable buffering
            "Connection": "keep-alive",
        },
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sse(event_type: str, data: dict) -> str:
    """Format a single SSE frame."""
    payload = json.dumps({"type": event_type, **data})
    return f"data: {payload}\n\n"


def _get_latest_price_history_id(user_id: int) -> int:
    """Return the current maximum PriceHistory.id for the user's products (seed value)."""
    db = SessionLocal()
    try:
        row = (
            db.query(PriceHistory.id)
            .join(CompetitorMatch, PriceHistory.match_id == CompetitorMatch.id)
            .join(ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id)
            .filter(ProductMonitored.user_id == user_id)
            .order_by(PriceHistory.id.desc())
            .first()
        )
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        db.close()


def _fetch_new_price_changes(user_id: int, last_seen_id: int):
    """
    Query for PriceHistory rows added since last_seen_id for this user's products.
    Returns (list_of_event_dicts, new_high_water_mark).
    """
    db = SessionLocal()
    events = []
    new_max_id = last_seen_id
    try:
        rows = (
            db.query(
                PriceHistory,
                CompetitorMatch.competitor_name,
                CompetitorMatch.monitored_product_id,
                ProductMonitored.title,
            )
            .join(CompetitorMatch, PriceHistory.match_id == CompetitorMatch.id)
            .join(ProductMonitored, CompetitorMatch.monitored_product_id == ProductMonitored.id)
            .filter(
                ProductMonitored.user_id == user_id,
                PriceHistory.id > last_seen_id,
            )
            .order_by(PriceHistory.id.asc())
            .limit(20)
            .all()
        )

        for ph, competitor_name, product_id, product_title in rows:
            if ph.id > new_max_id:
                new_max_id = ph.id

            events.append({
                "product_id": product_id,
                "product_title": product_title,
                "competitor": competitor_name,
                "new_price": ph.price,
                "in_stock": ph.in_stock,
                "timestamp": ph.timestamp.isoformat() if ph.timestamp else None,
            })

    except Exception as e:
        logger.error(f"SSE poll error: {e}")
    finally:
        db.close()

    return events, new_max_id
