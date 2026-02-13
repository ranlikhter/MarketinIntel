"""
Database Models for MarketIntel

This file defines the structure of our database tables using SQLAlchemy ORM.
Think of this as creating blueprints for our data storage.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# This creates a base class that all our models will inherit from
Base = declarative_base()


class ProductMonitored(Base):
    """
    Table: products_monitored
    Stores the products that the user wants to track (their own product catalog)
    """
    __tablename__ = "products_monitored"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)  # e.g., "Apple iPhone 13 128GB"
    sku = Column(String(100), nullable=True)      # e.g., "IPHONE13-128" (optional)
    brand = Column(String(100), nullable=True)    # e.g., "Apple"
    image_url = Column(Text, nullable=True)       # URL to product image
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship: One product can have many competitor matches
    competitor_matches = relationship("CompetitorMatch", back_populates="monitored_product", cascade="all, delete-orphan")

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
    competitor_title = Column(String(500), nullable=False)   # How the competitor lists it
    competitor_image_url = Column(Text, nullable=True)       # Competitor's product image

    match_score = Column(Float, default=0.0)                 # 0-100, confidence this is the same product
    last_crawled_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    price = Column(Float, nullable=False)           # e.g., 799.99
    currency = Column(String(10), default="USD")    # e.g., "USD", "EUR"
    in_stock = Column(Boolean, default=True)        # Is the product available?
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    competitor_match = relationship("CompetitorMatch", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(id={self.id}, price={self.price}, timestamp={self.timestamp})>"
