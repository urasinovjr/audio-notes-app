"""
SQLAlchemy database models.

This module contains all database models for the audio notes application.
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    User model for storing user information.

    Attributes:
        id: User identifier (string to match Supertokens UUID)
        email: User's email address (unique)
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        audio_notes: List of user's audio notes (relationship)
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    audio_notes: Mapped[list["AudioNote"]] = relationship(
        "AudioNote", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class AudioNote(Base):
    """
    AudioNote model for storing audio notes and their metadata.

    Attributes:
        id: Unique note identifier (auto-increment)
        user_id: Foreign key to User (owner of the note)
        title: Note title
        tags: Comma-separated tags for categorization
        file_path: Path to the audio file in storage
        text_notes: User's manual text notes
        transcription: AI-generated transcription from audio
        summary: AI-generated summary of the note
        status: Processing status (pending, processing, completed, failed)
        created_at: Timestamp when note was created
        updated_at: Timestamp when note was last updated
        user: Relationship to User model
    """

    __tablename__ = "audio_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    text_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="audio_notes")

    def __repr__(self) -> str:
        return f"<AudioNote(id={self.id}, title={self.title}, status={self.status})>"
