"""
Health check route.

GET /api/health
"""
from fastapi import APIRouter
from app.schemas.document import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns {"status": "ok"} — used for uptime monitoring and CI checks."""
    return HealthResponse(status="ok")
