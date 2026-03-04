"""
Automatic Competitor Discovery Service

Tier 1 (always works, no API keys):
  - Mines existing CompetitorMatch / CompetitorWebsite data from the DB
  - Constructs verifiable search URLs on major marketplaces so users can
    click through and confirm matches themselves
  - Builds site-search URLs for the user's already-configured competitor sites

Tier 2 (optional, set SERPAPI_KEY in .env):
  - Calls SerpAPI's Google Shopping endpoint to get real prices, URLs and
    retailer names for any search query

Tier 3 (optional, set GOOGLE_CSE_KEY + GOOGLE_CSE_ID in .env):
  - Calls Google Custom Search API as an alternative to SerpAPI

Tier 2/3 are drop-in upgrades — no code changes needed, just env vars.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, quote_plus

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    CompetitorMatch,
    CompetitorWebsite,
    PriceHistory,
    ProductMonitored,
    User,
)

logger = logging.getLogger(__name__)

# Well-known marketplaces: used for constructing search deep-links when no
# external search API is configured.
_MARKETPLACE_SEARCH_TEMPLATES = {
    "Amazon": "https://www.amazon.com/s?k={query}",
    "Walmart": "https://www.walmart.com/search?q={query}",
    "Target": "https://www.target.com/s?searchTerm={query}",
    "eBay": "https://www.ebay.com/sch/i.html?_nkw={query}",
    "Best Buy": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
    "Newegg": "https://www.newegg.com/p/pl?d={query}",
}

_REQUEST_TIMEOUT = 8  # seconds for external API calls


class DiscoveryService:
    """
    Service for automatically discovering competitors and products.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    # ── Public API ────────────────────────────────────────────────────────────

    def discover_competitors_for_product(
        self,
        product_id: int,
        search_engines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Discover potential competitors for a product.

        Strategy (highest to lowest quality):
          1. SerpAPI Google Shopping (if SERPAPI_KEY set)
          2. Google Custom Search (if GOOGLE_CSE_KEY + GOOGLE_CSE_ID set)
          3. User's configured CompetitorWebsite search URLs (free, always)
          4. Deep-link search URLs on major marketplaces (free, always)
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id,
        ).first()

        if not product:
            return {"error": "Product not found"}

        search_keywords = self._generate_search_keywords(product)
        existing_matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()
        existing_urls = {m.competitor_url for m in existing_matches}

        discovered = self._real_competitor_search(search_keywords, existing_urls)

        return {
            "product": {"id": product.id, "title": product.title, "brand": product.brand},
            "search_keywords": search_keywords,
            "discovered_competitors": discovered,
            "total_found": len(discovered),
            "existing_competitors": len(existing_urls),
            "recommendation": "Review and approve competitors to start tracking",
        }

    def suggest_new_products(
        self,
        based_on_category: Optional[str] = None,
        based_on_brand: Optional[str] = None,
        min_competitor_count: int = 2,
    ) -> Dict[str, Any]:
        """
        Suggest new products to add based on the user's existing catalog.

        Sources:
          - Other products seen on competitor sites (from CompetitorMatch titles)
          - SerpAPI / Google CSE search if a brand/category filter is given
        """
        existing_products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        if not existing_products:
            return {"message": "Add some products first to get suggestions", "suggestions": []}

        brands = {p.brand for p in existing_products if p.brand}
        categories: set = set()
        for p in existing_products:
            for m in p.competitor_matches:
                if m.category:
                    categories.add(m.category)

        if based_on_category:
            categories = {based_on_category}
        if based_on_brand:
            brands = {based_on_brand}

        suggestions = self._real_product_discovery(brands, categories, existing_products)

        return {
            "total_suggestions": len(suggestions),
            "filters_applied": {
                "category": based_on_category,
                "brand": based_on_brand,
                "min_competitors": min_competitor_count,
            },
            "your_catalog": {
                "total_products": len(existing_products),
                "unique_brands": len(brands),
                "unique_categories": len(categories),
            },
            "suggestions": suggestions,
        }

    def find_competitor_websites(
        self,
        industry: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Discover competitor websites not yet in the user's CompetitorWebsite list.

        Strategy:
          - Mine domains from existing CompetitorMatch records (data-driven, free)
          - Rank by how many of the user's products already appear on each domain
        """
        existing_sites = self.db.query(CompetitorWebsite).all()
        existing_domains = {urlparse(s.base_url).netloc.lower() for s in existing_sites}

        discovered = self._real_website_discovery(existing_domains, industry, location)

        return {
            "existing_websites": len(existing_domains),
            "discovered_websites": discovered,
            "total_found": len(discovered),
            "filters": {"industry": industry, "location": location},
            "recommendation": "Add websites to start automatic product matching",
        }

    def auto_match_products(
        self,
        product_id: Optional[int] = None,
        min_confidence: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Queue an auto-match Celery task that crawls competitor sites and creates
        CompetitorMatch records for high-confidence candidates.

        Returns immediately; the actual crawl runs in a Celery worker.
        """
        if product_id:
            products = self.db.query(ProductMonitored).filter(
                ProductMonitored.id == product_id,
                ProductMonitored.user_id == self.user.id,
            ).all()
        else:
            products = self.db.query(ProductMonitored).filter(
                ProductMonitored.user_id == self.user.id
            ).limit(50).all()

        if not products:
            return {"error": "No products found"}

        competitor_sites = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.is_active == True  # noqa: E712
        ).all()

        if not competitor_sites:
            return {
                "message": "Add competitor websites first before running auto-match",
                "products_processed": 0,
            }

        # Dispatch a Celery task per product so each crawl is independent and
        # can be retried without re-doing the whole batch.
        queued = 0
        task_ids = []
        try:
            from tasks.discovery_tasks import auto_match_product_task
            for product in products:
                site_ids = [s.id for s in competitor_sites]
                task = auto_match_product_task.delay(
                    product.id, site_ids, min_confidence
                )
                task_ids.append(task.id)
                queued += 1
        except Exception as exc:
            logger.error("Failed to queue auto-match tasks: %s", exc)
            return {"error": f"Failed to queue tasks: {exc}"}

        return {
            "products_queued": queued,
            "competitor_sites_to_check": len(competitor_sites),
            "min_confidence_threshold": min_confidence,
            "task_ids": task_ids,
            "status": "Auto-match queued — results will appear as matches are confirmed",
        }

    def get_discovery_suggestions(self) -> Dict[str, Any]:
        """
        Return personalized suggestions by analyzing coverage gaps in the catalog.
        This method is data-only (no external I/O) and always returns real insights.
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        if not products:
            return {
                "message": "Add products to get personalized suggestions",
                "suggestions": [],
            }

        products_no_competitors = []
        products_few_competitors = []

        for product in products:
            match_count = len(product.competitor_matches)
            if match_count == 0:
                products_no_competitors.append(product)
            elif match_count < 3:
                products_few_competitors.append(product)

        brand_stats = self._analyze_brand_coverage(products)

        suggestions = []

        if products_no_competitors:
            suggestions.append({
                "type": "missing_competitors",
                "priority": "high",
                "title": f"{len(products_no_competitors)} products have no competitors",
                "action": "Run competitor discovery on these products",
                "product_ids": [p.id for p in products_no_competitors[:10]],
            })

        if products_few_competitors:
            suggestions.append({
                "type": "expand_tracking",
                "priority": "medium",
                "title": f"{len(products_few_competitors)} products have fewer than 3 competitors",
                "action": "Expand competitor tracking for better insights",
                "product_ids": [p.id for p in products_few_competitors[:10]],
            })

        for brand, stats in list(brand_stats.items())[:5]:
            if stats["products"] > 5 and stats["avg_competitors"] < 2:
                suggestions.append({
                    "type": "brand_expansion",
                    "priority": "medium",
                    "title": f"Expand {brand} competitor tracking",
                    "action": f"You track {stats['products']} {brand} products but average only {stats['avg_competitors']:.1f} competitors",
                    "brand": brand,
                })

        return {
            "total_products": len(products),
            "products_needing_discovery": len(products_no_competitors),
            "products_needing_expansion": len(products_few_competitors),
            "suggestions": suggestions,
            "next_steps": [
                "Review high-priority suggestions",
                "Run auto-discovery on products with no competitors",
                "Add competitor websites for automatic matching",
            ],
        }

    def bulk_discover(self, batch_size: int = 10) -> Dict[str, Any]:
        """Run discovery on the next batch of products that need it."""
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).limit(batch_size).all()

        if not products:
            return {"message": "No products to process", "results": []}

        results = []
        for product in products:
            existing_count = len(product.competitor_matches)
            discovery = self.discover_competitors_for_product(product.id)
            if "discovered_competitors" in discovery:
                results.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "existing_competitors": existing_count,
                    "new_competitors_found": len(discovery["discovered_competitors"]),
                    "status": "success",
                })
            else:
                results.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "status": "error",
                    "message": discovery.get("error", "Unknown error"),
                })

        return {
            "products_processed": len(results),
            "total_competitors_found": sum(r.get("new_competitors_found", 0) for r in results),
            "results": results,
            "status": "Bulk discovery complete",
        }

    # ── Real search implementations ───────────────────────────────────────────

    def _real_competitor_search(
        self, keywords: List[str], existing_urls: set
    ) -> List[Dict[str, Any]]:
        """
        Run a tiered competitor search and return de-duplicated results.

        Tier 1: SerpAPI Google Shopping
        Tier 2: Google Custom Search Engine
        Tier 3: User's configured competitor site search URLs
        Tier 4: Major marketplace deep-link search URLs (always included)
        """
        results: List[Dict[str, Any]] = []
        primary_query = keywords[0] if keywords else ""

        # Tier 1 — SerpAPI (best quality; returns real prices)
        serpapi_key = os.getenv("SERPAPI_KEY")
        if serpapi_key and primary_query:
            try:
                results.extend(self._search_serpapi(primary_query, serpapi_key))
            except Exception as exc:
                logger.warning("SerpAPI search failed: %s", exc)

        # Tier 2 — Google Custom Search (fallback if no SerpAPI)
        if not results:
            google_cse_key = os.getenv("GOOGLE_CSE_KEY")
            google_cse_id = os.getenv("GOOGLE_CSE_ID")
            if google_cse_key and google_cse_id and primary_query:
                try:
                    results.extend(
                        self._search_google_cse(primary_query, google_cse_key, google_cse_id)
                    )
                except Exception as exc:
                    logger.warning("Google CSE search failed: %s", exc)

        # Tier 3 — Search URLs on user's configured competitor sites
        results.extend(self._search_known_competitor_sites(keywords))

        # Tier 4 — Deep-link search URLs on major marketplaces (always shown)
        results.extend(self._build_marketplace_search_links(primary_query, existing_urls))

        # Deduplicate by URL while preserving order (best results first)
        seen = set(existing_urls)
        unique: List[Dict[str, Any]] = []
        for item in results:
            url = item.get("competitor_url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(item)

        return unique

    def _search_serpapi(self, query: str, api_key: str) -> List[Dict[str, Any]]:
        """Call SerpAPI Google Shopping and normalise results."""
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": api_key, "tbm": "shop", "num": 10},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("shopping_results", [])[:10]:
            url = item.get("link") or item.get("product_link", "")
            if not url:
                continue
            results.append({
                "competitor_name": item.get("source") or urlparse(url).netloc,
                "competitor_url": url,
                "match_confidence": 0.88,
                "price": self._parse_price(item.get("price", "")),
                "in_stock": True,
                "discovery_method": "serpapi_shopping",
                "needs_approval": True,
                "thumbnail": item.get("thumbnail"),
            })
        return results

    def _search_google_cse(
        self, query: str, api_key: str, cse_id: str
    ) -> List[Dict[str, Any]]:
        """Call Google Custom Search API and normalise results."""
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"q": query, "key": api_key, "cx": cse_id, "num": 10},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", [])[:10]:
            url = item.get("link", "")
            if not url:
                continue
            results.append({
                "competitor_name": item.get("displayLink") or urlparse(url).netloc,
                "competitor_url": url,
                "match_confidence": 0.82,
                "price": None,
                "in_stock": None,
                "discovery_method": "google_cse",
                "needs_approval": True,
                "snippet": item.get("snippet", "")[:200],
            })
        return results

    def _search_known_competitor_sites(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Build site-search URLs for competitor websites the user has already
        configured. These are real clickable URLs, not scraped prices.
        """
        sites = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.is_active == True  # noqa: E712
        ).all()

        results = []
        primary_query = keywords[0] if keywords else ""

        for site in sites[:8]:
            search_url = self._build_site_search_url(site.base_url, primary_query)
            if not search_url:
                continue
            results.append({
                "competitor_name": site.name,
                "competitor_url": search_url,
                "match_confidence": 0.65,
                "price": None,
                "in_stock": None,
                "discovery_method": "configured_site_search",
                "needs_approval": True,
                "note": f"Search results on {site.name} — click to verify the match",
            })
        return results

    def _build_marketplace_search_links(
        self, query: str, existing_urls: set
    ) -> List[Dict[str, Any]]:
        """
        Always-available fallback: construct search URLs on major marketplaces.
        These are ready-to-click links users can use to manually find and add
        the competitor URL. No API key required.
        """
        if not query:
            return []
        encoded = quote_plus(query)
        results = []
        for name, template in _MARKETPLACE_SEARCH_TEMPLATES.items():
            url = template.format(query=encoded)
            if url not in existing_urls:
                results.append({
                    "competitor_name": name,
                    "competitor_url": url,
                    "match_confidence": 0.50,
                    "price": None,
                    "in_stock": None,
                    "discovery_method": "marketplace_search_link",
                    "needs_approval": True,
                    "note": f"Search page on {name} — find and copy the specific product URL",
                })
        return results

    def _real_website_discovery(
        self,
        existing_domains: set,
        industry: Optional[str],
        location: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Mine existing CompetitorMatch data to find domains that appear in the
        user's match records but haven't been added as CompetitorWebsite entries
        yet. Ranked by how many of the user's products have matches on that domain.
        """
        all_match_urls = (
            self.db.query(CompetitorMatch.competitor_url)
            .join(ProductMonitored)
            .filter(
                ProductMonitored.user_id == self.user.id,
                CompetitorMatch.competitor_url.isnot(None),
            )
            .all()
        )

        domain_product_counts: Dict[str, int] = {}
        for (url,) in all_match_urls:
            try:
                domain = urlparse(url).netloc.lower()
                if domain and domain not in existing_domains:
                    domain_product_counts[domain] = domain_product_counts.get(domain, 0) + 1
            except Exception:
                pass

        results = []
        for domain, count in sorted(domain_product_counts.items(), key=lambda x: -x[1])[:15]:
            results.append({
                "website_name": domain.split(".")[0].title(),
                "website_url": f"https://{domain}",
                "estimated_products": count,
                "crawlable": True,
                "confidence": round(min(0.5 + count * 0.1, 1.0), 2),
                "source": "existing_match_data",
                "note": f"Found {count} of your products already matched on this domain",
            })

        return results

    def _real_product_discovery(
        self,
        brands: set,
        categories: set,
        existing_products: List[ProductMonitored],
    ) -> List[Dict[str, Any]]:
        """
        Suggest new products by examining titles of competitor products that are
        already in CompetitorMatch but NOT in the user's monitored catalog.

        This is entirely data-driven — no external API calls needed.
        """
        existing_titles_lower = {p.title.lower() for p in existing_products}
        suggestions: List[Dict[str, Any]] = []
        seen_titles: set = set()

        # Pull competitor product titles from existing matches
        competitor_products = (
            self.db.query(
                CompetitorMatch.competitor_product_title,
                CompetitorMatch.competitor_name,
                CompetitorMatch.latest_price,
                CompetitorMatch.category,
                func.count(CompetitorMatch.id).label("site_count"),
            )
            .join(ProductMonitored)
            .filter(
                ProductMonitored.user_id == self.user.id,
                CompetitorMatch.competitor_product_title.isnot(None),
            )
            .group_by(
                CompetitorMatch.competitor_product_title,
                CompetitorMatch.competitor_name,
                CompetitorMatch.latest_price,
                CompetitorMatch.category,
            )
            .order_by(func.count(CompetitorMatch.id).desc())
            .limit(200)
            .all()
        )

        for row in competitor_products:
            title = row.competitor_product_title
            if not title or title.lower() in existing_titles_lower:
                continue

            title_key = title.lower()[:60]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # Brand filter
            if brands:
                title_words = set(title.lower().split())
                if not any(b.lower() in title_words for b in brands):
                    continue

            # Category filter
            if categories and row.category and not any(
                c.lower() in (row.category or "").lower() for c in categories
            ):
                continue

            suggestions.append({
                "suggested_product": title,
                "brand": next(
                    (b for b in brands if b.lower() in title.lower()), None
                ),
                "category": row.category,
                "reason": f"Seen on {row.site_count} competitor site(s) but not in your catalog",
                "estimated_competitors": row.site_count,
                "sample_price": row.latest_price,
                "potential_value": "high" if row.site_count >= 3 else "medium",
                "add_action": "Click to add to monitoring",
                "source": "competitor_catalog_mining",
            })

            if len(suggestions) >= 20:
                break

        # If we got nothing from mining (new user), offer search-link suggestions
        if not suggestions and brands:
            for brand in list(brands)[:3]:
                query = quote_plus(brand)
                suggestions.append({
                    "suggested_product": f"Search {brand} products",
                    "brand": brand,
                    "category": next(iter(categories), None),
                    "reason": f"Explore {brand} products across marketplaces",
                    "search_url": f"https://www.amazon.com/s?k={query}",
                    "potential_value": "unknown",
                    "add_action": "Search and add products manually",
                    "source": "marketplace_search_link",
                })

        return suggestions

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _generate_search_keywords(self, product: ProductMonitored) -> List[str]:
        """Build search queries ranked by specificity."""
        keywords = []

        # Most specific: UPC/EAN (guaranteed unique)
        if product.upc_ean:
            keywords.append(product.upc_ean)

        # MPN — manufacturer part number
        if product.mpn:
            keywords.append(product.mpn)

        # Brand + title
        if product.brand:
            keywords.append(f"{product.brand} {product.title}")

        # SKU
        if product.sku:
            keywords.append(product.sku)

        # Title keywords fallback
        if not keywords:
            title_words = re.findall(r"\b[A-Za-z0-9]+\b", product.title)
            important = [
                w for w in title_words
                if len(w) > 3 and w.lower() not in {"the", "and", "for", "with", "from", "this", "that"}
            ]
            if important:
                keywords.append(" ".join(important[:6]))

        return keywords[:4]

    @staticmethod
    def _parse_price(raw: str) -> Optional[float]:
        """Extract a float from a price string like '$29.99' or '29,99'."""
        if not raw:
            return None
        cleaned = re.sub(r"[^\d.,]", "", str(raw)).replace(",", ".")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _build_site_search_url(base_url: str, query: str) -> Optional[str]:
        """
        Construct a best-effort search URL for a given site.
        Tries common search parameter patterns; returns None if base_url is empty.
        """
        if not base_url or not query:
            return None
        encoded = quote_plus(query)
        domain = urlparse(base_url).netloc.lower()

        # Known patterns for common platforms
        if "shopify" in domain or domain.endswith(".myshopify.com"):
            return f"{base_url.rstrip('/')}/search?q={encoded}"
        if "woocommerce" in base_url or "wp-content" in base_url:
            return f"{base_url.rstrip('/')}/?s={encoded}&post_type=product"
        if "magento" in base_url:
            return f"{base_url.rstrip('/')}/catalogsearch/result/?q={encoded}"
        if "bigcommerce" in domain:
            return f"{base_url.rstrip('/')}/search.php?search_query={encoded}"

        # Generic: try `?q=` and `?search=` — most search engines use one of these
        return f"{base_url.rstrip('/')}/search?q={encoded}"

    def _analyze_brand_coverage(
        self, products: List[ProductMonitored]
    ) -> Dict[str, Dict[str, Any]]:
        brand_stats: Dict[str, Dict[str, Any]] = {}
        for product in products:
            if not product.brand:
                continue
            if product.brand not in brand_stats:
                brand_stats[product.brand] = {"products": 0, "total_competitors": 0}
            brand_stats[product.brand]["products"] += 1
            brand_stats[product.brand]["total_competitors"] += len(product.competitor_matches)
        for brand in brand_stats:
            prods = brand_stats[brand]["products"]
            brand_stats[brand]["avg_competitors"] = (
                brand_stats[brand]["total_competitors"] / prods if prods else 0
            )
        return brand_stats

    def _analyze_category_coverage(
        self, products: List[ProductMonitored]
    ) -> Dict[str, Dict[str, Any]]:
        category_stats: Dict[str, Dict[str, Any]] = {}
        for product in products:
            for m in product.competitor_matches:
                if not m.category:
                    continue
                cat = m.category
                if cat not in category_stats:
                    category_stats[cat] = {"products": 0, "total_competitors": 0}
                category_stats[cat]["products"] += 1
                category_stats[cat]["total_competitors"] += len(product.competitor_matches)
        for cat in category_stats:
            prods = category_stats[cat]["products"]
            category_stats[cat]["avg_competitors"] = (
                category_stats[cat]["total_competitors"] / prods if prods else 0
            )
        return category_stats


def get_discovery_service(db: Session, user: User) -> DiscoveryService:
    return DiscoveryService(db, user)
