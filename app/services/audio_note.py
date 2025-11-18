"""
Audio Note service layer.

This module contains business logic for audio note operations.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AudioNote
from app.schemas.audio_note import AudioNoteCreate, AudioNoteUpdate


class AudioNoteService:
    """Service class for audio note operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        data: AudioNoteCreate,
        file_path: str,
    ) -> AudioNote:
        """
        Create a new audio note.

        Args:
            db: Database session
            user_id: ID of the user creating the note
            data: Audio note creation data
            file_path: Path to the uploaded audio file

        Returns:
            Created AudioNote instance
        """
        note = AudioNote(
            user_id=user_id,
            title=data.title,
            tags=data.tags,
            text_notes=data.text_notes,
            file_path=file_path,
            status="pending",
        )

        db.add(note)
        await db.commit()
        await db.refresh(note)

        return note

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        note_id: int,
        user_id: int,
    ) -> Optional[AudioNote]:
        """
        Get an audio note by ID.

        Args:
            db: Database session
            note_id: ID of the note to retrieve
            user_id: ID of the user (for ownership verification)

        Returns:
            AudioNote instance if found and belongs to user, None otherwise
        """
        stmt = select(AudioNote).where(
            AudioNote.id == note_id,
            AudioNote.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AudioNote]:
        """
        Get a list of audio notes for a user with pagination.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AudioNote instances
        """
        stmt = (
            select(AudioNote)
            .where(AudioNote.user_id == user_id)
            .order_by(AudioNote.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        note_id: int,
        user_id: int,
        data: AudioNoteUpdate,
    ) -> Optional[AudioNote]:
        """
        Update an audio note.

        Args:
            db: Database session
            note_id: ID of the note to update
            user_id: ID of the user (for ownership verification)
            data: Update data

        Returns:
            Updated AudioNote instance if found, None otherwise
        """
        # First, get the note
        note = await AudioNoteService.get_by_id(db, note_id, user_id)
        if not note:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(note, field, value)

        await db.commit()
        await db.refresh(note)

        return note

    @staticmethod
    async def delete(
        db: AsyncSession,
        note_id: int,
        user_id: int,
    ) -> bool:
        """
        Delete an audio note.

        Args:
            db: Database session
            note_id: ID of the note to delete
            user_id: ID of the user (for ownership verification)

        Returns:
            True if deleted, False if not found
        """
        note = await AudioNoteService.get_by_id(db, note_id, user_id)
        if not note:
            return False

        await db.delete(note)
        await db.commit()

        return True
