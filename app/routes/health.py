from fastapi import APIRouter
from typing import Dict

health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=Dict[str, str])
def health_check():
    """
    Health check endpoint для Docker и мониторинга.
    """
    return {"status": "healthy", "service": "M5 Forecast API"}
