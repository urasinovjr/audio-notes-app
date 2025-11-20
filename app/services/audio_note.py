"""
Audio Note service layer.

This module contains business logic for audio note operations.
"""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AudioNote
from app.schemas.audio_note import AudioNoteCreate, AudioNoteUpdate


class AudioNoteService:
    """Service class for audio note operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
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
        user_id: str,
    ) -> AudioNote | None:
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
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        tags: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
        search: str | None = None,
    ) -> list[AudioNote]:
        """
        Get a list of audio notes for a user with filtering and sorting.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (pending, processing, completed, failed)
            tags: Comma-separated list of tags to filter by
            date_from: Filter notes created after this date (datetime object)
            date_to: Filter notes created before this date (datetime object)
            sort_by: Field to sort by (created_at, updated_at, title, status)
            order: Sort order (asc or desc)
            search: Search term to filter by title, text_notes, transcription, and summary (case-insensitive)

        Returns:
            List of AudioNote instances
        """
        # Base query
        stmt = select(AudioNote).where(AudioNote.user_id == user_id)

        # Apply status filter
        if status:
            stmt = stmt.where(AudioNote.status == status)

        # Apply tags filter
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            for tag in tag_list:
                stmt = stmt.where(AudioNote.tags.ilike(f"%{tag}%"))

        # Apply date filters
        if date_from:
            stmt = stmt.where(AudioNote.created_at >= date_from)

        if date_to:
            stmt = stmt.where(AudioNote.created_at <= date_to)

        # Full-text search (case-insensitive)
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    AudioNote.title.ilike(search_pattern),
                    AudioNote.text_notes.ilike(search_pattern),
                    AudioNote.transcription.ilike(search_pattern),
                    AudioNote.summary.ilike(search_pattern),
                )
            )

        # Apply sorting
        # Define sort column mapping
        sort_column = {
            "created_at": AudioNote.created_at,
            "updated_at": AudioNote.updated_at,
            "title": AudioNote.title,
            "status": AudioNote.status,
        }.get(sort_by, AudioNote.created_at)

        # Apply sort order
        if order.lower() == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        note_id: int,
        user_id: str,
        data: AudioNoteUpdate,
    ) -> AudioNote | None:
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
        user_id: str,
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
