"""
AI Service — Claude-powered competitive intelligence features

Three capabilities:
  1. Pricing Recommendation  — "What price should I set right now, and why?"
  2. Natural Language Query   — "Which products am I losing to Amazon?"
  3. Weekly Narrative          — Executive summary email written by AI

All calls are synchronous and use the ANTHROPIC_API_KEY env var.
Falls back gracefully if the key is absent or the API is unreachable.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_FAST_MODEL = "claude-haiku-4-5-20251001"      # NL queries — fast + cheap
_SMART_MODEL = "claude-sonnet-4-6"              # Pricing recommendation + narrative


def _client():
    """Return an Anthropic client or raise if key is missing."""
    try:
        import anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        raise RuntimeError("anthropic package is not installed — run: pip install anthropic")


def _call(model: str, system: str, user: str, max_tokens: int = 1024) -> str:
    """Single synchronous Claude call. Returns the response text."""
    client = _client()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Feature 1: AI Pricing Recommendation
# ─────────────────────────────────────────────────────────────────────────────

def get_pricing_recommendation(
    product: dict,
    competitors: list[dict],
    price_history: list[dict],
    inventory: Optional[int],
) -> dict:
    """
    Ask Claude for the optimal price with plain-English reasoning.

    Args:
        product:       {title, sku, my_price, cost_price, category}
        competitors:   [{name, price, stock_status, is_prime, last_scraped}]
        price_history: [{competitor, price, timestamp}]  — last 30 days
        inventory:     Current stock quantity (None = unknown)

    Returns:
        {
            recommended_price: float | None,
            confidence: "high" | "medium" | "low",
            reasoning: str,
            watch_trigger: str,
            raw_response: str
        }
    """
    title = product.get("title", "Unknown product")
    my_price = product.get("my_price")
    cost_price = product.get("cost_price")
    category = product.get("category", "")

    # Build competitor summary
    comp_lines = []
    for c in competitors:
        stock = c.get("stock_status", "unknown")
        prime = " (Prime)" if c.get("is_prime") else ""
        price_str = f"${c['price']:.2f}" if c.get("price") else "no price"
        comp_lines.append(f"  - {c['name']}: {price_str}, {stock}{prime}")
    comp_text = "\n".join(comp_lines) if comp_lines else "  No competitor data available"

    # Margin
    if my_price and cost_price and cost_price > 0:
        margin_pct = round((my_price - cost_price) / my_price * 100, 1)
        margin_text = f"${cost_price:.2f} cost → {margin_pct}% gross margin at current price"
    elif cost_price:
        margin_text = f"${cost_price:.2f} cost (current price unknown)"
    else:
        margin_text = "Cost price unknown"

    # Price history summary (last 30 days, top 3 competitors)
    history_lines = []
    if price_history:
        by_competitor: dict = {}
        for h in price_history:
            by_competitor.setdefault(h["competitor"], []).append(h["price"])
        for comp, prices in list(by_competitor.items())[:3]:
            if len(prices) >= 2:
                trend = "↓" if prices[-1] < prices[0] else "↑" if prices[-1] > prices[0] else "→"
                history_lines.append(
                    f"  - {comp}: ${prices[0]:.2f} → ${prices[-1]:.2f} ({trend})"
                )
    history_text = "\n".join(history_lines) if history_lines else "  No 30-day history available"

    inv_text = f"{inventory} units in stock" if inventory is not None else "inventory unknown"

    system_prompt = (
        "You are a senior pricing strategist for an e-commerce retailer. "
        "You give concise, confident, data-driven pricing recommendations. "
        "Always respond in valid JSON with exactly these keys: "
        "recommended_price (number or null), confidence (high/medium/low), "
        "reasoning (2-3 sentences), watch_trigger (one sentence — what event should prompt a reprice)."
    )

    user_prompt = f"""Product: {title}
Category: {category}
Current Price: {"$" + str(my_price) if my_price else "not set"}
{margin_text}
Inventory: {inv_text}

Current Competitor Prices:
{comp_text}

30-Day Price Trends:
{history_text}

