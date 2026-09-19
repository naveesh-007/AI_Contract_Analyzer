"""
Application settings loaded from environment variables.
Never hardcode secrets — copy .env.example to .env and fill in values.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "LexAI Simplifier API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database (PostgreSQL / Supabase) ──────────────────────────────────────
    # Supabase direct connection:
    #   postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    # Or use the direct DB URL from Supabase → Project Settings → Database
    DATABASE_URL: str

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str
    # Service-role key — NEVER sent to the frontend
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",
    ]

    # ── File Upload ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt"}
    ALLOWED_MIME_TYPES: set[str] = {"application/pdf", "text/plain"}

    # ── AI / LLM Service ──────────────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_PROVIDER: str = "openai"  # "openai", "gemini", "mock"
    LLM_BASE_URL: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — reads .env once."""
    return Settings()  # type: ignore[call-arg]
