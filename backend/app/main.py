"""
FastAPI application factory.

Lifespan:
  - Creates database tables on startup
  - Logs startup/shutdown events

CORS:
  - Configured from settings.CORS_ORIGINS
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import create_tables
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    try:
        await create_tables()
        logger.info("Database tables verified/created.")

        # Seed standard benchmark templates (SRS-S02)
        from app.core.database import AsyncSessionLocal
        from app.repositories.comparison_repo import ComparisonRepository

        async with AsyncSessionLocal() as session:
            comp_repo = ComparisonRepository(session)
            await comp_repo.ensure_seed_templates()
            await session.commit()
        logger.info("Standard benchmark templates verified/seeded.")
    except Exception as exc:
        logger.error("Database initialization failed at startup: %s", exc)
        # Don't crash — let individual requests fail with a clear error
    yield
    logger.info("Shutting down %s", settings.APP_NAME)



# ── App factory ───────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Phase 1 API — document upload, text extraction, and persistence. "
            "AI analysis features are planned for Phase 2."
        ),
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global error handlers ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred."},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "status": "online",
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/api/docs",
            "health": "/api/health",
        }

    app.include_router(api_router)

    return app


app = create_app()
