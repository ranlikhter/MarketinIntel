"""
Site Crawler API Endpoints
Automatically discover and scrape competitor websites
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from utils.time import utcnow

from database.connection import get_db
from database.models import ProductMonitored, CompetitorMatch, CompetitorWebsite
from scrapers.site_crawler import SiteCrawler

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


# Global crawl status storage (in production, use Redis or database)
crawl_status = {}


@router.post("/start", response_model=CrawlStatus)
async def start_site_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start automatic site crawl to discover all products

    - **base_url**: Competitor website URL
    - **max_products**: Maximum products to discover (default: 50)
    - **max_depth**: Crawl depth (default: 3)
    - **auto_import**: Automatically import discovered products (default: true)
    - **competitor_name**: Name for competitor website
    """
    try:
        base_url_str = str(request.base_url)

        # Check if competitor exists
        competitor = None
        if request.competitor_name:
            competitor = db.query(CompetitorWebsite).filter(
                CompetitorWebsite.name == request.competitor_name
            ).first()

            if not competitor:
                # Create competitor entry
                competitor = CompetitorWebsite(
                    name=request.competitor_name,
                    base_url=base_url_str,
                    website_type='auto_discovered'
                )
                db.add(competitor)
                db.commit()
                db.refresh(competitor)

        # Initialize crawler
        crawler = SiteCrawler()

        # Start crawl
        result = await crawler.crawl_site(
            base_url=base_url_str,
            max_products=request.max_products,
            max_depth=request.max_depth
        )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Crawl failed'))

        # Auto-import products if requested
        products_imported = 0
        if request.auto_import and result.get('products'):
            for product_data in result['products']:
                try:
                    # Check if product exists
                    existing = db.query(ProductMonitored).filter(
                        ProductMonitored.title == product_data['title']
                    ).first()

                    if not existing:
                        # Create new product
                        new_product = ProductMonitored(
                            title=product_data['title'],
                            image_url=product_data.get('image_url')
                        )
                        db.add(new_product)
                        db.commit()
                        db.refresh(new_product)

                        # Create competitor match
                        if competitor:
                            match = CompetitorMatch(
                                monitored_product_id=new_product.id,
                                competitor_website_id=competitor.id,
                                competitor_name=competitor.name,
                                competitor_url=product_data['url'],
                                competitor_product_title=product_data['title'],
                                latest_price=product_data.get('price'),
                                stock_status=product_data.get('stock_status'),
                                image_url=product_data.get('image_url'),
                                last_scraped_at=utcnow(),
                            )
                            db.add(match)

                        products_imported += 1

                except Exception as e:
                    logger.error(f"Error importing product: {e}")
                    continue

            db.commit()

        return CrawlStatus(
            status='completed',
            message=f'Successfully crawled {base_url_str}',
            categories_found=result['categories_found'],
            products_found=result['products_found'],
            products_imported=products_imported
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover-categories")
async def discover_categories(request: CrawlRequest):
    """
    Quickly discover category pages without scraping products

    - **base_url**: Competitor website URL
    """
    try:
        crawler = SiteCrawler()

        categories = await crawler.discover_categories(str(request.base_url))

        return {
            'success': True,
            'base_url': str(request.base_url),
            'categories_found': len(categories),
            'categories': categories
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{crawl_id}")
async def get_crawl_status(crawl_id: str):
    """Get status of ongoing crawl (for background tasks)"""
    if crawl_id not in crawl_status:
        raise HTTPException(status_code=404, detail="Crawl not found")

    return crawl_status[crawl_id]
