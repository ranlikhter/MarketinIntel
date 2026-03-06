"""
Promotion Detector — extract structured promotional offers from a product page.

Detects:
  • BOGO / Buy One Get One Free
  • Buy X Get Y (Free) — "Buy 3 Get 1 Free", "Buy 2 Get 1"
  • Percentage discounts tied to quantity — "Get 20% off when you buy 3"
  • Free item / gift with purchase
  • Coupon codes and general sale badges
  • JSON-LD structured offers with eligibleQuantity / priceSpecification

Entry point:
    from scrapers.promotion_detector import detect_promotions
    promos = detect_promotions(soup, page_text)

Performance notes vs original:
  • All 9 promo CSS selectors are combined into a single soup.select() call
    instead of 9 separate calls — one DOM traversal instead of nine.
  • page_text is computed once and reused; each helper receives it rather
    than calling soup.get_text() independently.
"""

import json
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup


# ── Pre-compiled regex patterns ───────────────────────────────────────────────

# Matches: "Buy 2 Get 1 Free", "Buy 3 get 2 free", "Buy 3, get 1 free"
_BUY_X_GET_Y_RE = re.compile(
    r"buy\s+(\d+)[,\s]+get\s+(\d+)\s*(?:free|off)?",
    re.IGNORECASE,
)

# Matches: "BOGO", "Buy One Get One Free", "Buy One Get One"
_BOGO_RE = re.compile(
    r"\b(bogo|buy\s+one[\s,]+get\s+one(?:\s+free)?)\b",
    re.IGNORECASE,
)

# Matches: "Get 20% off when you buy 3", "Save 15% when buying 2+"
_PCT_QTY_RE = re.compile(
    r"(?:get|save|earn)\s+(\d+(?:\.\d+)?)\s*%\s*off\s+(?:when\s+you\s+buy|if\s+you\s+buy|buying)\s+(\d+)",
    re.IGNORECASE,
)

# Matches: "Free gift", "Free charger", etc.
_FREE_ITEM_RE = re.compile(
    r"\bfree\s+(gift|item|product|sample|accessory|bag|case|cable|charger|[a-z]{3,30})\b",
    re.IGNORECASE,
)

# Generic sale phrases (fallback)
_GENERIC_SALE_RE = re.compile(
    r"\b(limited[\s-]time\s+(?:offer|deal)|flash\s+sale|special\s+offer|clearance|on\s+sale)\b",
    re.IGNORECASE,
)

# All promo-related CSS selectors merged into one expression so BeautifulSoup
# traverses the DOM a single time instead of once per selector.
_PROMO_SELECTOR = (
    "[class*='promo'],[class*='deal'],[class*='offer'],"
    "[class*='badge'],[class*='sale'],[class*='coupon'],"
    "[class*='savings'],[class*='discount'],"
    "[id*='promo'],[id*='deal'],[id*='offer']"
)


# ── Public API ────────────────────────────────────────────────────────────────

def detect_promotions(soup: BeautifulSoup, page_text: Optional[str] = None) -> List[Dict]:
    """
    Analyse a BeautifulSoup object and return a deduplicated list of structured
    promotion dicts.  Each dict matches the CompetitorPromotion fields:

        {
            "promo_type":    str,          # "bogo"|"bundle"|"pct_off"|"free_item"|"other"
            "description":   str,
            "buy_qty":       int | None,
            "get_qty":       int | None,
            "discount_pct":  float | None,
            "free_item_name":str | None,
        }
    """
    # Compute page_text exactly once; shared by all three sub-detectors.
    if page_text is None:
        page_text = soup.get_text(" ", strip=True)

    results: List[Dict] = []
    seen: set = set()

    def _add(promo: Dict):
        key = promo["description"].lower().strip()
        if key not in seen:
            seen.add(key)
            results.append(promo)

    for promo in _from_json_ld(soup, page_text):
        _add(promo)
    for promo in _from_dom_elements(soup):
        _add(promo)
    for promo in _from_page_text(page_text):
        _add(promo)

    return results


# ── Extraction helpers ────────────────────────────────────────────────────────

