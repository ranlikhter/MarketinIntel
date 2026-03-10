"""
Price Analytics Service
Calculates trends, averages, and insights from price history data
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from utils.time import utcnow
from typing import List, Dict, Optional
import logging

from database.models import PriceHistory, CompetitorMatch, ProductMonitored

logger = logging.getLogger(__name__)


class PriceAnalytics:
    """Service for calculating price trends and analytics"""

    def __init__(self, db: Session):
        self.db = db

    def get_product_trendline(
        self,
        product_id: int,
        days: int = 30
    ) -> Dict:
        """
        Get daily price trendline for a product

        Args:
            product_id: Product to analyze
            days: Number of days to look back (default: 30)

        Returns:
            Dict with trendline data and insights
        """
        try:
            # Get date range
            end_date = utcnow()
            start_date = end_date - timedelta(days=days)

            # Get all competitor matches for this product
            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id
            ).all()

            if not matches:
                return {
                    'success': False,
                    'message': 'No competitor data found'
                }

            # Get daily price data for each competitor
            competitors_data = []
            all_daily_prices = []

            for match in matches:
                # Get price history for this competitor
                price_data = self.db.query(
                    func.date(PriceHistory.timestamp).label('date'),
                    func.avg(PriceHistory.price).label('avg_price'),
                    func.min(PriceHistory.price).label('min_price'),
                    func.max(PriceHistory.price).label('max_price'),
                    func.count(PriceHistory.id).label('count')
                ).filter(
                    and_(
                        PriceHistory.match_id == match.id,
                        PriceHistory.timestamp >= start_date,
                        PriceHistory.timestamp <= end_date
                    )
                ).group_by(
                    func.date(PriceHistory.timestamp)
                ).order_by(
                    func.date(PriceHistory.timestamp)
                ).all()

                if price_data:
                    daily_prices = [
                        {
                            'date': str(row.date),
                            'avg_price': float(row.avg_price),
                            'min_price': float(row.min_price),
                            'max_price': float(row.max_price),
                            'count': row.count
                        }
                        for row in price_data
                    ]

                    competitors_data.append({
                        'competitor_id': match.id,
                        'competitor_name': match.competitor_name,
                        'daily_prices': daily_prices
                    })

                    all_daily_prices.extend(daily_prices)

            # Calculate overall daily averages (across all competitors)
            daily_aggregates = {}
            for item in all_daily_prices:
                date = item['date']
                if date not in daily_aggregates:
                    daily_aggregates[date] = {
                        'prices': [],
                        'date': date
                    }
                daily_aggregates[date]['prices'].append(item['avg_price'])

            # Calculate daily stats
            daily_trend = []
            for date, data in sorted(daily_aggregates.items()):
                prices = data['prices']
                daily_trend.append({
                    'date': date,
                    'avg_price': sum(prices) / len(prices),
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'competitor_count': len(prices)
                })

            # Calculate trend insights
            insights = self._calculate_insights(daily_trend)

            return {
                'success': True,
                'product_id': product_id,
                'date_range': {
                    'start': str(start_date.date()),
                    'end': str(end_date.date()),
                    'days': days
                },
                'daily_trend': daily_trend,
                'by_competitor': competitors_data,
                'insights': insights
            }

        except Exception as e:
            logger.exception(f"Error calculating trendline: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _calculate_insights(self, daily_trend: List[Dict]) -> Dict:
        """Calculate trend insights from daily data"""
        if not daily_trend:
            return {}

        prices = [d['avg_price'] for d in daily_trend]

        # Current vs oldest
        current_price = prices[-1]
        oldest_price = prices[0]
        price_change = current_price - oldest_price
        price_change_pct = (price_change / oldest_price * 100) if oldest_price > 0 else 0

        # Average price
        avg_price = sum(prices) / len(prices)

        # Lowest and highest in period
        lowest_price = min(prices)
        highest_price = max(prices)

        # Trend direction (simple linear)
        trend_direction = 'stable'
        if abs(price_change_pct) > 5:
            trend_direction = 'increasing' if price_change > 0 else 'decreasing'

        # Volatility (standard deviation)
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        volatility = (std_dev / mean * 100) if mean > 0 else 0

        # Price stability (how often price changes)
        price_changes = sum(1 for i in range(1, len(prices)) if prices[i] != prices[i-1])
        stability_score = 100 - (price_changes / len(prices) * 100)

        return {
            'current_price': round(current_price, 2),
            'oldest_price': round(oldest_price, 2),
            'price_change': round(price_change, 2),
            'price_change_pct': round(price_change_pct, 2),
            'avg_price_period': round(avg_price, 2),
            'lowest_price': round(lowest_price, 2),
            'highest_price': round(highest_price, 2),
            'price_range': round(highest_price - lowest_price, 2),
            'trend_direction': trend_direction,
            'volatility_pct': round(volatility, 2),
            'stability_score': round(stability_score, 2),
            'recommendation': self._get_recommendation(
                current_price,
                avg_price,
                trend_direction,
                volatility
            )
        }

    def _get_recommendation(
        self,
        current_price: float,
        avg_price: float,
        trend: str,
        volatility: float
    ) -> str:
        """Generate pricing recommendation"""
        if current_price < avg_price * 0.95:
            return "Great time to buy - price below average"
        elif current_price > avg_price * 1.05:
            return "Price above average - consider waiting"
        elif trend == 'decreasing':
            return "Price trending down - monitor for better deals"
        elif trend == 'increasing':
            return "Price trending up - consider buying soon"
        elif volatility > 10:
            return "High volatility - price changes frequently"
        else:
            return "Stable pricing - consistent over time"

    def get_competitor_comparison(
        self,
        product_id: int,
        days: int = 7
    ) -> Dict:
        """
        Compare prices across competitors for recent period

        Args:
            product_id: Product to analyze
            days: Number of days to look back (default: 7)

        Returns:
            Comparison data by competitor
        """
        try:
            end_date = utcnow()
            start_date = end_date - timedelta(days=days)

            # Get matches
            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id
            ).all()

            competitors = []
            for match in matches:
                # Get recent price stats
                price_stats = self.db.query(
                    func.avg(PriceHistory.price).label('avg_price'),
                    func.min(PriceHistory.price).label('min_price'),
                    func.max(PriceHistory.price).label('max_price'),
                    func.count(PriceHistory.id).label('count')
                ).filter(
                    and_(
                        PriceHistory.match_id == match.id,
                        PriceHistory.timestamp >= start_date
                    )
                ).first()

                if price_stats and price_stats.avg_price:
                    competitors.append({
                        'competitor_id': match.id,
                        'competitor_name': match.competitor_name,
                        'competitor_url': match.competitor_url,
                        'avg_price': round(float(price_stats.avg_price), 2),
                        'min_price': round(float(price_stats.min_price), 2),
                        'max_price': round(float(price_stats.max_price), 2),
                        'price_checks': price_stats.count
                    })

            # Sort by average price
            competitors.sort(key=lambda x: x['avg_price'])

            # Add rankings
            for i, comp in enumerate(competitors):
                comp['rank'] = i + 1
                comp['is_lowest'] = i == 0
                comp['is_highest'] = i == len(competitors) - 1

            return {
                'success': True,
                'product_id': product_id,
                'period_days': days,
                'competitors': competitors,
                'summary': {
                    'total_competitors': len(competitors),
                    'lowest_price': competitors[0]['avg_price'] if competitors else None,
                    'highest_price': competitors[-1]['avg_price'] if competitors else None,
                    'price_spread': round(
                        competitors[-1]['avg_price'] - competitors[0]['avg_price'], 2
                    ) if competitors else None
                }
            }

        except Exception as e:
            logger.exception(f"Error in competitor comparison: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_price_alerts(
        self,
        product_id: int,
        threshold_pct: float = 5.0
    ) -> Dict:
        """
        Check for significant price changes that should trigger alerts

        Args:
            product_id: Product to check
            threshold_pct: Percentage change threshold (default: 5%)

        Returns:
            Alerts for significant price changes
        """
        try:
            # Get last 24 hours vs previous 24 hours
            now = utcnow()
            yesterday = now - timedelta(days=1)
            day_before = yesterday - timedelta(days=1)

            matches = self.db.query(CompetitorMatch).filter(
                CompetitorMatch.monitored_product_id == product_id
            ).all()

            alerts = []

            for match in matches:
                # Recent price (last 24h)
                recent_price = self.db.query(
                    func.avg(PriceHistory.price).label('avg_price')
                ).filter(
                    and_(
                        PriceHistory.match_id == match.id,
                        PriceHistory.timestamp >= yesterday
                    )
                ).scalar()

                # Previous price (24-48h ago)
                previous_price = self.db.query(
                    func.avg(PriceHistory.price).label('avg_price')
                ).filter(
                    and_(
                        PriceHistory.match_id == match.id,
                        PriceHistory.timestamp >= day_before,
                        PriceHistory.timestamp < yesterday
                    )
                ).scalar()

                if recent_price and previous_price:
                    change = recent_price - previous_price
                    change_pct = (change / previous_price * 100)

                    if abs(change_pct) >= threshold_pct:
                        alerts.append({
                            'competitor_name': match.competitor_name,
                            'previous_price': round(float(previous_price), 2),
                            'current_price': round(float(recent_price), 2),
                            'change': round(float(change), 2),
                            'change_pct': round(float(change_pct), 2),
                            'alert_type': 'price_drop' if change < 0 else 'price_increase',
                            'severity': 'high' if abs(change_pct) > 10 else 'medium'
                        })

            return {
                'success': True,
                'product_id': product_id,
                'alerts_count': len(alerts),
                'alerts': sorted(alerts, key=lambda x: abs(x['change_pct']), reverse=True)
            }

        except Exception as e:
            logger.exception(f"Error checking price alerts: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Example usage
if __name__ == "__main__":
    from database.connection import SessionLocal

    db = SessionLocal()
    analytics = PriceAnalytics(db)

    # Get 30-day trendline for product 1
    result = analytics.get_product_trendline(product_id=1, days=30)

    if result['success']:
        print(f"Daily Trend Points: {len(result['daily_trend'])}")
        print(f"Insights: {result['insights']}")
