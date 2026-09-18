"""
MedPak AI — FastAPI Main Entry Point
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from config import settings
from routers import health, medicine, chat
from auth.router import router as auth_router
from ratelimit import limiter

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for MedPak AI - Conversational Medicine Assistant",
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Global rate limit middleware (100 req/min per IP) ────────────────────────
class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Health checks are exempt (monitoring/uptime probes)
            if request.url.path.startswith("/api/health"):
                return await call_next(request)

            # Simple in-memory sliding window keyed by IP
            allowed = _global_check(limiter.key_func(request))
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                )
        except Exception:
            # Rate limiting must never take the app down
            pass
        return await call_next(request)


# Minimal sliding-window counter for the global limit
from collections import defaultdict, deque
import time as _time

_window: dict[str, deque] = defaultdict(deque)
_WINDOW_SECONDS = 60
_MAX_REQUESTS = 100


def _global_check(key: str) -> bool:
    now = _time.monotonic()
    q = _window[key]
    while q and now - q[0] > _WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _MAX_REQUESTS:
        return False
    q.append(now)
    return True


app.add_middleware(GlobalRateLimitMiddleware)


# ── CORS ──────────────────────────────────────────────────────────────────────
# Restrict to known dev origins; production domains come from CORS_ORIGINS.
origins = list(settings.CORS_ORIGINS) or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "ngrok-skip-browser-warning"],
)

# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(health.router)          # public — health/uptime
app.include_router(auth_router)            # public — register/login (+/me w/ token)
app.include_router(medicine.router)        # protected — requires JWT
app.include_router(chat.router)            # protected — requires JWT


@app.on_event("startup")
async def on_startup():
    """Warm the in-memory price cache from the persistent live_prices DB."""
    from scrapers.price_cache import warm_cache_from_db
    from scrapers.price_scraper import preload_dvago_index
    from auth.users_db import init_users_db
    warm_cache_from_db()
    init_users_db()
    # Warm the Dvago product index in the background — the first live-price
    # request shouldn't wait for the sitemap download (~24k product URLs).
    asyncio.create_task(preload_dvago_index())
    # Build the RAG index in the background if empty (fresh clone or ephemeral
    # container filesystem) — semantic chat works from the first message on.
    asyncio.create_task(asyncio.to_thread(_warm_rag_index))


def _warm_rag_index() -> None:
    """Index all drugs into ChromaDB when the collection is empty."""
    try:
        from rag.vectorstore import get_collection, build_index

        if get_collection().count() == 0:
            print("[RAG] Empty index — building in background...")
            build_index()
    except Exception as e:
        # A missing index only degrades (keyword search still feeds the LLM),
        # so warm-up failures must never block startup.
        print(f"[RAG] Index warm-up failed (chat falls back to keyword search): {e}")


# ── Self-hosted frontend ──────────────────────────────────────────────────
# When the built frontend exists (npm run build → frontend/dist), serve the
# whole app from the API itself: one port, one URL, no CORS — ideal for a
# self-hosted demo tunnelled through ngrok. /api routes stay untouched.
_FRONTEND_DIST = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
)
if os.path.isdir(_FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"message": f"Welcome to {settings.APP_NAME} API. Visit /docs for Swagger UI."}


if __name__ == "__main__":
    # proxy_headers: when self-hosting behind a tunnel (ngrok) the real client
    # IP arrives in X-Forwarded-For — without this every visitor shares the
    # tunnel's localhost identity and one combined rate-limit bucket.
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
