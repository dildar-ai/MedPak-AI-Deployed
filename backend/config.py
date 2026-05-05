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

    # ── Database ─────────────────────────────────────────────────────────────
    DB_PATH: str = str(BASE_DIR / "database" / "pharmapedia.db")
    HISTORY_DB_PATH: str = str(BASE_DIR / "database" / "history.db")

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    CHROMA_DIR: str = str(BASE_DIR / "database" / "chroma_store")
    CHROMA_COLLECTION: str = "medpak_drugs"

    # ── Embedding model (local, free) ─────────────────────────────────────────
    EMBED_MODEL: str = "all-MiniLM-L6-v2"

    # ── LLM ──────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    # Primary: Qwen3-32B — best Urdu/Roman Urdu/English multilingual model on Groq
    GROQ_MODEL: str = "qwen/qwen3-32b"
    # Fallback: LLaMA 3.3 70B — if Qwen3 is rate-limited
    GROQ_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.3

    # ── Conversation memory ───────────────────────────────────────────────────
    MAX_HISTORY_TURNS: int = 5       # Last N user+assistant pairs sent to LLM

    # ── Uploads / OCR ────────────────────────────────────────────────────────
    MAX_UPLOAD_IMAGE_MB: int = 10
    # EasyOCR: False works on CPU-only machines; set True in .env if you have CUDA.
    OCR_USE_GPU: bool = False

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
