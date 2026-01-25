"""
Rate Limiting Middleware - Per-client rate limiting with abuse detection
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class RateLimitEntry:
    """Tracks request counts for a client"""
    minute_count: int = 0
    hour_count: int = 0
    minute_reset: float = 0.0
    hour_reset: float = 0.0
    abuse_score: float = 0.0
    blocked_until: Optional[float] = None


class RateLimiter:
    """
    Token bucket rate limiter with abuse detection
    
    Features:
    - Per-minute limits
    - Per-hour limits
    - Abuse threshold detection
    - IP-based throttling
    - Automatic blocking of abusers
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        abuse_threshold: int = 5,  # Number of limit hits before blocking
        block_duration_seconds: int = 3600  # 1 hour block
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.abuse_threshold = abuse_threshold
        self.block_duration = block_duration_seconds
        
        # In-memory storage (use Redis in production)
        self._clients: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        
        logger.info(
            "Rate limiter initialized",
            per_minute=requests_per_minute,
            per_hour=requests_per_hour
        )
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get API key first, then fall back to IP
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"key:{api_key[:16]}"
        
        # Get real IP (handle proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    def check_rate_limit(self, request: Request) -> Tuple[bool, Optional[str], Dict]:
        """
        Check if request should be allowed
        
        Returns:
            Tuple of (allowed, error_message, headers)
        """
        client_key = self._get_client_key(request)
        entry = self._clients[client_key]
        now = time.time()
        
        headers = {}
        
        # Check if client is blocked
        if entry.blocked_until and now < entry.blocked_until:
            remaining = int(entry.blocked_until - now)
            return False, f"Client blocked for abuse. Try again in {remaining}s", {
                "X-RateLimit-Blocked": "true",
                "Retry-After": str(remaining)
            }
        elif entry.blocked_until:
            # Block expired, reset
            entry.blocked_until = None
            entry.abuse_score = 0
        
        # Reset minute counter if window expired
        if now > entry.minute_reset:
            entry.minute_count = 0
            entry.minute_reset = now + 60
        
        # Reset hour counter if window expired
        if now > entry.hour_reset:
            entry.hour_count = 0
            entry.hour_reset = now + 3600
        
        # Check minute limit
        if entry.minute_count >= self.requests_per_minute:
            entry.abuse_score += 1
            self._check_abuse(client_key, entry)
            
            remaining = int(entry.minute_reset - now)
            return False, "Rate limit exceeded (per minute)", {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(entry.minute_reset)),
                "Retry-After": str(remaining)
            }
        
        # Check hour limit
        if entry.hour_count >= self.requests_per_hour:
            entry.abuse_score += 2
            self._check_abuse(client_key, entry)
            
            remaining = int(entry.hour_reset - now)
            return False, "Rate limit exceeded (per hour)", {
                "X-RateLimit-Limit": str(self.requests_per_hour),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(entry.hour_reset)),
                "Retry-After": str(remaining)
            }
        
        # Increment counters
        entry.minute_count += 1
        entry.hour_count += 1
        
        # Build response headers
        headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(self.requests_per_minute - entry.minute_count),
            "X-RateLimit-Reset": str(int(entry.minute_reset))
        }
        
        return True, None, headers
    
    def _check_abuse(self, client_key: str, entry: RateLimitEntry):
        """Check if client should be blocked for abuse"""
        if entry.abuse_score >= self.abuse_threshold:
            entry.blocked_until = time.time() + self.block_duration
            logger.warning(
                "Client blocked for rate limit abuse",
                client=client_key,
                abuse_score=entry.abuse_score,
                block_duration=self.block_duration
            )
    
    def get_client_status(self, client_key: str) -> Dict:
        """Get rate limit status for a client"""
        entry = self._clients.get(client_key)
        if not entry:
            return {"status": "no_data"}
        
        now = time.time()
        return {
            "minute_count": entry.minute_count,
            "minute_remaining": max(0, self.requests_per_minute - entry.minute_count),
            "hour_count": entry.hour_count,
            "hour_remaining": max(0, self.requests_per_hour - entry.hour_count),
            "abuse_score": entry.abuse_score,
            "is_blocked": entry.blocked_until is not None and now < entry.blocked_until
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)
        
        allowed, error_msg, headers = self.rate_limiter.check_rate_limit(request)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": error_msg
                    },
                    "data": None
                },
                headers=headers
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter singleton"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=settings.rate_limit_per_minute,
            requests_per_hour=settings.rate_limit_per_hour
        )
    return _rate_limiter
