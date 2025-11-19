"""
Authentication dependencies for FastAPI routes.

This module provides dependency functions for protecting routes with Supertokens session verification.
"""

from fastapi import Depends
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session


async def get_current_user_id(session: SessionContainer = Depends(verify_session())) -> str:
    """
    Get the current user ID from the session.

    Args:
        session: The verified session container from Supertokens.

    Returns:
        str: The user ID from the session.
    """
    return session.get_user_id()
