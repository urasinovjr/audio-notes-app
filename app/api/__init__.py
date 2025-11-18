"""
API package.

This package contains all API routes and endpoints.
"""

from fastapi import APIRouter

from app.api.routes import audio_notes

# Create main API router
router = APIRouter()

# Include route modules
router.include_router(
    audio_notes.router,
    prefix="/api",
    tags=["Audio Notes"],
)

__all__ = ["router"]
