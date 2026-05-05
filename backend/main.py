"""
MedPak AI — FastAPI Main Entry Point
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from routers import health, medicine, chat

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for MedPak AI - Conversational Medicine Assistant",
)

# CORS: wildcard + credentials is invalid in browsers; disable credentials for "*".
_origins = list(settings.CORS_ORIGINS)
_allow_credentials = settings.CORS_ALLOW_CREDENTIALS
if any(str(o).strip() == "*" for o in _origins):
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(medicine.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API. Visit /docs for Swagger UI."}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
