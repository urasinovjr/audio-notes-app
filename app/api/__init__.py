"""
API package.

This package contains all API routes and endpoints.
"""

from fastapi import APIRouter

from app.api.routes import audio_notes, auth_helper

# Create main API router
router = APIRouter()

# Include route modules
router.include_router(
    audio_notes.router,
    prefix="/api",
    tags=["Audio Notes"],
)

# Include auth helper endpoints (for Swagger/API testing)
router.include_router(
    auth_helper.router,
    tags=["Authentication"],
)

__all__ = ["router"]
