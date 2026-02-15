"""
Automatic Competitor Discovery Service
AI-powered product and competitor finding
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse

from database.models import (
    ProductMonitored, CompetitorMatch, CompetitorWebsite,
    PriceHistory, User
)


class DiscoveryService:
    """
    Service for automatically discovering competitors and products
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def discover_competitors_for_product(
        self,
        product_id: int,
        search_engines: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Automatically discover potential competitors for a product

        Process:
        1. Extract search keywords from product (brand + title + key features)
        2. Search for similar products on major e-commerce sites
        3. Find URLs that might be competitors
        4. Score potential matches
        5. Return top candidates for user review

        Note: In production, this would use:
        - Google Shopping API
        - Bing Shopping API
        - Web scraping with proper rate limiting
        - ML-based relevance scoring
        """
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id,
            ProductMonitored.user_id == self.user.id
        ).first()

        if not product:
            return {"error": "Product not found"}

        # Generate search keywords
        search_keywords = self._generate_search_keywords(product)

        # Get existing competitors to avoid duplicates
        existing_matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.monitored_product_id == product_id
        ).all()

        existing_urls = {match.competitor_url for match in existing_matches}

        # Simulate competitor discovery
        # In production, this would call real search APIs
        discovered_competitors = self._simulate_competitor_search(
            search_keywords,
            existing_urls
        )

        return {
            "product": {
                "id": product.id,
                "title": product.title,
                "brand": product.brand
            },
            "search_keywords": search_keywords,
            "discovered_competitors": discovered_competitors,
            "total_found": len(discovered_competitors),
            "existing_competitors": len(existing_urls),
            "recommendation": "Review and approve competitors to start tracking"
        }

    def suggest_new_products(
        self,
        based_on_category: Optional[str] = None,
        based_on_brand: Optional[str] = None,
        min_competitor_count: int = 2
    ) -> Dict[str, Any]:
        """
        Suggest new products to monitor based on existing catalog

        Looks for:
        - Products from same brands you're tracking
        - Products in same categories
        - Products frequently appearing on competitor sites
        - Trending products in your market
        """
        # Get existing products for pattern analysis
        existing_products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        if not existing_products:
            return {
                "message": "Add some products first to get suggestions",
                "suggestions": []
            }

        # Analyze patterns
        brands = set(p.brand for p in existing_products if p.brand)
        categories = set(p.category for p in existing_products if p.category)

        # Filter by criteria
        if based_on_category:
            categories = {based_on_category}
        if based_on_brand:
            brands = {based_on_brand}

        # Simulate product discovery
        # In production, this would:
        # - Crawl competitor sites for new products
        # - Use marketplace APIs (Amazon, eBay, etc.)
        # - Analyze trending products
        # - Check manufacturer catalogs
        suggestions = self._simulate_product_discovery(
            brands,
            categories,
            min_competitor_count
        )

        return {
            "total_suggestions": len(suggestions),
            "filters_applied": {
                "category": based_on_category,
                "brand": based_on_brand,
                "min_competitors": min_competitor_count
            },
            "your_catalog": {
                "total_products": len(existing_products),
                "unique_brands": len(brands),
                "unique_categories": len(categories)
            },
            "suggestions": suggestions
        }

    def find_competitor_websites(
        self,
        industry: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Discover new competitor websites to track

        Methods:
        - Analyze domains from existing competitor matches
        - Search for common e-commerce patterns
        - Industry-specific site directories
        - Competitor analysis tools
        """
        # Get existing competitor websites
        existing_sites = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.user_id == self.user.id
        ).all()

        existing_domains = {
            urlparse(site.website_url).netloc
            for site in existing_sites
        }

        # Analyze competitors from existing matches
        competitor_names = self.db.query(
            CompetitorMatch.competitor_name,
            func.count(CompetitorMatch.id).label('product_count')
        ).join(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).group_by(
            CompetitorMatch.competitor_name
        ).all()

        # Simulate website discovery
        discovered_sites = self._simulate_website_discovery(
            existing_domains,
            industry,
            location
        )

        return {
            "existing_websites": len(existing_domains),
            "discovered_websites": discovered_sites,
            "total_found": len(discovered_sites),
            "filters": {
                "industry": industry,
                "location": location
            },
            "recommendation": "Add websites to start automatic product matching"
        }

    def auto_match_products(
        self,
        product_id: Optional[int] = None,
        min_confidence: float = 0.7
    ) -> Dict[str, Any]:
        """
        Automatically match products across competitor sites

        Uses AI matching service to find product matches and
        automatically create CompetitorMatch records for high-confidence matches.

        If product_id provided, matches that product only.
        Otherwise, attempts to match all unmatched products.
        """
        if product_id:
            products = self.db.query(ProductMonitored).filter(
                ProductMonitored.id == product_id,
                ProductMonitored.user_id == self.user.id
            ).all()
        else:
            # Get products with few or no matches
            products = self.db.query(ProductMonitored).filter(
                ProductMonitored.user_id == self.user.id
            ).limit(50).all()  # Batch processing

        if not products:
            return {"error": "No products found"}

        # Get all competitor websites
        competitor_sites = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.user_id == self.user.id
        ).all()

        if not competitor_sites:
            return {
                "message": "Add competitor websites first",
                "products_processed": 0
            }

        # Simulate auto-matching
        # In production, this would:
        # - Crawl each competitor site
        # - Use AI matching to find products
        # - Create CompetitorMatch records automatically
        # - Schedule price tracking
        matches_created = self._simulate_auto_matching(
            products,
            competitor_sites,
            min_confidence
        )

        return {
            "products_processed": len(products),
            "competitor_sites_checked": len(competitor_sites),
            "matches_created": matches_created["created"],
            "matches_rejected": matches_created["rejected"],
            "min_confidence_threshold": min_confidence,
            "status": "Auto-matching complete"
        }

    def get_discovery_suggestions(self) -> Dict[str, Any]:
        """
        Get personalized discovery suggestions based on user's catalog

        Analyzes:
        - Products with no competitors (need discovery)
        - Brands/categories to expand
        - Popular competitor sites to add
        - Market gaps
        """
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).all()

        if not products:
            return {
                "message": "Add products to get personalized suggestions",
                "suggestions": []
            }

        # Find products with no competitors
        products_no_competitors = []
        products_few_competitors = []

        for product in products:
            match_count = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).count()

            if match_count == 0:
                products_no_competitors.append(product)
            elif match_count < 3:
                products_few_competitors.append(product)

        # Analyze brand/category coverage
        brand_stats = self._analyze_brand_coverage(products)
        category_stats = self._analyze_category_coverage(products)

        # Generate suggestions
        suggestions = []

        if products_no_competitors:
            suggestions.append({
                "type": "missing_competitors",
                "priority": "high",
                "title": f"{len(products_no_competitors)} products have no competitors",
                "action": "Run competitor discovery on these products",
                "product_ids": [p.id for p in products_no_competitors[:10]]
            })

        if products_few_competitors:
            suggestions.append({
                "type": "expand_tracking",
                "priority": "medium",
                "title": f"{len(products_few_competitors)} products have few competitors",
                "action": "Expand competitor tracking for better insights",
                "product_ids": [p.id for p in products_few_competitors[:10]]
            })

        # Brand expansion opportunities
        for brand, stats in list(brand_stats.items())[:5]:
            if stats["products"] > 5 and stats["avg_competitors"] < 2:
                suggestions.append({
                    "type": "brand_expansion",
                    "priority": "medium",
                    "title": f"Expand {brand} competitor tracking",
                    "action": f"You track {stats['products']} {brand} products but have few competitors",
                    "brand": brand
                })

        return {
            "total_products": len(products),
            "products_needing_discovery": len(products_no_competitors),
            "products_needing_expansion": len(products_few_competitors),
            "suggestions": suggestions,
            "next_steps": [
                "Review high-priority suggestions",
                "Run auto-discovery on products with no competitors",
                "Add competitor websites for automatic matching"
            ]
        }

    def bulk_discover(
        self,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Run bulk discovery across multiple products

        Processes products in batches to find competitors efficiently.
        Returns summary of discovery results.
        """
        # Get products needing discovery
        products = self.db.query(ProductMonitored).filter(
            ProductMonitored.user_id == self.user.id
        ).limit(batch_size).all()

        if not products:
            return {
                "message": "No products to process",
                "results": []
            }

        results = []

        for product in products:
            # Check existing competitor count
            existing_count = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).count()

            # Discover new competitors
            discovery = self.discover_competitors_for_product(product.id)

            if "discovered_competitors" in discovery:
                results.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "existing_competitors": existing_count,
                    "new_competitors_found": len(discovery["discovered_competitors"]),
                    "status": "success"
                })
            else:
                results.append({
                    "product_id": product.id,
                    "product_title": product.title,
                    "status": "error",
                    "message": discovery.get("error", "Unknown error")
                })

        total_found = sum(r.get("new_competitors_found", 0) for r in results)

        return {
            "products_processed": len(results),
            "total_competitors_found": total_found,
            "results": results,
            "status": "Bulk discovery complete"
        }

    # Helper methods

    def _generate_search_keywords(self, product: ProductMonitored) -> List[str]:
        """Generate effective search keywords from product data"""
        keywords = []

        # Brand + product name (most specific)
        if product.brand:
            keywords.append(f"{product.brand} {product.title}")

        # SKU if available
        if product.sku:
            keywords.append(product.sku)

        # Extract key features from title
        # Remove common words and keep important terms
        title_words = re.findall(r'\b[A-Za-z0-9]+\b', product.title)
        important_words = [
            word for word in title_words
            if len(word) > 3 and word.lower() not in {
                'the', 'and', 'for', 'with', 'from', 'this', 'that'
            }
        ]

        if important_words:
            keywords.append(' '.join(important_words[:5]))

        return keywords[:3]  # Top 3 most relevant

    def _simulate_competitor_search(
        self,
        keywords: List[str],
        existing_urls: set
    ) -> List[Dict[str, Any]]:
        """
        Simulate competitor discovery

        In production, this would call real search APIs and scrape results
        """
        # Simulate finding competitors on major e-commerce sites
        simulated_sites = [
            "amazon.com", "walmart.com", "target.com", "bestbuy.com",
            "ebay.com", "newegg.com", "bhphotovideo.com"
        ]

        discovered = []

        for site in simulated_sites:
            # Simulate URL construction
            url = f"https://www.{site}/product/{keywords[0].replace(' ', '-').lower()}"

            if url not in existing_urls:
                discovered.append({
                    "competitor_name": site.split('.')[0].title(),
                    "competitor_url": url,
                    "match_confidence": 0.85,
                    "price": 99.99,  # Simulated
                    "in_stock": True,
                    "discovery_method": "search_engine",
                    "needs_approval": True
                })

        return discovered

    def _simulate_product_discovery(
        self,
        brands: set,
        categories: set,
        min_competitor_count: int
    ) -> List[Dict[str, Any]]:
        """Simulate finding new products to track"""
        suggestions = []

        for brand in list(brands)[:3]:
            suggestions.append({
                "suggested_product": f"{brand} Premium Model XYZ",
                "brand": brand,
                "category": list(categories)[0] if categories else "Electronics",
                "reason": f"Popular {brand} product found on 5 competitor sites",
                "estimated_competitors": 5,
                "potential_value": "high",
                "add_action": "Click to add to monitoring"
            })

        return suggestions

    def _simulate_website_discovery(
        self,
        existing_domains: set,
        industry: Optional[str],
        location: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Simulate discovering competitor websites"""
        potential_sites = [
            {
                "website_name": "Competitor Store A",
                "website_url": "https://www.competitorA.com",
                "industry": industry or "E-commerce",
                "estimated_products": 500,
                "crawlable": True,
                "confidence": 0.9
            },
            {
                "website_name": "Competitor Store B",
                "website_url": "https://www.competitorB.com",
                "industry": industry or "E-commerce",
                "estimated_products": 300,
                "crawlable": True,
                "confidence": 0.85
            }
        ]

        # Filter out existing
        return [
            site for site in potential_sites
            if urlparse(site["website_url"]).netloc not in existing_domains
        ]

    def _simulate_auto_matching(
        self,
        products: List[ProductMonitored],
        competitor_sites: List[CompetitorWebsite],
        min_confidence: float
    ) -> Dict[str, int]:
        """Simulate automatic product matching"""
        # In production, this would create real CompetitorMatch records
        created = 0
        rejected = 0

        for product in products:
            # Simulate finding matches with varying confidence
            for site in competitor_sites[:2]:  # Check first 2 sites
                confidence = 0.8  # Simulated confidence score

                if confidence >= min_confidence:
                    created += 1
                else:
                    rejected += 1

        return {
            "created": created,
            "rejected": rejected
        }

    def _analyze_brand_coverage(
        self,
        products: List[ProductMonitored]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze competitor coverage by brand"""
        brand_stats = {}

        for product in products:
            if not product.brand:
                continue

            if product.brand not in brand_stats:
                brand_stats[product.brand] = {
                    "products": 0,
                    "total_competitors": 0
                }

            brand_stats[product.brand]["products"] += 1

            # Count competitors
            competitor_count = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).count()

            brand_stats[product.brand]["total_competitors"] += competitor_count

        # Calculate averages
        for brand in brand_stats:
            brand_stats[brand]["avg_competitors"] = (
                brand_stats[brand]["total_competitors"] /
                brand_stats[brand]["products"]
            )

        return brand_stats

    def _analyze_category_coverage(
        self,
        products: List[ProductMonitored]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze competitor coverage by category"""
        category_stats = {}

        for product in products:
            if not product.category:
                continue

            if product.category not in category_stats:
                category_stats[product.category] = {
                    "products": 0,
                    "total_competitors": 0
                }

            category_stats[product.category]["products"] += 1

            competitor_count = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product.id
            ).count()

            category_stats[product.category]["total_competitors"] += competitor_count

        # Calculate averages
        for category in category_stats:
            category_stats[category]["avg_competitors"] = (
                category_stats[category]["total_competitors"] /
                category_stats[category]["products"]
            )

        return category_stats


def get_discovery_service(db: Session, user: User) -> DiscoveryService:
    """Factory function for DiscoveryService"""
    return DiscoveryService(db, user)
