"""
Pydantic schemas for AudioNote API.

This module contains request and response schemas for audio note operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AudioNoteCreate(BaseModel):
    """
    Schema for creating a new audio note.

    Used when uploading audio files with initial metadata.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Title of the audio note",
        examples=["Team meeting notes", "Lecture 5: Machine Learning"]
    )
    tags: Optional[str] = Field(
        None,
        max_length=500,
        description="Comma-separated tags for categorization",
        examples=["work,meeting", "education,ml"]
    )
    text_notes: Optional[str] = Field(
        None,
        description="Additional text notes written by user",
        examples=["Important: Review action items before next meeting"]
    )


class AudioNoteUpdate(BaseModel):
    """
    Schema for updating an existing audio note.

    All fields are optional. Only provided fields will be updated.
    """

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Updated title of the audio note",
        examples=["Team meeting notes (updated)"]
    )
    tags: Optional[str] = Field(
        None,
        max_length=500,
        description="Updated comma-separated tags",
        examples=["work,meeting,followup"]
    )
    text_notes: Optional[str] = Field(
        None,
        description="Updated text notes",
        examples=["Action items completed"]
    )


class AudioNoteResponse(BaseModel):
    """
    Schema for audio note response.

    Returned when retrieving audio notes from the API.
    Includes all metadata, transcription, and summary.
    """

    id: int = Field(description="Unique identifier of the note")
    user_id: str = Field(description="ID of the note owner")
    title: str = Field(description="Title of the note")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    file_path: str = Field(description="Path to the audio file in storage")
    text_notes: Optional[str] = Field(None, description="User's manual text notes")
    transcription: Optional[str] = Field(
        None,
        description="AI-generated transcription (null while processing)"
    )
    summary: Optional[str] = Field(
        None,
        description="AI-generated summary (null while processing)"
    )
    status: str = Field(
        description="Processing status: pending, processing, completed, or failed"
    )
    created_at: datetime = Field(description="Timestamp when note was created")
    updated_at: datetime = Field(description="Timestamp when note was last updated")

    class Config:
        from_attributes = True
