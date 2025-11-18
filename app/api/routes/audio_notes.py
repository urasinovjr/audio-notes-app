"""
Audio Notes API endpoints.

This module contains REST API endpoints for managing audio notes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AudioNote
from app.schemas.audio_note import (
    AudioNoteCreate,
    AudioNoteResponse,
    AudioNoteUpdate,
)
from app.services.audio_note import AudioNoteService
from app.services.queue import queue_service

router = APIRouter()

# Temporary user_id placeholder until authentication is implemented
TEMP_USER_ID = 1


@router.post(
    "/notes",
    response_model=AudioNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new audio note",
    description="Create a new audio note with metadata (file upload to be implemented later)",
)
async def create_audio_note(
    data: AudioNoteCreate,
    db: AsyncSession = Depends(get_db),
) -> AudioNoteResponse:
    """
    Create a new audio note.

    Args:
        data: Audio note creation data
        db: Database session

    Returns:
        Created audio note

    Note:
        Currently uses a placeholder file path and user_id.
        File upload and authentication will be added later.
    """
    # Placeholder file path until file upload is implemented
    file_path = "placeholder.mp3"

    note = await AudioNoteService.create(
        db=db,
        user_id=TEMP_USER_ID,
        data=data,
        file_path=file_path,
    )

    return AudioNoteResponse.model_validate(note)


@router.get(
    "/notes",
    response_model=List[AudioNoteResponse],
    summary="List audio notes",
    description="Get a paginated list of audio notes for the current user",
)
async def list_audio_notes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
) -> List[AudioNoteResponse]:
    """
    Get a list of audio notes for the current user.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (pagination)
        db: Database session

    Returns:
        List of audio notes
    """
    notes = await AudioNoteService.list_by_user(
        db=db,
        user_id=TEMP_USER_ID,
        skip=skip,
        limit=limit,
    )

    return [AudioNoteResponse.model_validate(note) for note in notes]


@router.get(
    "/notes/{note_id}",
    response_model=AudioNoteResponse,
    summary="Get audio note by ID",
    description="Retrieve a specific audio note by its ID",
)
async def get_audio_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
) -> AudioNoteResponse:
    """
    Get an audio note by ID.

    Args:
        note_id: ID of the audio note
        db: Database session

    Returns:
        Audio note details

    Raises:
        HTTPException: 404 if note not found
    """
    note = await AudioNoteService.get_by_id(
        db=db,
        note_id=note_id,
        user_id=TEMP_USER_ID,
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio note with ID {note_id} not found",
        )

    return AudioNoteResponse.model_validate(note)


@router.patch(
    "/notes/{note_id}",
    response_model=AudioNoteResponse,
    summary="Update audio note",
    description="Update an existing audio note's metadata",
)
async def update_audio_note(
    note_id: int,
    data: AudioNoteUpdate,
    db: AsyncSession = Depends(get_db),
) -> AudioNoteResponse:
    """
    Update an audio note.

    Args:
        note_id: ID of the audio note to update
        data: Update data
        db: Database session

    Returns:
        Updated audio note

    Raises:
        HTTPException: 404 if note not found
    """
    note = await AudioNoteService.update(
        db=db,
        note_id=note_id,
        user_id=TEMP_USER_ID,
        data=data,
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio note with ID {note_id} not found",
        )

    return AudioNoteResponse.model_validate(note)


@router.delete(
    "/notes/{note_id}",
    summary="Delete audio note",
    description="Delete an audio note permanently",
)
async def delete_audio_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an audio note.

    Args:
        note_id: ID of the audio note to delete
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if note not found
    """
    deleted = await AudioNoteService.delete(
        db=db,
        note_id=note_id,
        user_id=TEMP_USER_ID,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio note with ID {note_id} not found",
        )

    return {"message": "Note deleted successfully"}


@router.post(
    "/notes/{note_id}/upload-complete",
    summary="Mark upload as complete",
    description="Mark audio file upload as complete and queue transcription task",
)
async def mark_upload_complete(
    note_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Mark upload as complete and queue transcription task.

    After the audio file is uploaded via WebSocket, this endpoint should be called
    to mark the upload as complete and queue the transcription task in RabbitMQ.

    Args:
        note_id: ID of the audio note
        db: Database session

    Returns:
        Success message with note ID

    Raises:
        HTTPException: 404 if note not found
    """
    note = await AudioNoteService.get_by_id(
        db=db,
        note_id=note_id,
        user_id=TEMP_USER_ID,
    )

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio note with ID {note_id} not found",
        )

    # Update file_path in database (replace placeholder with real path)
    real_file_path = f"uploads/user_{TEMP_USER_ID}_note_{note_id}.mp3"
    await db.execute(
        update(AudioNote)
        .where(AudioNote.id == note_id)
        .values(file_path=real_file_path)
    )
    await db.commit()

    # Send transcription task to RabbitMQ
    await queue_service.send_task(
        "transcription",
        {
            "note_id": note_id,
            "file_path": real_file_path,
            "user_id": TEMP_USER_ID,
        },
    )

    return {
        "message": "Transcription task queued",
        "note_id": note_id,
    }
