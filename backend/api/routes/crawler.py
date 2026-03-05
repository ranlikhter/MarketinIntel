"""
Site Crawler API Endpoints
Automatically discover and scrape competitor websites.

Security:
- All endpoints require authentication.
- URLs are validated against SSRF to prevent crawling internal infrastructure.
- Rate-limited to 10 crawl starts per hour (expensive operation).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, CompetitorWebsite, User
from scrapers.site_crawler import SiteCrawler
from api.dependencies import get_current_user
from api.limiter import limiter
from services.ssrf_validator import validate_external_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawler", tags=["crawler"])


# Pydantic models
class CrawlRequest(BaseModel):
    base_url: HttpUrl
    max_products: Optional[int] = 50
    max_depth: Optional[int] = 3
    auto_import: Optional[bool] = True
    competitor_name: Optional[str] = None


class CrawlStatus(BaseModel):
    status: str
    message: str
    categories_found: int = 0
    products_found: int = 0
    products_imported: int = 0


# In-process crawl status store (use Redis/DB in production for multi-worker envs)
crawl_status = {}


@router.post("/start", response_model=CrawlStatus)
@limiter.limit("10/hour")
async def start_site_crawl(
    request: Request,
    crawl_request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start automatic site crawl to discover all products.

    - **base_url**: Competitor website URL (must be a public, external host)
    - **max_products**: Maximum products to discover (default: 50)
    - **max_depth**: Crawl depth (default: 3)
    - **auto_import**: Automatically import discovered products (default: true)
    - **competitor_name**: Name for the competitor website entry
    """
    try:
        base_url_str = str(crawl_request.base_url)

        # SSRF protection — block private/internal URLs
        validate_external_url(base_url_str, field_name="base_url")

        # Look up or create the competitor entry scoped to this user
        competitor = None
        if crawl_request.competitor_name:
            competitor = db.query(CompetitorWebsite).filter(
                CompetitorWebsite.name == crawl_request.competitor_name,
                CompetitorWebsite.user_id == current_user.id,
            ).first()

            if not competitor:
                competitor = CompetitorWebsite(
                    user_id=current_user.id,
                    name=crawl_request.competitor_name,
                    base_url=base_url_str,
                    website_type="auto_discovered",
                )
                db.add(competitor)
                db.commit()
                db.refresh(competitor)

        # Initialize crawler and run
        crawler = SiteCrawler()
        result = await crawler.crawl_site(
            base_url=base_url_str,
            max_products=crawl_request.max_products,
            max_depth=crawl_request.max_depth,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Crawl failed"))

        # Auto-import discovered products
        products_imported = 0
        if crawl_request.auto_import and result.get("products"):
            for product_data in result["products"]:
                try:
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.title == product_data["title"],
                        ProductMonitored.user_id == current_user.id,
                    ).first()

                    if not existing:
                        new_product = ProductMonitored(
                            user_id=current_user.id,
                            title=product_data["title"],
                            image_url=product_data.get("image_url"),
                        )
                        db.add(new_product)
                        db.commit()
                        db.refresh(new_product)

                        if competitor:
                            match = CompetitorMatch(
                                monitored_product_id=new_product.id,
                                competitor_website_id=competitor.id,
                                competitor_name=competitor.name,
                                competitor_url=product_data["url"],
                                competitor_product_title=product_data["title"],
                                latest_price=product_data.get("price"),
                                stock_status=product_data.get("stock_status"),
                                image_url=product_data.get("image_url"),
                                last_scraped_at=datetime.utcnow(),
                            )
                            db.add(match)

                        products_imported += 1

                except Exception as e:
                    logger.error("Error importing crawled product: %s", e)
                    continue

            db.commit()

        return CrawlStatus(
            status="completed",
            message=f"Successfully crawled {base_url_str}",
            categories_found=result["categories_found"],
            products_found=result["products_found"],
            products_imported=products_imported,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover-categories")
@limiter.limit("20/hour")
async def discover_categories(
    request: Request,
    crawl_request: CrawlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Quickly discover category pages without scraping products.

    - **base_url**: Competitor website URL (must be a public, external host)
    """
    try:
        base_url_str = str(crawl_request.base_url)
        validate_external_url(base_url_str, field_name="base_url")

        crawler = SiteCrawler()
        categories = await crawler.discover_categories(base_url_str)

        return {
            "success": True,
            "base_url": base_url_str,
            "categories_found": len(categories),
            "categories": categories,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{crawl_id}")
async def get_crawl_status(
    crawl_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get status of an ongoing crawl job."""
    if crawl_id not in crawl_status:
        raise HTTPException(status_code=404, detail="Crawl not found")

    return crawl_status[crawl_id]
