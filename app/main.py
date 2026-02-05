"""
Agentic Honeypot - Main Application Entry Point
FastAPI application with hybrid LLM architecture for scam detection
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.health import router as health_router
from app.api.mock_scammer import router as mock_router
from app.utils.logging import setup_logging
from app.utils.rate_limiter import RateLimitMiddleware, get_rate_limiter
from app.utils.metrics import get_metrics

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events"""
    # Startup
    setup_logging(settings.log_level, settings.log_format)
    logger.info(
        "Starting Agentic Honeypot",
        app_name=settings.app_name,
        environment=settings.app_env,
        debug=settings.debug
    )
    
    # Initialize metrics
    metrics = get_metrics()
    metrics.increment("app.startup")
    
    # Initialize database
    from app.utils.database import init_database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
    
    # Initialize memory manager
    from app.memory.memory_manager import get_memory_manager
    try:
        memory = await get_memory_manager()
        logger.info("Memory manager initialized")
    except Exception as e:
        logger.warning("Memory manager init failed (using fallback)", error=str(e))
    
    # Initialize LLM clients
    from app.llm.gemini_client import get_gemini_client
    gemini = get_gemini_client()
    if await gemini.health_check():
        logger.info("Gemini client healthy")
    else:
        logger.warning("Gemini client not available")
    
    from app.llm.local_llama_client import get_local_llama_client
    llama = get_local_llama_client()
    if await llama.health_check():
        logger.info("Local LLaMA client healthy")
    else:
        logger.warning("Local LLaMA client not available")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agentic Honeypot")
    
    # Close memory connections
    try:
        memory = await get_memory_manager()
        await memory.disconnect()
    except Exception:
        pass
    
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="Agentic Honeypot API",
        description="Autonomous AI Honeypot for Scam Detection & Intelligence Extraction",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Rate Limiting Middleware
    rate_limiter = get_rate_limiter()
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"] + (["*"] if settings.debug else []),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred" if not settings.debug else str(exc)
                },
                "data": None
            }
        )
    
    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(api_router, prefix=settings.api_prefix, tags=["API"])
    app.include_router(mock_router, prefix="/demo", tags=["Demo"])
    
    # Analytics Router
    from app.api.analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
