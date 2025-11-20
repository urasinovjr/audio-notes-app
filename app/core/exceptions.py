"""
Custom exceptions and error handlers for the application.
"""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger


class AudioNotesException(Exception):
    """Base exception for audio notes app."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NoteNotFoundException(AudioNotesException):
    """Exception raised when note is not found."""

    def __init__(self, note_id: int):
        super().__init__(
            message=f"Note with ID {note_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"note_id": note_id},
        )


class UnauthorizedAccessException(AudioNotesException):
    """Exception raised when user tries to access resource they don't own."""

    def __init__(self, resource: str, resource_id: int):
        super().__init__(
            message=f"Unauthorized access to {resource} {resource_id}",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"resource": resource, "resource_id": resource_id},
        )


class FileUploadException(AudioNotesException):
    """Exception raised during file upload."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class ExternalAPIException(AudioNotesException):
    """Exception raised when external API call fails."""

    def __init__(self, service: str, error: str):
        super().__init__(
            message=f"{service} API error: {error}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service, "error": error},
        )


async def audio_notes_exception_handler(request: Request, exc: AudioNotesException) -> JSONResponse:
    """Handle custom AudioNotes exceptions."""
    logger.error(
        f"AudioNotesException: {exc.message}",
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details, "path": str(request.url.path)},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.exception("Unhandled exception", exc_info=exc, path=request.url.path)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions."""
    logger.warning(
        f"HTTP exception: {exc.detail}", status_code=exc.status_code, path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code, content={"error": exc.detail, "path": str(request.url.path)}
    )
