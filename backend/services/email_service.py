"""
Email Service
Handles sending email notifications for price alerts and digests
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications"""

    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'MarketIntel')

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = to_email

            # Add text part
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_price_alert(
        self,
        to_email: str,
        product_title: str,
        competitor: str,
        old_price: float,
        new_price: float,
        change_pct: float,
        product_url: str
    ) -> bool:
        """
        Send a price alert email

        Args:
            to_email: Recipient email
            product_title: Product name
            competitor: Competitor name
            old_price: Previous price
            new_price: Current price
            change_pct: Percentage change
            product_url: Link to product detail page

        Returns:
            True if sent successfully
        """
        # Determine if price increase or decrease
        is_decrease = new_price < old_price
        change_emoji = '📉' if is_decrease else '📈'
        change_color = '#10b981' if is_decrease else '#ef4444'
        change_text = 'dropped' if is_decrease else 'increased'

        subject = f"{change_emoji} Price Alert: {product_title} {change_text} {abs(change_pct):.1f}%"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e5e7eb;
                    border-top: none;
                }}
                .alert-box {{
                    background: {change_color}15;
                    border-left: 4px solid {change_color};
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .price-comparison {{
                    display: flex;
                    justify-content: space-around;
                    margin: 20px 0;
                    padding: 20px;
                    background: #f9fafb;
                    border-radius: 8px;
                }}
                .price-box {{
                    text-align: center;
                }}
                .price-label {{
                    font-size: 12px;
                    color: #6b7280;
                    text-transform: uppercase;
                    margin-bottom: 5px;
                }}
                .price-value {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #1f2937;
                }}
                .change-badge {{
                    display: inline-block;
                    padding: 8px 16px;
                    background: {change_color};
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 18px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #6b7280;
                    font-size: 12px;
                    border-top: 1px solid #e5e7eb;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">{change_emoji} Price Alert</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Competitor Price Change Detected</p>
            </div>

            <div class="content">
                <div class="alert-box">
                    <h2 style="margin-top: 0; color: {change_color};">{product_title}</h2>
                    <p style="margin: 0; font-size: 16px;">
                        <strong>{competitor}</strong> has {change_text} their price by
                        <span class="change-badge">{abs(change_pct):.1f}%</span>
                    </p>
                </div>

                <div class="price-comparison">
                    <div class="price-box">
                        <div class="price-label">Previous Price</div>
                        <div class="price-value" style="color: #6b7280;">${old_price:.2f}</div>
                    </div>
                    <div class="price-box">
                        <div class="price-label" style="font-size: 20px;">→</div>
                    </div>
                    <div class="price-box">
                        <div class="price-label">New Price</div>
                        <div class="price-value" style="color: {change_color};">${new_price:.2f}</div>
                    </div>
                </div>

                <p style="text-align: center;">
                    <a href="{product_url}" class="button">View Product Details →</a>
                </p>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    {'💡 This is a great opportunity to adjust your pricing strategy!' if is_decrease else '⚠️ Consider reviewing your pricing to stay competitive.'}
                </p>
            </div>

            <div class="footer">
                <p>You're receiving this because you have price alerts enabled in MarketIntel.</p>
                <p>© 2024 MarketIntel - E-commerce Competitive Intelligence</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {change_emoji} PRICE ALERT

        Product: {product_title}
        Competitor: {competitor}

        Previous Price: ${old_price:.2f}
        New Price: ${new_price:.2f}
        Change: {change_pct:+.1f}%

        View details: {product_url}

        --
        MarketIntel - E-commerce Competitive Intelligence
        """

        return self.send_email(to_email, subject, html_content, text_content)

    def send_daily_digest(
        self,
        to_email: str,
        date: str,
        stats: dict,
        top_price_drops: List[dict],
        top_price_increases: List[dict]
    ) -> bool:
        """
        Send daily digest email

        Args:
            to_email: Recipient email
            date: Date of digest
            stats: Overall statistics
            top_price_drops: List of biggest price drops
            top_price_increases: List of biggest price increases

        Returns:
            True if sent successfully
        """
        subject = f"📊 Daily Digest - {date}"

        # Build price drops HTML
        drops_html = ""
        if top_price_drops:
            for item in top_price_drops[:5]:
                drops_html += f"""
                <div style="padding: 10px; background: #f0fdf4; border-radius: 5px; margin: 10px 0;">
                    <strong>{item['product']}</strong> - {item['competitor']}<br>
                    <span style="color: #10b981; font-size: 20px; font-weight: bold;">
                        ${item['new_price']:.2f} <small style="color: #6b7280;">({item['change_pct']:.1f}%)</small>
                    </span>
                </div>
                """
        else:
            drops_html = "<p style='color: #6b7280;'>No significant price drops today.</p>"

        # Build price increases HTML
        increases_html = ""
        if top_price_increases:
            for item in top_price_increases[:5]:
                increases_html += f"""
                <div style="padding: 10px; background: #fef2f2; border-radius: 5px; margin: 10px 0;">
                    <strong>{item['product']}</strong> - {item['competitor']}<br>
                    <span style="color: #ef4444; font-size: 20px; font-weight: bold;">
                        ${item['new_price']:.2f} <small style="color: #6b7280;">(+{item['change_pct']:.1f}%)</small>
                    </span>
                </div>
                """
        else:
            increases_html = "<p style='color: #6b7280;'>No significant price increases today.</p>"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat-box {{
                    text-align: center;
                    padding: 15px;
                    background: #f9fafb;
                    border-radius: 8px;
                }}
                .stat-value {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #667eea;
                }}
                .stat-label {{
                    font-size: 12px;
                    color: #6b7280;
                    text-transform: uppercase;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">📊 Daily Digest</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{date}</p>
            </div>

            <div style="background: white; padding: 30px; border: 1px solid #e5e7eb;">
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{stats.get('products_monitored', 0)}</div>
                        <div class="stat-label">Products</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats.get('price_updates', 0)}</div>
                        <div class="stat-label">Price Updates</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{stats.get('competitors_tracked', 0)}</div>
                        <div class="stat-label">Competitors</div>
                    </div>
                </div>

                <h2 style="color: #10b981;">📉 Top Price Drops</h2>
                {drops_html}

                <h2 style="color: #ef4444; margin-top: 30px;">📈 Top Price Increases</h2>
                {increases_html}

                <div style="margin-top: 30px; padding: 20px; background: #eff6ff; border-radius: 8px;">
                    <p style="margin: 0; color: #1e40af;">
                        💡 <strong>Tip of the Day:</strong> Review your pricing strategy based on these market changes.
                    </p>
                </div>
            </div>

            <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
                <p>© 2024 MarketIntel - E-commerce Competitive Intelligence</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_content)

    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email to new users"""
        subject = "Welcome to MarketIntel! 🎉"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px;
                    border-radius: 10px;
                    text-align: center;
                }}
                .feature {{
                    padding: 15px;
                    margin: 10px 0;
                    background: #f9fafb;
                    border-left: 4px solid #667eea;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Welcome to MarketIntel! 🎉</h1>
                <p>Your competitive intelligence platform is ready</p>
            </div>

            <div style="padding: 30px;">
                <p>Hi {user_name},</p>

                <p>We're excited to have you on board! MarketIntel helps you stay ahead of the competition by automatically tracking competitor prices and market trends.</p>

                <h2>Get Started:</h2>

                <div class="feature">
                    <strong>1. Add Your Products</strong><br>
                    Start by adding products you want to monitor.
                </div>

                <div class="feature">
                    <strong>2. Import from E-commerce</strong><br>
                    Bulk import from WooCommerce, Shopify, or XML.
                </div>

                <div class="feature">
                    <strong>3. Set Up Alerts</strong><br>
                    Get notified when competitor prices change.
                </div>

                <div class="feature">
                    <strong>4. Auto-Crawl Competitors</strong><br>
                    Discover all products from competitor websites automatically.
                </div>

                <p style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:3000" style="display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Go to Dashboard →
                    </a>
                </p>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    Need help? Reply to this email anytime!
                </p>
            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_content)


# Singleton instance
email_service = EmailService()
