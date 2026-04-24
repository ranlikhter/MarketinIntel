"""
AI Command Palette API
POST /ai/command — conversational interface powered by Claude tool use.

Supports:
  • Natural language catalog questions   "Which products am I losing on?"
  • Navigation commands                  "Take me to repricing"
  • Scrape triggers                      "Refresh my price data"
  • Repricing rule creation              "Stay $1 below Amazon on all headphones"
  • Quick price summary                  "How am I doing competitively?"
"""

import os
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import User, ProductMonitored, CompetitorMatch, PriceAlert
from api.dependencies import get_current_user
from services.activity_service import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Command"])

# ── Models ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str

class CommandRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOLS = [
    {
        "name": "query_catalog",
        "description": (
            "Answer a question about the user's product catalog, competitor pricing, "
            "market position, or price history. Use this for any analytical or "
            "informational question about prices, competitors, or products."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific question to answer about the catalog"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "navigate_to",
        "description": (
            "Navigate the user to a specific page in the app. Use when the user wants "
            "to go somewhere: repricing rules, alerts, products list, settings, analytics, dashboard."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "App path: /repricing, /alerts, /products, /analytics, /settings, /dashboard, /competitors"
                },
                "label": {
                    "type": "string",
                    "description": "Button label for the navigation action, e.g. 'Go to Repricing'"
                }
            },
            "required": ["path", "label"]
        }
    },
    {
        "name": "trigger_scrape",
        "description": (
            "Queue an immediate competitor price scrape for all the user's products. "
            "Use when the user wants fresh data, asks to refresh prices, or wants to "
            "check current competitor prices right now."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why the scrape was triggered"
                }
            },
            "required": []
        }
    },
    {
        "name": "create_repricing_rule",
        "description": (
            "Propose a repricing rule to the user. Shows a confirmation card before "
            "creating. Use when the user asks to set up pricing automation like "
            "'stay below Amazon', 'match the lowest price', 'add margin X%'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Human-readable rule name"
                },
                "rule_type": {
                    "type": "string",
                    "enum": ["match_lowest", "undercut", "margin_based", "map_protected"],
                    "description": "Type of repricing rule"
                },
                "config": {
                    "type": "object",
                    "description": "Rule configuration. undercut: {amount: 1.00} or {percentage: 5}. match_lowest: {margin_amount: 0.50}. margin_based: {cost: X, margin_pct: 20}. map_protected: {map_price: X}"
                },
                "description": {
                    "type": "string",
                    "description": "Plain-English explanation of what this rule does"
                }
            },
            "required": ["name", "rule_type", "config", "description"]
        }
    },
]

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = """\
You are MarketIntel AI — an expert competitive pricing assistant embedded in a \
price intelligence platform. You help e-commerce sellers understand their market \
position and take action on pricing opportunities.

You have access to tools:
- query_catalog: answer questions about products, prices, competitors
- navigate_to: send the user to a page in the app
- trigger_scrape: refresh competitor price data
- create_repricing_rule: propose an automated repricing rule

Guidelines:
- Be concise and direct. Use numbers and product names when you have them.
- For informational questions, always use query_catalog even if you think you know the answer — the tool has live data.
- For navigation requests like "take me to repricing", use navigate_to.
- For "refresh my data" / "check prices now", use trigger_scrape.
- For pricing automation requests, use create_repricing_rule with a sensible config.
- Never make up data. If you don't know, say so and suggest what action would help.
- Keep replies under 150 words unless the user asks for detail.
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _compact_context(user: User, db: Session) -> dict:
    """Build a compact JSON context blob for the tool executor."""
    products = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == user.id
    ).limit(50).all()

    if not products:
        return {"products": [], "metrics": {}, "recent_alerts": 0}

    product_ids = [p.id for p in products]

    # Batch: latest competitor prices per product
    rows = db.query(
        CompetitorMatch.monitored_product_id,
        CompetitorMatch.competitor_name,
        CompetitorMatch.latest_price,
    ).filter(
        CompetitorMatch.monitored_product_id.in_(product_ids),
        CompetitorMatch.latest_price.isnot(None),
    ).all()

    from collections import defaultdict
    prices_by_product: dict = defaultdict(list)
    for r in rows:
        prices_by_product[r.monitored_product_id].append(
            {"competitor": r.competitor_name, "price": r.latest_price}
        )

    prod_list = []
    overpriced = 0
    for p in products:
        comps = prices_by_product.get(p.id, [])
        lowest = min((c["price"] for c in comps), default=None)
        if lowest and p.my_price:
            gap_pct = (p.my_price - lowest) / lowest * 100
            if gap_pct > 5:
                overpriced += 1
        prod_list.append({
            "id": p.id,
            "title": p.title,
            "my_price": p.my_price,
            "competitors": comps[:5],
        })

    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_alerts = db.query(PriceAlert).filter(
        PriceAlert.user_id == user.id,
        PriceAlert.last_triggered_at >= cutoff,
    ).count()

    return {
        "products": prod_list,
        "metrics": {
            "total_products": len(products),
            "overpriced_count": overpriced,
            "recent_alerts_24h": recent_alerts,
        },
        "recent_alerts": recent_alerts,
    }


def _execute_tool(name: str, tool_input: dict, user: User, db: Session) -> tuple[str, Optional[dict]]:
    """
    Execute a tool call and return (text_result_for_claude, action_for_frontend).
    action_for_frontend is None for pure-query tools; non-None for side-effect tools.
    """

    if name == "query_catalog":
        from services.ai_service import answer_competitive_query
        from api.routes.ai import _build_user_context
        context = _build_user_context(user, db)
        try:
            result = answer_competitive_query(tool_input["question"], context)
            return result["answer"], None
        except Exception as exc:
            return f"Could not answer: {exc}", None

    elif name == "navigate_to":
        path = tool_input.get("path", "/dashboard")
        label = tool_input.get("label", "Open page")
        action = {"type": "navigate", "path": path, "label": label}
        return f"Navigation ready to {path}.", action

    elif name == "trigger_scrape":
        try:
            from tasks.scraping_tasks import scrape_all_products
            task = scrape_all_products.delay()
            action = {
                "type": "scrape_queued",
                "task_id": task.id,
                "label": "Scrape queued — results in ~5 min",
            }
            return "Scrape queued successfully.", action
        except Exception as exc:
            return f"Could not queue scrape: {exc}", None

    elif name == "create_repricing_rule":
        action = {
            "type": "create_rule",
            "payload": {
                "name": tool_input.get("name"),
                "rule_type": tool_input.get("rule_type"),
                "config": tool_input.get("config", {}),
                "description": tool_input.get("description", ""),
            },
            "label": "Create Rule",
        }
        return "Rule ready for your confirmation.", action

    return f"Unknown tool: {name}", None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/command")
async def ai_command(
    body: CommandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Conversational AI command — answers questions and takes actions via tool use.

    Send a plain-English message; receive a reply and an optional action card.
    Supported multi-turn via the `history` array.
    """
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="message cannot be empty")
    if len(body.message) > 1000:
        raise HTTPException(status_code=422, detail="message must be under 1000 characters")

    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="AI features require ANTHROPIC_API_KEY to be configured"
        )

    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="anthropic package not installed")

    client = anthropic.Anthropic(api_key=key)

    # Build message history
    messages = []
    for h in body.history[-10:]:  # cap context at 10 turns
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": body.message})

    # ── First Claude call — may return tool_use ───────────────────────────────
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # fast for interactive palette
            max_tokens=1024,
            system=_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )
    except Exception as exc:
        logger.error("AI command failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"AI service error: {str(exc)}")

    action: Optional[dict] = None
    tool_called: Optional[str] = None

    if response.stop_reason == "tool_use":
        # Find the tool_use block
        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_block:
            tool_called = tool_block.name
            tool_result_text, action = _execute_tool(
                tool_block.name, tool_block.input, current_user, db
            )

            # ── Second Claude call — synthesise the tool result into a reply ─
            follow_up_messages = messages + [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": tool_result_text,
                        }
                    ],
                },
            ]
            try:
                final = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=512,
                    system=_SYSTEM,
                    tools=_TOOLS,
                    messages=follow_up_messages,
                )
                reply = next(
                    (b.text for b in final.content if hasattr(b, "text")),
                    "Done."
                )
            except Exception as exc:
                logger.warning("Follow-up AI call failed: %s", exc)
                reply = tool_result_text
        else:
            reply = next((b.text for b in response.content if hasattr(b, "text")), "")
    else:
        reply = next((b.text for b in response.content if hasattr(b, "text")), "")

    # Log activity (non-blocking)
    try:
        log_activity(
            db, current_user.id, "ai.command", "user",
            f"AI command: {body.message[:80]}",
            metadata={"tool_called": tool_called},
        )
        db.commit()
    except Exception:
        pass

    return {
        "success": True,
        "reply": reply,
        "action": action,
        "tool_called": tool_called,
        "generated_at": datetime.utcnow().isoformat(),
    }
