"""
Application Configuration
Loads settings from environment variables with validation
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "agentic-honeypot"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # API Server
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Security
    api_key: str = "change-me-in-production"
    secret_key: str = "super-secret-key-change-in-production"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/honeypot"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""
    
    # Gemini API (Cloud LLM)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"
    gemini_max_tokens: int = 4096
    gemini_temperature: float = 0.7
    gemini_timeout: int = 30
    
    # Local LLaMA
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.1:8b"
    local_llm_max_tokens: int = 2048
    local_llm_temperature: float = 0.3
    local_llm_timeout: int = 60
    
    # Honeypot Settings
    max_conversation_turns: int = 50
    max_engagement_duration_minutes: int = 60
    scam_threshold: float = 0.7
    
    # Safety
    enable_kill_switch: bool = True
    auto_stop_on_payment_request: bool = True
    max_daily_engagements: int = 100
    
    # Memory
    short_term_memory_ttl: int = 3600
    long_term_memory_enabled: bool = True
    
    # Logging
    log_format: str = "json"
    log_file: str = "logs/honeypot.log"
    
    # Metrics
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
