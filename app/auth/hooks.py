"""
Supertokens hooks for user synchronization.

This module contains hooks that sync Supertokens users with the main application database.
"""

import logging
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)

# Create a separate engine for hooks (to avoid dependency on app lifecycle)
_engine = None
_async_session_maker = None


def _get_async_session_maker() -> async_sessionmaker:
    """Get or create async session maker for database operations."""
    global _engine, _async_session_maker

    if _async_session_maker is None:
        _engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=False,
            pool_pre_ping=True,
        )
        _async_session_maker = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _async_session_maker


async def create_user_in_db(user_id: str, email: str) -> bool:
    """
    Create a user record in the main application database.

    This function is called after successful Supertokens signup to sync
    the user data with the main application's users table.

    Args:
        user_id: The Supertokens user ID (UUID string)
        email: The user's email address

    Returns:
        bool: True if user was created successfully, False otherwise
    """
    try:
        async_session_maker = _get_async_session_maker()

        async with async_session_maker() as session:
            # Use PostgreSQL's INSERT ... ON CONFLICT DO NOTHING
            # to handle race conditions or duplicate signup attempts
            stmt = pg_insert(User).values(
                id=user_id,
                email=email,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ).on_conflict_do_nothing(index_elements=['id'])

            await session.execute(stmt)
            await session.commit()

            logger.info(f"User synced to database: {user_id} ({email})")
            return True

    except Exception as e:
        logger.error(f"Failed to create user in database: {user_id} ({email}). Error: {e}")
        return False


async def update_user_email_in_db(user_id: str, email: str) -> bool:
    """
    Update user email in the main application database.

    This function is called when a user updates their email via Supertokens.

    Args:
        user_id: The Supertokens user ID (UUID string)
        email: The new email address

    Returns:
        bool: True if email was updated successfully, False otherwise
    """
    try:
        async_session_maker = _get_async_session_maker()

        async with async_session_maker() as session:
            # Check if user exists first
            result = await session.get(User, user_id)

            if result:
                result.email = email
                result.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"User email updated in database: {user_id} ({email})")
                return True
            else:
                # User doesn't exist, create them
                logger.warning(f"User not found during email update, creating: {user_id}")
                return await create_user_in_db(user_id, email)

    except Exception as e:
        logger.error(f"Failed to update user email in database: {user_id} ({email}). Error: {e}")
        return False