def _from_json_ld(soup: BeautifulSoup, _page_text: str) -> List[Dict]:
    """Parse Schema.org Offer objects from <script type="application/ld+json">."""
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            offers = item.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers:
                if not isinstance(offer, dict):
                    continue

                desc = offer.get("description") or offer.get("name") or ""
                eligible_qty = offer.get("eligibleQuantity") or {}
                min_qty = None
                if isinstance(eligible_qty, dict):
                    min_qty = eligible_qty.get("minValue") or eligible_qty.get("value")
                elif isinstance(eligible_qty, (int, float)):
                    min_qty = int(eligible_qty)

                if min_qty and int(min_qty) > 1 and desc:
                    results.append({
                        "promo_type": "bundle",
                        "description": desc[:200],
                        "buy_qty": int(min_qty),
                        "get_qty": None,
                        "discount_pct": None,
                        "free_item_name": None,
                    })
                elif desc:
                    results.extend(_parse_text(desc))

    return results


def _from_dom_elements(soup: BeautifulSoup) -> List[Dict]:
    """
    Scan promo-related DOM elements using a single combined CSS selector.
    This replaces the original loop over 9 separate soup.select() calls.
    """
    results = []
    try:
        for elem in soup.select(_PROMO_SELECTOR):
            text = elem.get_text(" ", strip=True)
            if not text or len(text) > 300:
                continue
            parsed = _parse_text(text)
            if parsed:
                results.extend(parsed)
            elif _GENERIC_SALE_RE.search(text):
                results.append(_other(text))
    except Exception:
        pass
    return results


def _from_page_text(page_text: str) -> List[Dict]:
    """Run regex patterns over the full page text."""
    results = []

    for m in _BUY_X_GET_Y_RE.finditer(page_text):
        buy_qty = int(m.group(1))
        get_qty = int(m.group(2))
        results.append({
            "promo_type": "bogo" if buy_qty == 1 and get_qty == 1 else "bundle",
            "description": m.group(0).strip()[:200],
            "buy_qty": buy_qty,
            "get_qty": get_qty,
            "discount_pct": None,
            "free_item_name": None,
        })

    if _BOGO_RE.search(page_text) and not results:
        results.append({
            "promo_type": "bogo",
            "description": "Buy One Get One Free",
            "buy_qty": 1,
            "get_qty": 1,
            "discount_pct": None,
            "free_item_name": None,
        })

    for m in _PCT_QTY_RE.finditer(page_text):
        results.append({
            "promo_type": "pct_off",
            "description": m.group(0).strip()[:200],
            "buy_qty": int(m.group(2)),
            "get_qty": None,
            "discount_pct": float(m.group(1)),
            "free_item_name": None,
        })

    for m in _FREE_ITEM_RE.finditer(page_text):
        results.append({
            "promo_type": "free_item",
            "description": m.group(0).strip()[:200],
            "buy_qty": None,
            "get_qty": None,
            "discount_pct": None,
            "free_item_name": m.group(1).strip(),
        })

    return results


def _parse_text(text: str) -> List[Dict]:
    """Run all regex patterns against a single text snippet."""
    m = _BUY_X_GET_Y_RE.search(text)
    if m:
        buy_qty, get_qty = int(m.group(1)), int(m.group(2))
        return [{
            "promo_type": "bogo" if buy_qty == 1 and get_qty == 1 else "bundle",
            "description": text[:200],
            "buy_qty": buy_qty,
            "get_qty": get_qty,
            "discount_pct": None,
            "free_item_name": None,
        }]

    m = _BOGO_RE.search(text)
    if m:
        return [{
            "promo_type": "bogo",
            "description": text[:200],
            "buy_qty": 1,
            "get_qty": 1,
            "discount_pct": None,
            "free_item_name": None,
        }]

    m = _PCT_QTY_RE.search(text)
    if m:
        return [{
            "promo_type": "pct_off",
            "description": text[:200],
            "buy_qty": int(m.group(2)),
            "get_qty": None,
            "discount_pct": float(m.group(1)),
            "free_item_name": None,
        }]

    m = _FREE_ITEM_RE.search(text)
    if m:
        return [{
            "promo_type": "free_item",
            "description": text[:200],
            "buy_qty": None,
            "get_qty": None,
            "discount_pct": None,
            "free_item_name": m.group(1).strip(),
        }]

    return []


def _other(text: str) -> Dict:
    return {
        "promo_type": "other",
        "description": text[:200],
        "buy_qty": None,
        "get_qty": None,
        "discount_pct": None,
        "free_item_name": None,
    }
