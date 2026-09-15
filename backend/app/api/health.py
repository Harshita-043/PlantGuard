"""
Health check API endpoints
"""
from fastapi import APIRouter
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/ping", response_model=HealthResponse)
async def ping():
    """
    Health check endpoint - returns pong message
    """
    return HealthResponse(message="pong")


@router.get("/demo", response_model=HealthResponse)
async def demo():
    """
    Demo endpoint - returns hello message
    """
    return HealthResponse(message="Hello from PlantGuard AI Backend")