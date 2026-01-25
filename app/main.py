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
    
    # Initialize connections (database, redis, LLM clients)
    # TODO: Add database connection pool
    # TODO: Add Redis connection
    # TODO: Initialize Gemini client
    # TODO: Initialize Local LLaMA client
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agentic Honeypot")
    # TODO: Close database connections
    # TODO: Close Redis connection
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
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
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
