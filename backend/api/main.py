"""
MarketIntel FastAPI Application

This is the main entry point for our backend API.
It handles HTTP requests from the frontend and returns data.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our API routes
from api.routes import products, competitors, integrations, crawler, analytics, scheduler, alerts, ai_matching, auth, billing, insights, filters, repricing, competitor_intel, forecasting, discovery, notifications, events

# Create the FastAPI application
app = FastAPI(
    title="MarketIntel API",
    description="E-commerce Competitive Intelligence Platform - Monitor ANY competitor website",
    version="1.1.0",
    docs_url="/docs",  # Swagger UI documentation at http://localhost:8000/docs
    redoc_url="/redoc"  # ReDoc documentation at http://localhost:8000/redoc
)

# Configure CORS (allows frontend to make requests to backend)
# CORS = Cross-Origin Resource Sharing
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include our routes
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing & Subscriptions"])
app.include_router(insights.router, prefix="/api", tags=["Insights & Recommendations"])
app.include_router(filters.router, prefix="/api", tags=["Filtering & Search"])
app.include_router(repricing.router, prefix="/api", tags=["Repricing & Bulk Actions"])
app.include_router(competitor_intel.router, prefix="/api", tags=["Competitor Intelligence"])
app.include_router(forecasting.router, prefix="/api", tags=["Forecasting & Analytics"])
app.include_router(discovery.router, prefix="/api", tags=["Auto Discovery"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(competitors.router, prefix="/competitors", tags=["Competitor Websites"])
app.include_router(integrations.router, prefix="/api", tags=["Integrations"])
app.include_router(crawler.router, prefix="/api", tags=["Site Crawler"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(scheduler.router, prefix="/api", tags=["Scheduler & Background Tasks"])
app.include_router(alerts.router, prefix="/api", tags=["Price Alerts & Notifications"])
app.include_router(ai_matching.router, prefix="/api", tags=["AI Product Matching"])
app.include_router(notifications.router, prefix="/api", tags=["Notification Preferences"])
app.include_router(events.router, prefix="/api", tags=["Real-time Events"])


@app.get("/")
def read_root():
    """
    Root endpoint - just a health check.
    Visit http://localhost:8000/ to see this message.
    """
    return {
        "message": "Welcome to MarketIntel API",
        "status": "online",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Used to verify the API is running properly.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    # Run the server
    # This will start the API at http://localhost:8000
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload when code changes
    )
