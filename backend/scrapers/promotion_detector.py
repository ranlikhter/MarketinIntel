"""
Promotion Detector — extract structured promotional offers from a scraped product page.

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
    # Returns list of dicts, e.g.:
    # [{"promo_type": "bundle", "description": "Buy 2 Get 1 Free",
    #   "buy_qty": 2, "get_qty": 1, "discount_pct": None, "free_item_name": None}]
"""

import json
import re
from typing import List, Dict, Optional

from bs4 import BeautifulSoup


# ── Pattern library ────────────────────────────────────────────────────────────

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

# Matches: "Free [word]", "Free gift", "Complimentary [word]"
_FREE_ITEM_RE = re.compile(
    r"\bfree\s+(gift|item|product|sample|accessory|bag|case|cable|charger|[a-z]{3,30})\b",
    re.IGNORECASE,
)

# Common promotional CSS class/id fragments (partial match)
_PROMO_SELECTORS = [
    "[class*='promo']", "[class*='deal']", "[class*='offer']",
    "[class*='badge']", "[class*='sale']", "[class*='coupon']",
    "[class*='savings']", "[class*='discount']",
    "[id*='promo']", "[id*='deal']", "[id*='offer']",
]

# Phrases that indicate a generic sale (fallback)
_GENERIC_SALE_RE = re.compile(
    r"\b(limited[\s-]time\s+(?:offer|deal)|flash\s+sale|special\s+offer|clearance|on\s+sale)\b",
    re.IGNORECASE,
)


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_promotions(soup: BeautifulSoup, page_text: Optional[str] = None) -> List[Dict]:
    """
    Analyse a BeautifulSoup object and return a deduplicated list of structured
    promotion dicts.  Each dict matches the fields of CompetitorPromotion:

        {
            "promo_type":    str,          # "bogo"|"bundle"|"pct_off"|"free_item"|"other"
            "description":   str,          # human-readable, e.g. "Buy 2 Get 1 Free"
            "buy_qty":       int | None,
            "get_qty":       int | None,
            "discount_pct":  float | None,
            "free_item_name":str | None,
        }
    """
    if page_text is None:
        page_text = soup.get_text(" ", strip=True)

    results: List[Dict] = []
    seen_descs: set = set()

    def _add(promo: Dict):
        key = promo["description"].lower().strip()
        if key not in seen_descs:
            seen_descs.add(key)
            results.append(promo)

    # 1. JSON-LD structured data (most reliable)
    for promo in _from_json_ld(soup):
        _add(promo)

    # 2. DOM element scan (promo badges, banners)
    for promo in _from_dom_elements(soup):
        _add(promo)

    # 3. Full page text regex scan
    for promo in _from_page_text(page_text):
        _add(promo)

    return results


# ── Extraction helpers ─────────────────────────────────────────────────────────

def _from_json_ld(soup: BeautifulSoup) -> List[Dict]:
    """Parse Schema.org Offer objects from <script type="application/ld+json">."""
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue

        # Normalise: could be a single object or a list
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
                    parsed = _parse_text(desc)
                    if parsed:
                        results.extend(parsed)

    return results


def _from_dom_elements(soup: BeautifulSoup) -> List[Dict]:
    """Scrape promo-related DOM elements using broad CSS selectors."""
    results = []
    for selector in _PROMO_SELECTORS:
        try:
            for elem in soup.select(selector):
                text = elem.get_text(" ", strip=True)
                if not text or len(text) > 300:
                    continue
                parsed = _parse_text(text)
                if parsed:
                    results.extend(parsed)
                elif _GENERIC_SALE_RE.search(text):
                    results.append(_other(text))
        except Exception:
            continue
    return results


def _from_page_text(page_text: str) -> List[Dict]:
    """Run regex patterns over the entire page text."""
    results = []

    for m in _BUY_X_GET_Y_RE.finditer(page_text):
        buy_qty = int(m.group(1))
        get_qty = int(m.group(2))
        desc = m.group(0).strip()
        results.append({
            "promo_type": "bogo" if buy_qty == 1 and get_qty == 1 else "bundle",
            "description": desc[:200],
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
        item_name = m.group(1).strip()
        results.append({
            "promo_type": "free_item",
            "description": m.group(0).strip()[:200],
            "buy_qty": None,
            "get_qty": None,
            "discount_pct": None,
            "free_item_name": item_name,
        })

    return results


def _parse_text(text: str) -> List[Dict]:
    """Run all regex patterns against a single text snippet."""
    results = []

    m = _BUY_X_GET_Y_RE.search(text)
    if m:
        buy_qty = int(m.group(1))
        get_qty = int(m.group(2))
        results.append({
            "promo_type": "bogo" if buy_qty == 1 and get_qty == 1 else "bundle",
            "description": text[:200],
            "buy_qty": buy_qty,
            "get_qty": get_qty,
            "discount_pct": None,
            "free_item_name": None,
        })
        return results

    m = _BOGO_RE.search(text)
    if m:
        results.append({
            "promo_type": "bogo",
            "description": text[:200],
            "buy_qty": 1,
            "get_qty": 1,
            "discount_pct": None,
            "free_item_name": None,
        })
        return results

    m = _PCT_QTY_RE.search(text)
    if m:
        results.append({
            "promo_type": "pct_off",
            "description": text[:200],
            "buy_qty": int(m.group(2)),
            "get_qty": None,
            "discount_pct": float(m.group(1)),
            "free_item_name": None,
        })
        return results

    m = _FREE_ITEM_RE.search(text)
    if m:
        results.append({
            "promo_type": "free_item",
            "description": text[:200],
            "buy_qty": None,
            "get_qty": None,
            "discount_pct": None,
            "free_item_name": m.group(1).strip(),
        })

    return results


def _other(text: str) -> Dict:
    return {
        "promo_type": "other",
        "description": text[:200],
        "buy_qty": None,
        "get_qty": None,
        "discount_pct": None,
        "free_item_name": None,
    }
