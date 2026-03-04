"""
MarketIntel FastAPI Application

This is the main entry point for our backend API.
It handles HTTP requests from the frontend and returns data.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our API routes
from api.routes import products, competitors, integrations, crawler, analytics, scheduler, alerts, ai_matching, auth, billing, insights, filters, repricing, competitor_intel, forecasting, discovery, notifications, events, api_keys, workspaces, activity, promotions, ai, competitor_dna
from api.limiter import limiter, AuthRateLimitMiddleware

# Create the FastAPI application
app = FastAPI(
    title="MarketIntel API",
    description="E-commerce Competitive Intelligence Platform - Monitor ANY competitor website",
    version="1.1.0",
    docs_url="/docs",  # Swagger UI documentation at http://localhost:8000/docs
    redoc_url="/redoc"  # ReDoc documentation at http://localhost:8000/redoc
)

# Attach limiter to app state so route decorators can access it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Global 200 req/hr cap (keyed by user or IP)
app.add_middleware(SlowAPIMiddleware)
# Strict 10 req/min cap on auth endpoints (brute-force protection)
app.add_middleware(AuthRateLimitMiddleware)

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
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["Competitor Websites"])
app.include_router(integrations.router, prefix="/api", tags=["Integrations"])
app.include_router(crawler.router, prefix="/api", tags=["Site Crawler"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(scheduler.router, prefix="/api", tags=["Scheduler & Background Tasks"])
app.include_router(alerts.router, prefix="/api", tags=["Price Alerts & Notifications"])
app.include_router(ai_matching.router, prefix="/api", tags=["AI Product Matching"])
app.include_router(notifications.router, prefix="/api", tags=["Notification Preferences"])
app.include_router(events.router, prefix="/api", tags=["Real-time Events"])
app.include_router(api_keys.router, prefix="/api", tags=["API Keys"])
app.include_router(workspaces.router, prefix="/api", tags=["Workspaces"])
app.include_router(activity.router, prefix="/api", tags=["Activity Log"])
app.include_router(promotions.router, prefix="/api", tags=["Competitor Promotions"])
app.include_router(ai.router, prefix="/api", tags=["AI Intelligence"])
app.include_router(competitor_dna.router, prefix="/api", tags=["Competitor Strategy DNA"])


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
    """Shallow liveness probe — always fast, used by load-balancers."""
    return {"status": "healthy"}


@app.get("/health/deep")
async def deep_health_check():
    """
    Deep readiness probe — tests every external dependency.
    Returns HTTP 200 when all checks pass, 503 when any are degraded.
    Each sub-check has a short timeout so the endpoint never hangs.
    """
    from fastapi.responses import JSONResponse
    from sqlalchemy import text as sql_text
    from database.connection import SessionLocal

    checks: dict = {}

    # Database
    try:
        _db = SessionLocal()
        _db.execute(sql_text("SELECT 1"))
        _db.close()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # Redis
    try:
        import redis as _redis
        _redis_url = (
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}"
            f":{os.getenv('REDIS_PORT', '6379')}"
            f"/{os.getenv('REDIS_DB', '0')}"
        )
        _r = _redis.Redis.from_url(_redis_url, socket_connect_timeout=2)
        _r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # Celery workers
    try:
        from celery_app import celery_app as _celery
        _workers = _celery.control.inspect(timeout=2.0).ping()
        checks["celery"] = "ok" if _workers else "no_workers"
    except Exception as exc:
        checks["celery"] = f"error: {exc}"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={"status": overall, "checks": checks},
    )


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
