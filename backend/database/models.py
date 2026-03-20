"""
Database Models for MarketIntel

This file defines the structure of our database tables using SQLAlchemy ORM.
Think of this as creating blueprints for our data storage.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import enum

# This creates a base class that all our models will inherit from
Base = declarative_base()


# Enums for user roles and subscription tiers
class UserRole(enum.Enum):
    """User roles for access control"""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class SubscriptionTier(enum.Enum):
    """Subscription plan tiers"""
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.Enum):
    """Subscription statuses"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"


class ProductMonitored(Base):
    """
    Table: products_monitored
    Stores the products that the user wants to track (their own product catalog)
    """
    __tablename__ = "products_monitored"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Owner of this product
    title = Column(String(500), nullable=False)  # e.g., "Apple iPhone 13 128GB"
    sku = Column(String(100), nullable=True)      # e.g., "IPHONE13-128" (optional)
    brand = Column(String(100), nullable=True)    # e.g., "Apple"
    image_url = Column(Text, nullable=True)       # URL to product image
    my_price = Column(Float, nullable=True)       # User's own selling price for this product
    # Match-rate identifiers (gold standard for exact product matching)
    description = Column(Text, nullable=True)     # Product description / feature bullets
    mpn = Column(String(100), nullable=True)      # Manufacturer Part Number (e.g., "WH1000XM5/B")
    upc_ean = Column(String(50), nullable=True)   # UPC-12 or EAN-13 barcode
    # Extended identifiers — enrich search queries and improve match accuracy
    asin = Column(String(20), nullable=True)          # Known Amazon ASIN (enables direct lookup vs. text search)
    model_number = Column(String(100), nullable=True) # Manufacturer model number when distinct from MPN
    keywords = Column(Text, nullable=True)            # User-curated search terms for competitor discovery
    category = Column(String(200), nullable=True)     # e.g. "Electronics > Headphones" — disambiguates AI matches
    # Margin intelligence
    cost_price = Column(Float, nullable=True)     # User's cost / COGS — enables margin calculation
    # Inventory (synced from connected store)
    inventory_quantity = Column(Integer, nullable=True)  # Units in stock
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="products")
    competitor_matches = relationship("CompetitorMatch", back_populates="monitored_product", cascade="all, delete-orphan")
    my_price_history = relationship("MyPriceHistory", back_populates="product", cascade="all, delete-orphan", order_by="MyPriceHistory.changed_at")

    def __repr__(self):
        return f"<ProductMonitored(id={self.id}, title='{self.title}')>"


