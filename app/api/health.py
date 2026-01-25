"""
Health Check Endpoint
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for load balancers and monitoring
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "agentic-honeypot",
            "version": "1.0.0"
        }
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness check - verifies all dependencies are available
    """
    # TODO: Check database connection
    # TODO: Check Redis connection
    # TODO: Check Gemini API availability
    # TODO: Check Local LLaMA availability
    
    checks = {
        "database": "ok",  # Placeholder
        "redis": "ok",      # Placeholder
        "gemini": "ok",     # Placeholder
        "local_llm": "ok"   # Placeholder
    }
    
    all_healthy = all(v == "ok" for v in checks.values())
    
    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks
        }
    )
