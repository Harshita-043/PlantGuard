"""
PlantGuard AI Backend - FastAPI Application
Main entry point for the backend server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import API routers
from app.api import scans, health
from app.api.v1 import analyze
from app.core.database import create_tables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Initialize resources on startup, cleanup on shutdown.
    """
    logger.info("Starting PlantGuard AI Backend...")
    # Initialize database
    create_tables()
    logger.info("Database tables created/verified")
    # TODO: Initialize ML models, etc.
    yield
    logger.info("Shutting down PlantGuard AI Backend...")


# Create FastAPI application
app = FastAPI(
    title="PlantGuard AI API",
    description="Backend API for PlantGuard AI plant health monitoring application",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(scans.router, prefix="/api", tags=["scans"])
app.include_router(analyze.router, prefix="/api/v1", tags=["analysis"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PlantGuard AI Backend API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)