class CompetitorMatch(Base):
    """
    Table: competitor_matches
    Links a monitored product to competitor listings (e.g., same product found on Amazon)
    """
    __tablename__ = "competitor_matches"

    id = Column(Integer, primary_key=True, index=True)
    monitored_product_id = Column(Integer, ForeignKey("products_monitored.id"), nullable=False)

    competitor_name = Column(String(100), nullable=False)    # e.g., "Amazon", "Walmart"
    competitor_url = Column(Text, nullable=False)            # Full URL to the product page
    competitor_product_title = Column(String(500), nullable=False)   # How the competitor lists it

    match_score = Column(Float, default=0.0)                 # 0-100, confidence this is the same product
    created_at = Column(DateTime, default=datetime.utcnow)   # When the match was first created
    last_scraped_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Latest price data (for quick access without querying price_history)
    latest_price = Column(Float, nullable=True)              # Most recent price
    stock_status = Column(String(50), nullable=True)         # "In Stock", "Out of Stock", etc.
    image_url = Column(Text, nullable=True)                  # Product image URL
    competitor_website_id = Column(Integer, ForeignKey("competitor_websites.id"), nullable=True)

    # Rich competitor intelligence (populated from scraping)
    external_id = Column(String(100), nullable=True)         # ASIN (Amazon) or platform-specific ID
    rating = Column(Float, nullable=True)                    # Star rating (e.g., 4.5)
    review_count = Column(Integer, nullable=True)            # Number of customer reviews
    is_prime = Column(Boolean, nullable=True)                # Amazon Prime eligible
    fulfillment_type = Column(String(20), nullable=True)     # 'FBA', 'FBM', 'merchant'
    product_condition = Column(String(30), nullable=True)    # 'New', 'Used', 'Refurbished'
    seller_name = Column(String(200), nullable=True)         # Who is selling it
    seller_count = Column(Integer, nullable=True)            # Number of competing sellers (latest)
    category = Column(String(200), nullable=True)            # Product category/breadcrumb
    variant = Column(String(200), nullable=True)             # Which variant (size/color/model)
    # Match-rate identifiers (used to confirm product identity)
    brand = Column(String(200), nullable=True)               # Brand extracted from competitor page
    description = Column(Text, nullable=True)                # Feature bullets / product description
    mpn = Column(String(100), nullable=True)                 # Manufacturer Part Number
    upc_ean = Column(String(50), nullable=True)              # UPC-12 or EAN-13 barcode
    # Match diagnostics — explain how and how confidently the match was made
    match_method = Column(String(20), nullable=True)         # 'upc_exact', 'mpn_exact', 'text_fuzzy', 'ai_semantic'
    ai_match_score = Column(Float, nullable=True)            # AI semantic score 0-100 (separate from simple match_score)
    title_similarity = Column(Float, nullable=True)          # Title-only similarity component 0.0-1.0
    brand_match = Column(Boolean, nullable=True)             # Explicit brand equality flag
    match_explanation = Column(Text, nullable=True)          # Human-readable explanation from AI matcher
    # Tier 1 — Effective pricing (what the buyer actually pays)
    subscribe_save_price = Column(Float, nullable=True)      # Price with Subscribe & Save (recurring)
    coupon_value = Column(Float, nullable=True)              # Clippable coupon savings ($)
    coupon_pct = Column(Float, nullable=True)                # Clippable coupon savings (%)
    effective_price = Column(Float, nullable=True)           # Best one-time price after coupon
    is_lightning_deal = Column(Boolean, nullable=True)       # Active lightning / limited-time deal
    deal_end_time = Column(DateTime, nullable=True)          # When the current deal expires
    stock_quantity = Column(Integer, nullable=True)          # Parsed from "Only X left in stock"
    low_stock_warning = Column(Boolean, nullable=True)       # Amazon is showing a low-stock banner
    # Tier 1 — Market position
    best_seller_rank = Column(Integer, nullable=True)        # BSR (lower = more sales)
    best_seller_rank_category = Column(String(300), nullable=True)  # Category the BSR applies to
    # Tier 2 — Demand & visibility
    units_sold_past_month = Column(Integer, nullable=True)   # "X+ bought in past month"
    badge_amazons_choice = Column(Boolean, nullable=True)    # Amazon's Choice badge present
    badge_best_seller = Column(Boolean, nullable=True)       # Best Seller badge present
    badge_new_release = Column(Boolean, nullable=True)       # #1 New Release badge present
    is_sponsored = Column(Boolean, nullable=True)            # Paid search placement (search results)
    rating_distribution = Column(JSON, nullable=True)        # {5: 72, 4: 15, 3: 6, 2: 4, 1: 3} (%)
    # Tier 3 — Product attributes (semi-static, improve matching & analysis)
    specifications = Column(JSON, nullable=True)             # Full tech spec table {key: value}
    variant_options = Column(JSON, nullable=True)            # {Color: {selected, options}, Size: ...}
    date_first_available = Column(String(50), nullable=True) # "January 1, 2023" — product age

    # ── GAP 1: Seller Identity Intelligence ───────────────────────────────────
    amazon_is_seller = Column(Boolean, nullable=True)             # Is Amazon itself the buy-box seller?
    seller_feedback_count = Column(Integer, nullable=True)        # Seller lifetime feedback volume
    seller_positive_feedback_pct = Column(Float, nullable=True)   # % positive feedback (0-100)
    lowest_new_offer_price = Column(Float, nullable=True)         # Lowest price from "Other sellers"
    number_of_used_offers = Column(Integer, nullable=True)        # Used/refurb offer count

    # ── GAP 2: Listing Quality ─────────────────────────────────────────────────
    image_count = Column(Integer, nullable=True)                  # Number of product images in gallery
    has_video = Column(Boolean, nullable=True)                    # Has product demo/explainer video
    has_aplus_content = Column(Boolean, nullable=True)            # Has A+ / Enhanced Brand Content
    has_brand_story = Column(Boolean, nullable=True)              # Has brand story section
    bullet_point_count = Column(Integer, nullable=True)           # Feature bullet count
    title_char_count = Column(Integer, nullable=True)             # Title length in characters
    questions_count = Column(Integer, nullable=True)              # Customer Q&A question count
    listing_quality_score = Column(Integer, nullable=True)        # Computed 0-100 composite score

    # ── GAP 3: Delivery & Fulfilment Promise ──────────────────────────────────
    delivery_fastest_days = Column(Integer, nullable=True)        # Fastest delivery option (days)
    delivery_standard_days = Column(Integer, nullable=True)       # Standard delivery (days)
    has_same_day = Column(Boolean, nullable=True)                 # Same-day delivery available
    ships_from_location = Column(String(100), nullable=True)      # "Amazon", "Seller", city, etc.
    has_free_returns = Column(Boolean, nullable=True)             # Free return shipping offered
    return_window_days = Column(Integer, nullable=True)           # Return window in days

    # ── GAP 4: Variation Intelligence ─────────────────────────────────────────
    parent_asin = Column(String(20), nullable=True)               # Parent ASIN for variant family
    total_variations = Column(Integer, nullable=True)             # Total variant count in family
    is_best_seller_variation = Column(Boolean, nullable=True)     # Is this the default/popular variant?

    # ── GAP 5: Extended Badges ────────────────────────────────────────────────
    climate_pledge_friendly = Column(Boolean, nullable=True)      # Amazon sustainability badge
    small_business_badge = Column(Boolean, nullable=True)         # Amazon Small Business label

    # Relationships
    monitored_product = relationship("ProductMonitored", back_populates="competitor_matches")
    price_history = relationship("PriceHistory", back_populates="competitor_match", cascade="all, delete-orphan")
    promotions = relationship("CompetitorPromotion", back_populates="competitor_match", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CompetitorMatch(id={self.id}, competitor='{self.competitor_name}', match_score={self.match_score})>"


class PriceHistory(Base):
    """
    Table: price_history
    Stores historical pricing data for each competitor match (time-series data)
    """
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("competitor_matches.id"), nullable=False)

    price = Column(Float, nullable=False)                    # e.g., 799.99
    currency = Column(String(10), default="USD")             # e.g., "USD", "EUR"
    in_stock = Column(Boolean, default=True)                 # Is the product available?
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Rich price snapshot fields
    was_price = Column(Float, nullable=True)                 # Strike-through/original price (detects fake sales)
    discount_pct = Column(Float, nullable=True)              # Active discount percentage (0-100)
    shipping_cost = Column(Float, nullable=True)             # Shipping cost (0 = free shipping)
    total_price = Column(Float, nullable=True)               # price + shipping (true landed cost)
    promotion_label = Column(String(200), nullable=True)     # e.g., "Coupon: 20% off", "Limited time deal"
    seller_name = Column(String(200), nullable=True)         # Who held the buy box at this snapshot
    seller_count = Column(Integer, nullable=True)            # Number of competing sellers at scrape time
    is_buy_box_winner = Column(Boolean, nullable=True)       # Did this seller own the buy box?
    scrape_quality = Column(String(20), nullable=True)       # 'clean', 'partial', 'fallback'
    # Intelligence snapshot (copied from scrape so historical trends are preserved)
    rating = Column(Float, nullable=True)                    # Star rating at this point in time
    review_count = Column(Integer, nullable=True)            # Review count at this point in time
    is_prime = Column(Boolean, nullable=True)                # Prime eligibility at scrape time
    fulfillment_type = Column(String(20), nullable=True)     # 'FBA', 'FBM', 'merchant'
    product_condition = Column(String(30), nullable=True)    # 'New', 'Used', 'Refurbished'
    source = Column(String(20), nullable=True)               # 'playwright' or 'apify' — which scraper produced this
    # Time-series snapshot of volatile pricing & demand fields
    subscribe_save_price = Column(Float, nullable=True)      # S&S price at this point in time
    coupon_value = Column(Float, nullable=True)              # Active coupon $ at scrape time
    coupon_pct = Column(Float, nullable=True)                # Active coupon % at scrape time
    effective_price = Column(Float, nullable=True)           # Best price buyer could pay at this time
    is_lightning_deal = Column(Boolean, nullable=True)       # Was there an active deal?
    deal_end_time = Column(DateTime, nullable=True)          # When did that deal end?
    stock_quantity = Column(Integer, nullable=True)          # "Only X left" at this moment
    units_sold_past_month = Column(Integer, nullable=True)   # Demand velocity at scrape time
    best_seller_rank = Column(Integer, nullable=True)        # BSR at this point in time
    badge_amazons_choice = Column(Boolean, nullable=True)    # Had badge at scrape time
    badge_best_seller = Column(Boolean, nullable=True)       # Had badge at scrape time
    is_sponsored = Column(Boolean, nullable=True)            # Was a paid placement at scrape time
    # Gap fields captured at snapshot time
    amazon_is_seller = Column(Boolean, nullable=True)        # Was Amazon the buy-box holder?
    seller_name_snapshot = Column(String(200), nullable=True)  # Buy-box holder at this moment
    delivery_fastest_days = Column(Integer, nullable=True)   # Fastest delivery at this moment
    has_free_returns = Column(Boolean, nullable=True)        # Free returns at this moment

    # Relationship
    competitor_match = relationship("CompetitorMatch", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(id={self.id}, price={self.price}, timestamp={self.timestamp})>"


class CompetitorWebsite(Base):
    """
    Table: competitor_websites
    Stores custom competitor websites that clients want to monitor.

    This allows users to add their own private competitor websites
    (not just Amazon/eBay). For example: "mycompetitor.com", "rival-store.com"
    """
    __tablename__ = "competitor_websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)           # e.g., "Competitor Store", "Rival Electronics"
    base_url = Column(String(500), nullable=False)       # e.g., "https://www.competitor.com"
    website_type = Column(String(50), default="custom")  # "custom", "amazon", "walmart", etc.

    # CSS Selectors for scraping (user can configure these)
    price_selector = Column(String(500), nullable=True)       # e.g., ".product-price", "#price"
    title_selector = Column(String(500), nullable=True)       # e.g., "h1.product-title"
    stock_selector = Column(String(500), nullable=True)       # e.g., ".availability"
    image_selector = Column(String(500), nullable=True)       # e.g., "img.product-image"

    # Status and metadata
    is_active = Column(Boolean, default=True)            # Can be disabled without deleting
    notes = Column(Text, nullable=True)                  # User notes about this competitor
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CompetitorWebsite(id={self.id}, name='{self.name}', url='{self.base_url}')>"


class PriceAlert(Base):
    """
    Table: price_alerts
    Stores user-defined alert rules for price changes

    Supported Alert Types:
    - price_drop: Price decreased
    - price_increase: Price increased
    - any_change: Any price change
    - out_of_stock: Competitor out of stock
    - price_war: Multiple competitors dropped prices (3+ in 24h)
    - new_competitor: New competitor detected
    - most_expensive: You're most expensive
    - competitor_raised: Competitor increased price (opportunity)
    - back_in_stock: Competitor restocked
    - market_trend: Overall market trending up/down
    """
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Owner of this alert
    product_id = Column(Integer, ForeignKey("products_monitored.id"), nullable=False)

    # Alert configuration
    alert_type = Column(String(50), nullable=False)  # See alert types above
    threshold_pct = Column(Float, nullable=False, default=5.0)  # Trigger when price changes by this %
    threshold_amount = Column(Float, nullable=True)  # Or trigger when price changes by this amount

    # Multi-channel notification settings
    email = Column(String(255), nullable=False)  # Email to send alerts to
    notify_email = Column(Boolean, default=True)  # Send email notifications
    notify_sms = Column(Boolean, default=False)  # Send SMS notifications
    notify_slack = Column(Boolean, default=False)  # Send Slack notifications
    notify_discord = Column(Boolean, default=False)  # Send Discord notifications
    notify_push = Column(Boolean, default=False)  # Send push notifications (PWA)

    # Channel-specific settings
    phone_number = Column(String(20), nullable=True)  # For SMS
    slack_webhook_url = Column(String(500), nullable=True)  # Slack webhook URL
    discord_webhook_url = Column(String(500), nullable=True)  # Discord webhook URL

    # Delivery preferences
    digest_frequency = Column(String(20), default="instant")  # "instant", "daily", "weekly"
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(Integer, nullable=True)  # Hour of day (0-23)
    quiet_hours_end = Column(Integer, nullable=True)  # Hour of day (0-23)

    # Alert status
    enabled = Column(Boolean, default=True)  # Can be disabled without deleting

    # Frequency control
    cooldown_hours = Column(Integer, default=24)  # Don't send duplicate alerts within this period
    last_triggered_at = Column(DateTime, nullable=True)  # When was this alert last sent
    trigger_count = Column(Integer, default=0)  # How many times this alert has fired

    # Snooze — silence an alert temporarily without deleting it
    snoozed_until = Column(DateTime, nullable=True)  # Null = not snoozed

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="alerts")
    product = relationship("ProductMonitored")
    notification_logs = relationship("NotificationLog", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PriceAlert(id={self.id}, product_id={self.product_id}, type='{self.alert_type}', threshold={self.threshold_pct}%)>"

    def is_in_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled:
            return False

        from datetime import datetime
        current_hour = datetime.utcnow().hour

        if self.quiet_hours_start < self.quiet_hours_end:
            # Normal range (e.g., 22:00 to 08:00)
            return self.quiet_hours_start <= current_hour < self.quiet_hours_end
        else:
            # Overnight range (e.g., 22:00 to 08:00 crosses midnight)
            return current_hour >= self.quiet_hours_start or current_hour < self.quiet_hours_end

    def can_trigger(self) -> bool:
        """Check if alert can be triggered (not snoozed, not in cooldown, not in quiet hours)"""
        if not self.enabled:
            return False

        if self.snoozed_until and datetime.utcnow() < self.snoozed_until:
            return False

        if self.is_in_quiet_hours():
            return False

        if self.last_triggered_at and self.cooldown_hours:
            from datetime import datetime, timedelta
            cooldown_end = self.last_triggered_at + timedelta(hours=self.cooldown_hours)
            if datetime.utcnow() < cooldown_end:
                return False

        return True


class User(Base):
    """
    Table: users
    Stores user accounts with authentication and subscription info
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    auth_provider = Column(String(50), nullable=False, default="local")
    auth_provider_subject = Column(String(255), nullable=True, unique=True)
    avatar_url = Column(Text, nullable=True)
    password_login_enabled = Column(Boolean, nullable=False, default=True)

    # Subscription info
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)

    # Usage limits (enforced based on tier)
    products_limit = Column(Integer, default=5)  # FREE: 5, PRO: 50, BUSINESS: 200
    matches_limit = Column(Integer, default=10)  # FREE: 10, PRO: 100, BUSINESS: unlimited
    alerts_limit = Column(Integer, default=1)    # FREE: 1, PRO: 10, BUSINESS: unlimited

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)

    # Trial
    trial_ends_at = Column(DateTime, nullable=True)

    # Notification preferences (JSON blob)
    notification_prefs = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    products = relationship("ProductMonitored", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")
    workspaces_owned = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    saved_views = relationship("SavedView", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    store_connections = relationship("StoreConnection", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tier='{self.subscription_tier.value}')>"


class SavedView(Base):
    """
    Table: saved_views
    Stores user's saved filter combinations for quick access

    Examples:
    - "Problem Products" - Most expensive + high competition
    - "Black Friday Prep" - High opportunity + trending
    - "Quick Wins" - Competitor out of stock
    """
    __tablename__ = "saved_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)  # For team-shared views

    # View details
    name = Column(String(255), nullable=False)  # e.g., "Problem Products"
    description = Column(Text, nullable=True)  # Optional description
    icon = Column(String(50), nullable=True)  # Optional emoji/icon

    # Filter configuration (stored as JSON)
    filters = Column(JSON, nullable=False)  # {"price_position": "most_expensive", "competition_level": "high"}

    # View settings
    is_default = Column(Boolean, default=False)  # Default view on page load
    is_shared = Column(Boolean, default=False)  # Shared with workspace (Business/Enterprise)
    sort_by = Column(String(50), nullable=True)  # "created_at", "title", "opportunity_score"
    sort_order = Column(String(10), default="desc")  # "asc" or "desc"

    # Usage stats
    use_count = Column(Integer, default=0)  # How many times this view was loaded
    last_used_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_views")
    workspace = relationship("Workspace")

    def __repr__(self):
        return f"<SavedView(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class RepricingRule(Base):
    """
    Table: repricing_rules
    Automated pricing rules for products

    Rule Types:
    - match_lowest: Match the lowest competitor price (with optional margin)
    - undercut: Price below lowest competitor by fixed amount/percentage
    - margin_based: Set price based on cost + margin percentage
    - dynamic: Complex rules based on multiple factors (stock, time, competition)
    - map_protected: Never go below Minimum Advertised Price
    """
    __tablename__ = "repricing_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products_monitored.id"), nullable=True)  # Null = applies to all

    # Rule configuration
    rule_type = Column(String(50), nullable=False)  # See types above
    name = Column(String(255), nullable=False)  # User-friendly name
    description = Column(Text, nullable=True)

    # Rule parameters (stored as JSON)
    config = Column(JSON, nullable=False)
    # Examples:
    # match_lowest: {"margin_amount": 0.5, "margin_pct": 0}
    # undercut: {"amount": 1.0, "percentage": 5}
    # margin_based: {"cost": 50, "margin_pct": 40}
    # dynamic: {"rules": [...], "conditions": [...]}

    # Constraints
    min_price = Column(Float, nullable=True)  # Never go below this
    max_price = Column(Float, nullable=True)  # Never go above this
    map_price = Column(Float, nullable=True)  # Minimum Advertised Price

    # Rule settings
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority rules execute first
    auto_apply = Column(Boolean, default=False)  # Auto-apply without approval

    # Approval workflow
    requires_approval = Column(Boolean, default=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Execution tracking
    last_applied_at = Column(DateTime, nullable=True)
    last_suggested_price = Column(Float, nullable=True)
    application_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    product = relationship("ProductMonitored")
    approver = relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<RepricingRule(id={self.id}, name='{self.name}', type='{self.rule_type}', enabled={self.enabled})>"


class Workspace(Base):
    """
    Table: workspaces
    For team collaboration (Business/Enterprise tiers)
    """
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Settings
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="workspaces_owned")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}')>"


class WorkspaceMember(Base):
    """
    Table: workspace_members
    Links users to workspaces with specific roles
    """
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)

    # Status
    is_active = Column(Boolean, default=True)
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")

    def __repr__(self):
        return f"<WorkspaceMember(workspace_id={self.workspace_id}, user_id={self.user_id}, role='{self.role.value}')>"


class MyPriceHistory(Base):
    """
    Table: my_price_history
    Tracks the user's own price changes over time for each product.
    Auto-recorded whenever my_price is updated via the API.
    Enables "did my price change correlate with sales impact?" analysis.
    """
    __tablename__ = "my_price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_monitored.id"), nullable=False, index=True)
    old_price = Column(Float, nullable=True)      # Previous price (null if first record)
    new_price = Column(Float, nullable=False)     # New price being set
    note = Column(String(300), nullable=True)     # Optional reason ("Black Friday", "matched Amazon")
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("ProductMonitored", back_populates="my_price_history")

    def __repr__(self):
        return f"<MyPriceHistory(product_id={self.product_id}, old={self.old_price}, new={self.new_price})>"


class MatchFeedback(Base):
    """
    Table: match_feedback
    Stores user feedback on AI product matching decisions.
    Used to track accuracy and improve matching thresholds over time.
    """
    __tablename__ = "match_feedback"

    id = Column(Integer, primary_key=True, index=True)
    product_title = Column(String(500), nullable=False)
    competitor_title = Column(String(500), nullable=False)
    ai_score = Column(Float, nullable=False)       # Score the AI gave
    user_confirmed = Column(Boolean, nullable=False)  # True = match, False = not a match
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MatchFeedback(id={self.id}, confirmed={self.user_confirmed}, ai_score={self.ai_score})>"


class ApiKey(Base):
    """
    Table: api_keys
    User-generated API keys for external integrations.
    The full key is shown once at creation; only a SHA-256 hash is stored.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)        # e.g., "My Shopify Automation"
    key_prefix = Column(String(12), nullable=False)   # First chars for display (e.g., "mi_a1b2c3")
    key_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 of full key
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"