What is the optimal price to set right now? Consider: margin protection, competitive position, stock opportunities, and pricing power. Respond in JSON only."""

    try:
        raw = _call(_SMART_MODEL, system_prompt, user_prompt, max_tokens=512)
        # Strip markdown code fences if Claude wraps the JSON
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[: cleaned.rfind("```")]
        data = json.loads(cleaned)
        return {
            "recommended_price": data.get("recommended_price"),
            "confidence": data.get("confidence", "medium"),
            "reasoning": data.get("reasoning", ""),
            "watch_trigger": data.get("watch_trigger", ""),
            "raw_response": raw,
        }
    except json.JSONDecodeError:
        # Claude returned prose instead of JSON — extract and return as-is
        return {
            "recommended_price": None,
            "confidence": "low",
            "reasoning": raw,
            "watch_trigger": "",
            "raw_response": raw,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 2: Natural Language Competitive Query
# ─────────────────────────────────────────────────────────────────────────────

def answer_competitive_query(question: str, user_context: dict) -> dict:
    """
    Answer a free-form competitive intelligence question about the user's catalog.

    Args:
        question:     Natural language question from the user.
        user_context: {
            products: [{id, title, my_price, competitor_count, my_position}],
            recent_changes: [{product, competitor, old_price, new_price, changed_at}],
            metrics: {total_products, total_competitors, cheapest_pct, expensive_pct, ...}
          }

    Returns:
        {answer: str, related_products: list[int], confidence: str}
    """
    # Build a compact catalog summary
    products = user_context.get("products", [])[:30]  # cap context size
    prod_lines = []
    for p in products:
        pos = p.get("my_position", "unknown")
        price = f"${p['my_price']:.2f}" if p.get("my_price") else "no price"
        prod_lines.append(
            f"  [{p['id']}] {p['title']} — {price}, {p.get('competitor_count', 0)} competitors, position: {pos}"
        )
    catalog_text = "\n".join(prod_lines) if prod_lines else "  No products yet"

    # Recent changes
    changes = user_context.get("recent_changes", [])[:15]
    change_lines = []
    for c in changes:
        direction = "dropped" if c.get("new_price", 0) < c.get("old_price", 0) else "raised"
        change_lines.append(
            f"  {c['competitor']} {direction} price on '{c['product']}': "
            f"${c['old_price']:.2f} → ${c['new_price']:.2f}"
        )
    changes_text = "\n".join(change_lines) if change_lines else "  No recent changes"

    metrics = user_context.get("metrics", {})

    system_prompt = (
        "You are a competitive intelligence analyst for an e-commerce retailer. "
        "You have full visibility into the user's product catalog and competitor pricing. "
        "Give direct, specific, actionable answers. "
        "Reference actual product names and prices from the data. "
        "If the question can't be answered from available data, say so clearly and suggest what data would help."
    )

    user_prompt = f"""User's Question: {question}

--- Catalog Overview ---
Total products: {metrics.get('total_products', len(products))}
Total competitor matches: {metrics.get('total_competitors', '?')}
Position breakdown: {metrics.get('cheapest_pct', '?')}% cheapest, {metrics.get('expensive_pct', '?')}% most expensive

--- Products (with competitive position) ---
{catalog_text}

--- Recent Price Changes (last 7 days) ---
{changes_text}

Answer the user's question based on this data. Be specific — use product names and dollar amounts."""

    try:
        answer = _call(_FAST_MODEL, system_prompt, user_prompt, max_tokens=768)
        # Extract referenced product IDs (heuristic: look for [id] patterns)
        import re
        mentioned_ids = [int(m) for m in re.findall(r'\[(\d+)\]', user_prompt + answer)]

        return {
            "answer": answer,
            "related_product_ids": list(set(mentioned_ids)),
            "model_used": _FAST_MODEL,
        }
    except Exception as e:
        logger.error("NL query failed: %s", e)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3: Weekly Competitive Narrative
# ─────────────────────────────────────────────────────────────────────────────

