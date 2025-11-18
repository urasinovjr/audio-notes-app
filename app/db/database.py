"""
Database configuration and session management.

This module provides async database engine, session maker, and utility functions
for database connection management.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def init_db_url() -> str:
    """
    Initialize and return the database URL from settings.

    Returns:
        str: Database connection URL
    """
    return str(settings.DATABASE_URL)


# Create async engine with SQLAlchemy 2.0 syntax
engine = create_async_engine(
    init_db_url(),
    echo=settings.DEBUG,
    future=True,
)

# Create async session maker
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    This is used as a FastAPI dependency to provide database sessions
    to route handlers.

    Yields:
        AsyncSession: Database session

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def connect_db() -> None:
    """
    Initialize database connection.

    This function is called on application startup to establish
    the database connection pool.
    """
    # The connection pool is created automatically when the engine is created
    # This function can be used to run any startup tasks if needed
    pass


async def disconnect_db() -> None:
    """
    Close database connection and dispose of the engine.

    This function is called on application shutdown to properly
    close all database connections.
    """
    await engine.dispose()
