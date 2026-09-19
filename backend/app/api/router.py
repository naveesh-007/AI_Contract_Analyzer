"""
API router — aggregates all route modules under /api prefix.
"""
from fastapi import APIRouter

from app.api.routes import analysis, chat, documents, health

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(analysis.router)
api_router.include_router(chat.router)
