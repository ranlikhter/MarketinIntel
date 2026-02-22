"""
Database Models for MarketIntel

This file defines the structure of our database tables using SQLAlchemy ORM.
Think of this as creating blueprints for our data storage.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
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
    category = Column(String(200), nullable=True)            # Product category/breadcrumb
    variant = Column(String(200), nullable=True)             # Which variant (size/color/model)
    # Match-rate identifiers (used to confirm product identity)
    brand = Column(String(200), nullable=True)               # Brand extracted from competitor page
    description = Column(Text, nullable=True)                # Feature bullets / product description
    mpn = Column(String(100), nullable=True)                 # Manufacturer Part Number
    upc_ean = Column(String(50), nullable=True)              # UPC-12 or EAN-13 barcode

    # Relationships
    monitored_product = relationship("ProductMonitored", back_populates="competitor_matches")
    price_history = relationship("PriceHistory", back_populates="competitor_match", cascade="all, delete-orphan")

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

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="alerts")
    product = relationship("ProductMonitored")

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
        """Check if alert can be triggered (not in cooldown, not in quiet hours)"""
        if not self.enabled:
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
    user = relationship("User")
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
