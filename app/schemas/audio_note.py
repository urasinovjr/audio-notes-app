"""
Pydantic schemas for AudioNote API.

This module contains request and response schemas for audio note operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AudioNoteCreate(BaseModel):
    """Schema for creating a new audio note."""

    title: str = Field(..., min_length=1, max_length=255, description="Title of the audio note")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags")
    text_notes: Optional[str] = Field(None, description="User's text notes")


class AudioNoteUpdate(BaseModel):
    """Schema for updating an existing audio note."""

    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Title of the audio note")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags")
    text_notes: Optional[str] = Field(None, description="User's text notes")


class AudioNoteResponse(BaseModel):
    """Schema for audio note response."""

    id: int
    user_id: int
    title: str
    tags: Optional[str] = None
    file_path: str
    text_notes: Optional[str] = None
    transcription: Optional[str] = None
    summary: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
