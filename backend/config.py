"""
MedPak AI — Application Configuration
Reads settings from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "MedPak AI"
    APP_VERSION: str = "1.0.0"
    # Set DEBUG=false in production .env
    DEBUG: bool = True

    # ── Server ──────────────────────────────────────────────────────────────────
    PORT: int = 8000

    # ── Database ─────────────────────────────────────────────────────────────
    DB_PATH: str = str(BASE_DIR / "database" / "pharmapedia.db")
    PRICES_DB_PATH: str = str(BASE_DIR / "database" / "live_prices.db")
    HISTORY_DB_PATH: str = str(BASE_DIR / "database" / "history.db")
    USERS_DB_PATH: str = str(BASE_DIR / "database" / "users.db")

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    CHROMA_DIR: str = str(BASE_DIR / "database" / "chroma_store")
    CHROMA_COLLECTION: str = "medpak_drugs"

    # ── Embedding model (local, free) ─────────────────────────────────────────
    EMBED_MODEL: str = "all-MiniLM-L6-v2"

    # ── LLM (Groq — OpenAI-compatible API, free tier) ──────────────────────
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    # Primary: GPT-OSS 120B — flagship, strong multilingual
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Fallback: GPT-OSS 20B — faster, cheaper
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-20b"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.2

    # ── Authentication / JWT ───────────────────────────────────────────────────
    # Generate a secret with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440   # 24 hours

    # ── Conversation memory ───────────────────────────────────────────────────
    MAX_HISTORY_TURNS: int = 5       # Last N user+assistant pairs sent to LLM

    # ── Uploads / OCR ────────────────────────────────────────────────────────
    MAX_UPLOAD_IMAGE_MB: int = 10
    # OCR.space API Key (Free tier: 25k requests/month)
    OCR_SPACE_API_KEY: str = "helloworld"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Dev-friendly defaults; set CORS_ORIGINS in .env as JSON, e.g. ["http://localhost:5173"]
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    # Browsers disallow credentials with wildcard origins; main.py disables credentials if "*" is used.
    CORS_ALLOW_CREDENTIALS: bool = True

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
