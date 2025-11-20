"""
Pydantic schemas for AudioNote API.

This module contains request and response schemas for audio note operations.
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AudioNoteCreate(BaseModel):
    """
    Schema for creating a new audio note.

    Used when uploading audio files with initial metadata.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Note title (1-200 characters)",
        examples=["Team meeting notes", "Lecture 5: Machine Learning"],
    )
    tags: str | None = Field(
        None,
        max_length=500,
        description="Comma-separated tags (max 500 characters)",
        examples=["work,meeting", "education,ml"],
    )
    text_notes: str | None = Field(
        None,
        max_length=10000,
        description="Text notes (max 10,000 characters)",
        examples=["Important: Review action items before next meeting"],
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        """Validate title is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tags format."""
        if v is None:
            return v

        # Remove extra spaces
        v = v.strip()

        # Check for valid characters (alphanumeric, comma, dash, underscore)
        if not re.match(r"^[a-zA-Z0-9,\-_\s]+$", v):
            raise ValueError(
                "Tags can only contain letters, numbers, commas, dashes, and underscores"
            )

        # Check individual tag length
        tags = [tag.strip() for tag in v.split(",")]
        for tag in tags:
            if len(tag) > 50:
                raise ValueError("Each tag must be 50 characters or less")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "My Audio Note",
                "tags": "work,meeting,important",
                "text_notes": "Discussion about project timeline",
            }
        }


class AudioNoteUpdate(BaseModel):
    """
    Schema for updating an existing audio note.

    All fields are optional. Only provided fields will be updated.
    """

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Updated title of the audio note",
        examples=["Team meeting notes (updated)"],
    )
    tags: str | None = Field(
        None,
        max_length=500,
        description="Updated comma-separated tags",
        examples=["work,meeting,followup"],
    )
    text_notes: str | None = Field(
        None, description="Updated text notes", examples=["Action items completed"]
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
    tags: str | None = Field(None, description="Comma-separated tags")
    file_path: str = Field(description="Path to the audio file in storage")
    text_notes: str | None = Field(None, description="User's manual text notes")
    transcription: str | None = Field(
        None, description="AI-generated transcription (null while processing)"
    )
    summary: str | None = Field(None, description="AI-generated summary (null while processing)")
    status: str = Field(description="Processing status: pending, processing, completed, or failed")
    created_at: datetime = Field(description="Timestamp when note was created")
    updated_at: datetime = Field(description="Timestamp when note was last updated")

    class Config:
        from_attributes = True
