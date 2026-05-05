"""
MedPak AI — Health Check Router
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from database.db import get_db_stats

router = APIRouter(prefix="/api/health", tags=["Health"])

@router.get("/")
def health_check():
    """Basic health check and DB stats."""
    try:
        stats = get_db_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )
