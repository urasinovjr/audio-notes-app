"""
Pytest configuration and fixtures for audio-notes-app tests.
"""

import asyncio
import io
import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.database import get_db
from app.db.models import AudioNote, User
from app.main import app

# Test database URL (use separate database for tests)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://audiouser:audiopass@localhost:5433/audio_notes_test_db",
)

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

# Create test session maker
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session

    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create HTTP client for testing.
    """

    # Override get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Disable rate limiting for tests
    from app.core.rate_limit import limiter

    limiter.enabled = False

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Re-enable rate limiting after tests
    limiter.enabled = True
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient, db_session: AsyncSession) -> dict:
    """
    Create a test user and return credentials with token.

    Note: This fixture creates a user through the auth API.
    You may need to adjust this based on your Supertokens setup.
    """
    from app.auth.dependencies import get_current_user_id

    email = "test@example.com"
    password = "TestPassword123!@#"
    user_id = "test-user-id-123"

    # For testing purposes, you might want to create a user directly in the database
    # or use Supertokens API to create a test user
    # This is a placeholder - adjust according to your auth flow

    user = User(
        id=user_id,
        email=email,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Override auth dependency for tests
    async def override_get_current_user_id():
        return user_id

    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    return {
        "email": email,
        "password": password,
        "user_id": user.id,
        "headers": {},  # Add auth headers when you have token logic
    }


@pytest_asyncio.fixture
async def test_note(db_session: AsyncSession, test_user: dict) -> AudioNote:
    """
    Create a test note in the database.
    """
    note = AudioNote(
        user_id=test_user["user_id"],
        title="Test Note",
        tags="test,sample",
        text_notes="This is a test note",
        file_path="test.mp3",
        status="pending",
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    return note


@pytest.fixture
def mock_audio_file() -> io.BytesIO:
    """
    Create a mock audio file (minimal valid MP3).

    Returns:
        BytesIO object containing minimal MP3 data
    """
    # Minimal valid MP3 data
    mp3_header = b"ID3\x04\x00\x00\x00\x00\x00\x00"  # ID3v2.4 header
    mp3_data = b"\xff\xfb\x10\x00" * 1000  # MPEG-1 Layer 3 sync word repeated

    audio_bytes = mp3_header + mp3_data
    audio_file = io.BytesIO(audio_bytes)
    audio_file.seek(0)
    return audio_file
