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

# Import our API routes (we'll create these next)
from api.routes import products

# Create the FastAPI application
app = FastAPI(
    title="MarketIntel API",
    description="E-commerce Competitive Intelligence Platform",
    version="1.0.0",
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
app.include_router(products.router, prefix="/products", tags=["products"])


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
