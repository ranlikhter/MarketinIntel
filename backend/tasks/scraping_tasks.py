"""
Scraping Background Tasks
Handles automated product scraping
"""

from celery import Task
from celery_app import celery_app
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import ProductMonitored, CompetitorMatch, PriceHistory, CompetitorWebsite
from scrapers.amazon_scraper import AmazonScraper
from matchers.simple_matcher import SimpleProductMatcher
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session handling"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def scrape_single_product(self, product_id: int, website: str = 'amazon.com'):
    """
    Scrape a single product from competitor website

    Args:
        product_id: ID of the product to scrape
        website: Competitor website to scrape
    """
    try:
        logger.info(f"Starting scrape for product {product_id} on {website}")

        # Get product
        product = self.db.query(ProductMonitored).filter(
            ProductMonitored.id == product_id
        ).first()

        if not product:
            logger.error(f"Product {product_id} not found")
            return {'success': False, 'error': 'Product not found'}

        # Get competitor website
        competitor = self.db.query(CompetitorWebsite).filter(
            CompetitorWebsite.base_url.contains(website)
        ).first()

        # Initialize scraper (only Amazon for now)
        if 'amazon' in website.lower():
            scraper = AmazonScraper()
            matcher = SimpleProductMatcher()

            # Run async scrape
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(
                scraper.search_product(product.title, max_results=5)
            )
            loop.close()

            if not results.get('success'):
                raise Exception(results.get('error', 'Scraping failed'))

            matches_found = 0

            # Process each result
            for item in results.get('products', []):
                # Calculate match score
                match_score = matcher.calculate_similarity(
                    product.title,
                    item['title']
                )

                if match_score < 70:  # Skip low confidence matches
                    continue

                # Check if match exists
                existing = self.db.query(CompetitorMatch).filter(
                    CompetitorMatch.product_id == product_id,
                    CompetitorMatch.competitor_url == item['url']
                ).first()

                if existing:
                    # Update existing match
                    existing.latest_price = item['price']
                    existing.stock_status = item['stock_status']
                    existing.last_scraped_at = datetime.utcnow()
                    existing.match_score = match_score
                    match = existing
                else:
                    # Create new match
                    match = CompetitorMatch(
                        product_id=product_id,
                        competitor_website_id=competitor.id if competitor else None,
                        competitor_name=website,
                        competitor_url=item['url'],
                        competitor_product_title=item['title'],
                        latest_price=item['price'],
                        stock_status=item['stock_status'],
                        image_url=item.get('image_url'),
                        match_score=match_score,
                        last_scraped_at=datetime.utcnow()
                    )
                    self.db.add(match)
                    self.db.flush()  # Get match ID

                # Record price history
                if item['price']:
                    price_record = PriceHistory(
                        match_id=match.id,
                        price=item['price'],
                        currency='USD',
                        in_stock=(item['stock_status'] == 'In Stock'),
                        timestamp=datetime.utcnow()
                    )
                    self.db.add(price_record)

                matches_found += 1

            self.db.commit()

            logger.info(f"Successfully scraped product {product_id}: {matches_found} matches found")

            return {
                'success': True,
                'product_id': product_id,
                'matches_found': matches_found,
                'timestamp': datetime.utcnow().isoformat()
            }

        else:
            return {'success': False, 'error': f'Unsupported website: {website}'}

    except Exception as e:
        logger.error(f"Error scraping product {product_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(base=DatabaseTask, bind=True)
def scrape_all_products(self):
    """
    Scrape all active products
    Runs on schedule (every 6 hours by default)
    """
    try:
        logger.info("Starting bulk scrape for all products")

        # Get all products
        products = self.db.query(ProductMonitored).all()

        if not products:
            logger.warning("No products found to scrape")
            return {'success': True, 'message': 'No products to scrape'}

        # Queue individual scrape tasks
        tasks = []
        for product in products:
            task = scrape_single_product.delay(product.id)
            tasks.append(task.id)

        logger.info(f"Queued {len(tasks)} scraping tasks")

        return {
            'success': True,
            'products_queued': len(tasks),
            'task_ids': tasks,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in bulk scrape: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def scrape_products_by_priority(self):
    """
    Scrape products based on priority
    - Products not scraped in 24h get highest priority
    - Products with price volatility get medium priority
    """
    try:
        logger.info("Starting priority-based scraping")

        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Get products that haven't been scraped recently
        stale_products = self.db.query(ProductMonitored).join(
            CompetitorMatch
        ).filter(
            CompetitorMatch.last_scraped_at < cutoff_time
        ).distinct().limit(50).all()

        # Queue scraping tasks
        tasks = []
        for product in stale_products:
            task = scrape_single_product.delay(product.id)
            tasks.append(task.id)

        logger.info(f"Queued {len(tasks)} priority scraping tasks")

        return {
            'success': True,
            'priority_products_queued': len(tasks),
            'task_ids': tasks
        }

    except Exception as e:
        logger.error(f"Error in priority scraping: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def retry_failed_scrapes(self):
    """
    Retry scrapes that failed in the last 24 hours
    """
    try:
        logger.info("Retrying failed scrapes")

        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Get matches with old scrape times (likely failed)
        failed_matches = self.db.query(CompetitorMatch).filter(
            CompetitorMatch.last_scraped_at < cutoff_time
        ).limit(20).all()

        tasks = []
        for match in failed_matches:
            task = scrape_single_product.delay(match.product_id)
            tasks.append(task.id)

        logger.info(f"Queued {len(tasks)} retry tasks")

        return {
            'success': True,
            'retries_queued': len(tasks),
            'task_ids': tasks
        }

    except Exception as e:
        logger.error(f"Error retrying failed scrapes: {e}")
        return {'success': False, 'error': str(e)}
