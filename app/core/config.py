"""
Application configuration settings.

This module defines all application settings loaded from environment variables.
Settings are managed using Pydantic BaseSettings for validation and type safety.
"""

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    """

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
    CORS_ORIGINS: list[str] = Field(
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
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Directory for uploaded audio files",
    )
    MAX_AUDIO_SIZE_MB: int = Field(
        default=50,
        description="Maximum audio file size in megabytes",
    )
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB (for backward compatibility)
    ALLOWED_AUDIO_FORMATS: list[str] = [
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
    GEMINI_MODEL: str = "gemini-pro"  # Stable model (can also use 'gemini-1.5-flash-latest')

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

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("DEEPGRAM_API_KEY", "GEMINI_API_KEY")
    @classmethod
    def validate_api_keys(cls, v, info):
        """Validate that API keys are provided."""
        if not v or v == "your_key_here":
            raise ValueError(f"{info.field_name} is required. Please set it in .env file.")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format."""
        url_str = str(v)
        if not url_str.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL")
        return v


# Create a global settings instance
settings = Settings()
