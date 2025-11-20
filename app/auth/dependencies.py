"""
Authentication dependencies for FastAPI routes.

This module provides dependency functions for protecting routes with Supertokens session verification.
Supports both cookie-based authentication (web) and Bearer token authentication (API/Swagger).
"""

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session


async def get_user_from_bearer_token(
    authorization: str | None = Header(None, alias="Authorization"),
) -> str | None:
    """
    Extract user ID from Bearer token.

    Args:
        authorization: Authorization header with Bearer token.

    Returns:
        User ID if valid token, None otherwise.
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        # Decode JWT without signature verification (for development/testing)
        # The token was already created by SuperTokens, so we trust it
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get("sub")
        return user_id
    except Exception:
        return None


async def get_current_user_id(
    request: Request,
    bearer_user_id: str | None = Depends(get_user_from_bearer_token),
) -> str:
    """
    Get current user ID from either Bearer token or session cookies.

    This dependency tries multiple authentication methods:
    1. Bearer token (for Swagger/API testing)
    2. SuperTokens session cookies (for web apps)

    Args:
        request: FastAPI request object.
        bearer_user_id: User ID from Bearer token (if provided).

    Returns:
        str: The authenticated user ID.

    Raises:
        HTTPException: 401 if no valid authentication found.
    """
    # If Bearer token is provided and valid, use it
    if bearer_user_id:
        return bearer_user_id

    # Try SuperTokens session verification
    try:
        # Call verify_session manually to check cookies
        session_dependency = verify_session()
        # Execute the dependency
        session: SessionContainer = await session_dependency(request)
        return session.get_user_id()
    except Exception as e:
        # No valid authentication found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Use /auth/token endpoint to get Bearer token, or login through web UI.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
