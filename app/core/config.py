from typing import List

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application settings
    PROJECT_NAME: str = "Audio Notes API"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Database settings
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/audio_notes",
        description="PostgreSQL database URL",
    )

    # RabbitMQ settings
    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )
    RABBITMQ_QUEUE_TRANSCRIPTION: str = "transcription_queue"
    RABBITMQ_QUEUE_SUMMARIZATION: str = "summarization_queue"

    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_AUDIO_FORMATS: List[str] = [
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/m4a",
        "audio/ogg",
        "audio/webm",
    ]

    # SuperTokens settings
    SUPERTOKENS_CONNECTION_URI: str = Field(
        default="http://localhost:3567",
        description="SuperTokens core connection URI",
    )
    SUPERTOKENS_API_KEY: str | None = None
    SUPERTOKENS_APP_NAME: str = "Audio Notes"
    SUPERTOKENS_API_DOMAIN: str = "http://localhost:8000"
    SUPERTOKENS_WEBSITE_DOMAIN: str = "http://localhost:3000"

    # Deepgram API settings
    DEEPGRAM_API_KEY: str = Field(
        default="",
        description="Deepgram API key for audio transcription",
    )

    # Google Gemini API settings
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key for summarization",
    )
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Redis settings (optional, for caching)
    REDIS_URL: str | None = Field(
        default=None,
        description="Redis connection URL for caching",
    )

    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for signing tokens",
    )


# Create a global settings instance
settings = Settings()
