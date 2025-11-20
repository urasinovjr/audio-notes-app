"""
Audio Notes API endpoints.

This module contains REST API endpoints for managing audio notes.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id
from app.core.exceptions import NoteNotFoundException
from app.core.rate_limit import limiter
from app.db.database import get_db
from app.db.models import AudioNote
from app.schemas.audio_note import (
    AudioNoteCreate,
    AudioNoteResponse,
    AudioNoteUpdate,
)
from app.services.audio_note import AudioNoteService
from app.services.queue import queue_service

# Constants
DEFAULT_SKIP = 0
DEFAULT_LIMIT = 100
MAX_LIMIT = 100

router = APIRouter()


@router.post(
    "/notes",
    response_model=AudioNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new audio note",
    description="Create a new audio note with metadata (file upload via WebSocket)",
)
@limiter.limit("10/minute")
async def create_audio_note(
    request: Request,
    data: AudioNoteCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> AudioNoteResponse:
    """
    Create a new audio note.

    Args:
        data: Audio note creation data
        db: Database session
        user_id: Current authenticated user ID from session

    Returns:
        Created audio note

    Note:
        File will be uploaded via WebSocket after note creation.
    """
    # Placeholder file path until file upload is implemented
    file_path = "placeholder.mp3"

    note = await AudioNoteService.create(
        db=db,
        user_id=user_id,
        data=data,
        file_path=file_path,
    )

    return AudioNoteResponse.model_validate(note)


@router.get(
    "/notes",
    response_model=list[AudioNoteResponse],
    summary="List audio notes",
    description="Get a paginated list of audio notes for the current user with filtering and sorting",
)
@limiter.limit("50/minute")
async def list_audio_notes(
    request: Request,
    skip: int = Query(DEFAULT_SKIP, ge=0, description="Number of records to skip"),
    limit: int = Query(
        DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Maximum number of records to return"
    ),
    status: str | None = Query(
        None, description="Filter by status (pending|processing|completed|failed)"
    ),
    tags: str | None = Query(None, description="Comma-separated tags"),
    date_from: datetime | None = Query(
        None, description="Filter notes created after this date (ISO 8601)"
    ),
    date_to: datetime | None = Query(
        None, description="Filter notes created before this date (ISO 8601)"
    ),
    sort_by: str = Query(
        "created_at", regex="^(created_at|updated_at|title|status)$", description="Sort by field"
    ),
    order: str = Query("desc", regex="^(asc|desc)$"),
    search: str | None = Query(
        None, description="Search in title, text_notes, transcription, summary"
    ),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> list[AudioNoteResponse]:
    """
    Get notes with filters.

    Query parameters:
    - status: Filter by status (pending|processing|completed|failed)
    - tags: Filter by tags (comma-separated)
    - date_from: Filter notes created after this date (ISO 8601: 2025-11-19T00:00:00)
    - date_to: Filter notes created before this date (ISO 8601: 2025-11-19T23:59:59)
    - sort_by: Sort by field (created_at|updated_at|title|status)
    - order: Sort order (asc|desc)
    - skip: Number of items to skip (pagination)
    - limit: Max number of items to return (max 100)
    - search: Search in title, text_notes, transcription, summary (case-insensitive)

    Examples:
    - GET /api/notes?date_from=2025-11-19T00:00:00&date_to=2025-11-19T23:59:59
    - GET /api/notes?date_from=2025-11-01T00:00:00&status=completed
    - GET /api/notes?sort_by=title&order=asc
    - GET /api/notes?sort_by=status&order=desc
    - GET /api/notes?sort_by=updated_at&order=desc
    - GET /api/notes?search=даня
    - GET /api/notes?search=тестовая&status=completed
    - GET /api/notes?search=знакомство&date_from=2025-11-19T00:00:00

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (pagination)
        status: Filter by status (pending, processing, completed, failed)
        tags: Comma-separated list of tags to filter by
        date_from: Filter notes created after this date (ISO 8601)
        date_to: Filter notes created before this date (ISO 8601)
        sort_by: Field to sort by (created_at, updated_at, title, status)
        order: Sort order (asc or desc)
        search: Search term for title, text_notes, transcription, and summary (case-insensitive)
        db: Database session
        user_id: Current authenticated user ID from session

    Returns:
        List of audio notes
    """
    notes = await AudioNoteService.list_by_user(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        status=status,
        tags=tags,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        order=order,
        search=search,
    )

    return [AudioNoteResponse.model_validate(note) for note in notes]


@router.get(
    "/notes/{note_id}",
    response_model=AudioNoteResponse,
    summary="Get audio note by ID",
    description="Retrieve a specific audio note by its ID",
)
@limiter.limit("30/minute")
async def get_audio_note(
    request: Request,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> AudioNoteResponse:
    """
    Get an audio note by ID.

    Args:
        note_id: ID of the audio note
        db: Database session
        user_id: Current authenticated user ID from session

    Returns:
        Audio note details

    Raises:
        HTTPException: 404 if note not found or doesn't belong to user
    """
    note = await AudioNoteService.get_by_id(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    if not note:
        raise NoteNotFoundException(note_id=note_id)

    return AudioNoteResponse.model_validate(note)


@router.patch(
    "/notes/{note_id}",
    response_model=AudioNoteResponse,
    summary="Update audio note",
    description="Update an existing audio note's metadata",
)
@limiter.limit("20/minute")
async def update_audio_note(
    request: Request,
    note_id: int,
    data: AudioNoteUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> AudioNoteResponse:
    """
    Update an audio note.

    Args:
        note_id: ID of the audio note to update
        data: Update data
        db: Database session
        user_id: Current authenticated user ID from session

    Returns:
        Updated audio note

    Raises:
        HTTPException: 404 if note not found or doesn't belong to user
    """
    note = await AudioNoteService.update(
        db=db,
        note_id=note_id,
        user_id=user_id,
        data=data,
    )

    if not note:
        raise NoteNotFoundException(note_id=note_id)

    return AudioNoteResponse.model_validate(note)


@router.delete(
    "/notes/{note_id}",
    summary="Delete audio note",
    description="Delete an audio note permanently",
)
@limiter.limit("20/minute")
async def delete_audio_note(
    request: Request,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Delete an audio note.

    Args:
        note_id: ID of the audio note to delete
        db: Database session
        user_id: Current authenticated user ID from session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if note not found or doesn't belong to user
    """
    deleted = await AudioNoteService.delete(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    if not deleted:
        raise NoteNotFoundException(note_id=note_id)

    return {"message": "Note deleted successfully"}


@router.post(
    "/notes/{note_id}/upload-complete",
    summary="Mark upload as complete",
    description="Mark audio file upload as complete and queue transcription task",
)
@limiter.limit("15/minute")
async def mark_upload_complete(
    request: Request,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Mark upload as complete and queue transcription task.

    After the audio file is uploaded via WebSocket, this endpoint should be called
    to mark the upload as complete and queue the transcription task in RabbitMQ.

    Args:
        note_id: ID of the audio note
        db: Database session
        user_id: Current authenticated user ID from session

    Returns:
        Success message with note ID

    Raises:
        HTTPException: 404 if note not found or doesn't belong to user
    """
    note = await AudioNoteService.get_by_id(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    if not note:
        raise NoteNotFoundException(note_id=note_id)

    # Update file_path in database (replace placeholder with real path)
    real_file_path = f"uploads/user_{user_id}_note_{note_id}.mp3"
    await db.execute(
        update(AudioNote).where(AudioNote.id == note_id).values(file_path=real_file_path)
    )
    await db.commit()

    # Send transcription task to RabbitMQ
    await queue_service.send_task(
        "transcription",
        {
            "note_id": note_id,
            "file_path": real_file_path,
            "user_id": user_id,
        },
    )

    return {
        "message": "Transcription task queued",
        "note_id": note_id,
    }