def generate_weekly_narrative(
    user_name: str,
    metrics: dict,
    top_changes: list[dict],
    top_opportunities: list[dict],
    top_threats: list[dict],
    week_start: Optional[datetime] = None,
) -> dict:
    """
    Generate a 3-paragraph executive summary of the week's competitive activity.

    Args:
        user_name:         Display name for personalisation.
        metrics:           Current KPI snapshot.
        top_changes:       Up to 5 biggest price changes this week.
        top_opportunities: Up to 3 top opportunities.
        top_threats:       Up to 3 top threats.
        week_start:        Start of reporting week (defaults to 7 days ago).

    Returns:
        {subject: str, html: str, plain_text: str}
    """
    if week_start is None:
        week_start = datetime.utcnow() - timedelta(days=7)
    week_label = week_start.strftime("%B %d")

    # Changes
    change_lines = []
    for c in top_changes[:5]:
        direction = "dropped" if c.get("drop", True) else "raised"
        change_lines.append(
            f"- {c['competitor']} {direction} on '{c['product']}' by {c.get('change_pct', '?')}%"
        )
    changes_text = "\n".join(change_lines) if change_lines else "- No significant price changes this week"

    # Opportunities
    opp_lines = [f"- {o['title']}: {o.get('description', '')}" for o in top_opportunities[:3]]
    opp_text = "\n".join(opp_lines) if opp_lines else "- No new opportunities identified"

    # Threats
    threat_lines = [f"- {t['title']}: {t.get('description', '')}" for t in top_threats[:3]]
    threat_text = "\n".join(threat_lines) if threat_lines else "- No critical threats this week"

    system_prompt = (
        "You are a senior competitive intelligence analyst writing a weekly executive briefing "
        "for an e-commerce business owner. "
        "Write in a professional yet conversational tone — clear, specific, confident. "
        "Structure your response as exactly 3 paragraphs: "
        "1) What happened this week (price movements and market shifts), "
        "2) Biggest opportunity to act on, "
        "3) Biggest threat to monitor. "
        "Use specific numbers and product/competitor names from the data. "
        "End with one sentence suggesting the single most important action for next week. "
        "Do NOT use markdown headers or bullet points — flowing prose only."
    )

    user_prompt = f"""Write a weekly competitive intelligence briefing for {user_name}.
Week of: {week_label}

Key Metrics:
- Products monitored: {metrics.get('total_products', '?')}
- Total competitors tracked: {metrics.get('total_competitors', '?')}
- Competitive position: {metrics.get('cheapest_pct', '?')}% of products cheapest, {metrics.get('expensive_pct', '?')}% most expensive
- Price changes this week: {metrics.get('price_changes_last_week', '?')}
- Active alerts fired: {metrics.get('alerts_fired', '?')}

Significant Price Changes:
{changes_text}

Top Opportunities:
{opp_text}

Top Threats:
{threat_text}"""

    try:
        narrative = _call(_SMART_MODEL, system_prompt, user_prompt, max_tokens=600)

        # Build a clean subject line
        subject_prompt = (
            f"Write a concise email subject line (max 60 chars) for this weekly "
            f"competitive intelligence report for the week of {week_label}. "
            f"Make it specific and action-oriented. No quotes."
        )
        subject = _call(_FAST_MODEL, "You write concise email subject lines.", subject_prompt, max_tokens=30)

        # Convert plain text narrative to basic HTML
        paragraphs = [p.strip() for p in narrative.split("\n\n") if p.strip()]
        html_paras = "".join(f"<p>{p}</p>" for p in paragraphs)
        html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
<h2 style="color:#1a1a2e">Weekly Competitive Intelligence — {week_label}</h2>
{html_paras}
<hr style="margin:24px 0;border:none;border-top:1px solid #eee">
<p style="color:#666;font-size:12px">Powered by MarketIntel AI &bull; <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
</div>"""

        return {
            "subject": subject,
            "plain_text": narrative,
            "html": html,
            "week_start": week_start.isoformat(),
        }
    except Exception as e:
        logger.error("Narrative generation failed: %s", e)
        raise
