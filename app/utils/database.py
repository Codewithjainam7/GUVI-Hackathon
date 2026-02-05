"""
Database Connection - Async SQLAlchemy setup with connection pooling
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import structlog

from app.config import get_settings
from app.schemas.database_models import Base

logger = structlog.get_logger()
settings = get_settings()


class DatabaseManager:
    """
    Manages async database connections with SQLAlchemy
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self, database_url: Optional[str] = None):
        """
        Initialize the database engine and session factory
        
        Args:
            database_url: Override database URL (useful for testing)
        """
        if self._initialized:
            return
        
        url = database_url or settings.database_url
        
        # Render provides 'postgres://' but SQLAlchemy requires 'postgresql://'
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        # Create async engine with connection pooling
        self.engine = create_async_engine(
            url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            echo=settings.debug,
            pool_pre_ping=True,  # Check connection health
        )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        
        self._initialized = True
        logger.info("Database initialized", url=url.split("@")[-1])  # Log without credentials
    
    async def create_tables(self):
        """Create all database tables"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created")
    
    async def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("Database tables dropped")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic cleanup
        
        Usage:
            async with db.session() as session:
                result = await session.execute(query)
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def close(self):
        """Close the database engine"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connection closed")
    
    async def health_check(self) -> bool:
        """Check if database is accessible"""
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """Get or create the database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager


async def init_database():
    """Initialize database and create tables"""
    db = await get_database()
    await db.create_tables()
    return db
