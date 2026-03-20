"""
Server-Sent Events (SSE) real-time price change feed.
"""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.dependencies import get_current_token_payload
from database.connection import SessionLocal
from database.models import CompetitorMatch, PriceHistory, ProductMonitored

router = APIRouter(prefix="/events", tags=["Real-time Events"])
logger = logging.getLogger(__name__)

POLL_INTERVAL = 15


@router.get("")
async def price_event_stream(
    request: Request,
    token_payload: dict = Depends(get_current_token_payload),
):
    """
    Stream real-time price changes for the authenticated user.

    The browser authenticates with the secure auth cookie, so no JWT is placed
    in the URL anymore.
    """
    user_id = int(token_payload["sub"])

    async def generate():
        last_seen_id = _get_latest_price_history_id(user_id)
        yield _sse("ping", {"ts": datetime.utcnow().isoformat()})

        ping_counter = 0

        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected (user %s)", user_id)
                break

            await asyncio.sleep(POLL_INTERVAL)
            ping_counter += POLL_INTERVAL

            new_rows, last_seen_id = _fetch_new_price_changes(user_id, last_seen_id)
            for row in new_rows:
                yield _sse("price_change", row)

            if ping_counter >= 60:
                yield _sse("ping", {"ts": datetime.utcnow().isoformat()})
                ping_counter = 0

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event_type: str, data: dict) -> str:
    payload = json.dumps({"type": event_type, **data})
    return f"data: {payload}\n\n"


def _get_latest_price_history_id(user_id: int) -> int:
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

        for price_history, competitor_name, product_id, product_title in rows:
            if price_history.id > new_max_id:
                new_max_id = price_history.id

            events.append(
                {
                    "product_id": product_id,
                    "product_title": product_title,
                    "competitor": competitor_name,
                    "in_stock": price_history.in_stock,
                    "new_price": price_history.price,
                    "timestamp": price_history.timestamp.isoformat() if price_history.timestamp else None,
                }
            )
    except Exception as exc:
        logger.error("SSE poll error: %s", exc)
    finally:
        db.close()

    return events, new_max_id