class StoreConnection(Base):
    """
    Table: store_connections
    Persisted store credentials for Shopify / WooCommerce.
    Enables periodic inventory sync without re-entering credentials.
    """
    __tablename__ = "store_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String(20), nullable=False)      # "shopify" | "woocommerce"
    store_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)       # Shopify access_token / WC consumer_key
    api_secret = Column(String(500), nullable=True)    # WC consumer_secret
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_inventory = Column(Boolean, default=True)     # Include in periodic sync
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="store_connections")

    def __repr__(self):
        return f"<StoreConnection(id={self.id}, platform='{self.platform}', url='{self.store_url}')>"


class ActivityLog(Base):
    """
    Table: activity_logs
    Full audit trail of every user-initiated action across the platform.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # What happened
    action = Column(String(50), nullable=False, index=True)   # e.g. "product.create", "price.update"
    category = Column(String(30), nullable=False, index=True) # "product","price","alert","rule","integration","account","team"

    # What it affected
    entity_type = Column(String(30), nullable=True)   # "product", "match", "alert", "rule", "apikey", "workspace"
    entity_id = Column(Integer, nullable=True, index=True)
    entity_name = Column(String(500), nullable=True)  # Human-readable name for display

    # Human-readable summary
    description = Column(Text, nullable=False)

    # Structured extra data (old/new values, counts, etc.)
    metadata_ = Column("metadata", JSON, nullable=True)

    status = Column(String(10), default="success")    # "success" | "error"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"


class NotificationLog(Base):
    """
    Table: notification_logs
    Records every notification attempt so users can see their alert history and
    so ops can diagnose delivery failures (e.g. invalid SMS numbers, expired
    Slack webhooks) without relying solely on server logs.
    """
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("price_alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    channel = Column(String(20), nullable=False)   # email | sms | slack | discord | push
    status = Column(String(20), nullable=False)    # sent | failed | timeout
    error_message = Column(Text, nullable=True)    # populated on failure
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)

    alert = relationship("PriceAlert", back_populates="notification_logs")
    user = relationship("User", back_populates="notification_logs")

    def __repr__(self):
        return f"<NotificationLog(id={self.id}, channel='{self.channel}', status='{self.status}')>"


class PushSubscription(Base):
    """
    Table: push_subscriptions
    Stores browser Web Push API subscriptions so the backend can send
    push notifications to users' devices even when the tab is closed.
    Each browser/device creates its own row identified by endpoint URL.
    """
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Web Push subscription keys (from browser PushManager.subscribe())
    endpoint = Column(Text, nullable=False, unique=True)   # Push service delivery URL
    p256dh = Column(Text, nullable=False)                  # ECDH public key for payload encryption
    auth = Column(Text, nullable=False)                    # Auth secret for payload encryption

    # Device context
    user_agent = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="push_subscriptions")

    def __repr__(self):
        return f"<PushSubscription(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class CompetitorPromotion(Base):
    """
    Table: competitor_promotions
    Stores structured promotional offers detected on competitor product pages.

    Promotion types:
    - bogo    : Buy One Get One Free
    - bundle  : Buy X Get Y (quantity-based, e.g., "Buy 3 Get 1 Free")
    - pct_off : Percentage discount (e.g., "20% off when you buy 2")
    - free_item : Free item added to order
    - other   : Coupon codes, seasonal sales, etc.
    """
    __tablename__ = "competitor_promotions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("competitor_matches.id"), nullable=False, index=True)

    # Structured promotion data
    promo_type = Column(String(20), nullable=False)         # "bogo", "bundle", "pct_off", "free_item", "other"
    description = Column(String(500), nullable=False)       # Raw human-readable text, e.g. "Buy 2 Get 1 Free"
    buy_qty = Column(Integer, nullable=True)                # Quantity customer must purchase
    get_qty = Column(Integer, nullable=True)                # Quantity customer receives free/discounted
    discount_pct = Column(Float, nullable=True)             # Percentage off (for pct_off type)
    free_item_name = Column(String(200), nullable=True)     # Name of free item (for free_item type)

    # Lifecycle
    first_seen_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)

    competitor_match = relationship("CompetitorMatch", back_populates="promotions")

    def __repr__(self):
        return f"<CompetitorPromotion(id={self.id}, type='{self.promo_type}', desc='{self.description[:40]}')>"


class ReviewSnapshot(Base):
    """
    Table: review_snapshots
    Dedicated time-series table for review count + rating — separate from PriceHistory
    so that review velocity queries don't scan the full price_history table.
    Populated on every scrape alongside the PriceHistory insert.
    """
    __tablename__ = "review_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("competitor_matches.id"), nullable=False, index=True)

    review_count = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    rating_distribution = Column(JSON, nullable=True)    # {5: 72, 4: 15, ...}
    questions_count = Column(Integer, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)

    competitor_match = relationship("CompetitorMatch")

    def __repr__(self):
        return f"<ReviewSnapshot(match_id={self.match_id}, reviews={self.review_count}, at={self.scraped_at})>"


class SellerProfile(Base):
    """
    Table: seller_profiles
    Aggregated intelligence about each unique seller encountered across all matches.
    One row per seller name — updated on every scrape where that seller appears.
    Enables cross-product seller analysis (e.g. which sellers compete on most products).
    """
    __tablename__ = "seller_profiles"

    id = Column(Integer, primary_key=True, index=True)
    seller_name = Column(String(200), nullable=False, unique=True, index=True)

    amazon_is_1p = Column(Boolean, default=False)             # Is this Amazon itself?
    feedback_rating = Column(Float, nullable=True)            # Seller feedback score (0-5 or 0-100)
    feedback_count = Column(Integer, nullable=True)           # Lifetime feedback volume
    positive_feedback_pct = Column(Float, nullable=True)      # % positive feedback
    storefront_url = Column(Text, nullable=True)              # Link to seller storefront

    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SellerProfile(name='{self.seller_name}', 1p={self.amazon_is_1p})>"


class ListingQualitySnapshot(Base):
    """
    Table: listing_quality_snapshots
    Tracks listing content quality metrics over time per competitor match.
    Enables detecting when a competitor upgrades their listing (adds video, A+, images).
    The listing_score (0-100) is a computed composite.
    """
    __tablename__ = "listing_quality_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("competitor_matches.id"), nullable=False, index=True)

    image_count = Column(Integer, nullable=True)
    has_video = Column(Boolean, nullable=True)
    has_aplus_content = Column(Boolean, nullable=True)
    has_brand_story = Column(Boolean, nullable=True)
    bullet_point_count = Column(Integer, nullable=True)
    title_char_count = Column(Integer, nullable=True)
    questions_count = Column(Integer, nullable=True)
    listing_score = Column(Integer, nullable=True)            # 0-100 composite

    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)

    competitor_match = relationship("CompetitorMatch")

    def __repr__(self):
        return f"<ListingQualitySnapshot(match_id={self.match_id}, score={self.listing_score})>"


class KeywordRank(Base):
    """
    Table: keyword_ranks
    Tracks search-result rank positions for user-defined keywords per product.
    Populated by a dedicated keyword-rank scraper task (separate from product scraping).
    One row per (product, keyword, scrape_time) — supports daily rank tracking.
    """
    __tablename__ = "keyword_ranks"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_monitored.id"), nullable=False, index=True)

    keyword = Column(String(300), nullable=False, index=True)
    organic_rank = Column(Integer, nullable=True)             # Position in organic results (1-based)
    sponsored_rank = Column(Integer, nullable=True)           # Position of our sponsored ad (if any)
    total_results = Column(Integer, nullable=True)            # Total results for this keyword

    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("ProductMonitored")

    def __repr__(self):
        return f"<KeywordRank(product_id={self.product_id}, keyword='{self.keyword}', rank={self.organic_rank})>"


# ── Composite indexes ──────────────────────────────────────────────────────────
# Defined here (not inside __table_args__) so they work with SQLAlchemy's
# create_all() on fresh databases.  The same CREATE INDEX statements are also
# in setup.py migrations so existing databases are upgraded automatically.

# competitor_matches — the two hottest query paths
Index("idx_cm_product_url",   CompetitorMatch.monitored_product_id, CompetitorMatch.competitor_url)
Index("idx_cm_product_price", CompetitorMatch.monitored_product_id, CompetitorMatch.latest_price)
Index("idx_cm_last_scraped",  CompetitorMatch.last_scraped_at)

# price_history — every alert and notification check sorts by (match_id, timestamp DESC)
Index("idx_ph_match_time", PriceHistory.match_id, PriceHistory.timestamp)

# review_snapshots — velocity queries always look at recent rows per match
Index("idx_rs_match_time", ReviewSnapshot.match_id, ReviewSnapshot.scraped_at)

# listing_quality_snapshots — trend queries per match
Index("idx_lqs_match_time", ListingQualitySnapshot.match_id, ListingQualitySnapshot.scraped_at)

# keyword_ranks — dashboard queries per product + recent rows
Index("idx_kr_product_keyword_time", KeywordRank.product_id, KeywordRank.keyword, KeywordRank.scraped_at)

# products_monitored — user's product list is the most common list view
Index("idx_pm_user_created", ProductMonitored.user_id, ProductMonitored.created_at)
