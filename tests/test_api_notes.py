"""
Tests for audio notes API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCreateNote:
    """Tests for POST /api/notes endpoint."""

    async def test_create_note_success(self, client: AsyncClient, test_user: dict):
        """Test successful note creation."""
        response = await client.post(
            "/api/notes",
            json={
                "title": "My First Note",
                "tags": "work,important",
                "text_notes": "This is my first audio note"
            },
            headers=test_user["headers"]
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My First Note"
        assert data["tags"] == "work,important"
        assert data["text_notes"] == "This is my first audio note"
        assert data["status"] == "pending"
        assert data["user_id"] == test_user["user_id"]
        assert "id" in data
        assert "created_at" in data

    async def test_create_note_minimal(self, client: AsyncClient, test_user: dict):
        """Test note creation with minimal required fields."""
        response = await client.post(
            "/api/notes",
            json={"title": "Minimal Note"},
            headers=test_user["headers"]
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Note"
        assert data["tags"] is None or data["tags"] == ""
        assert data["text_notes"] is None or data["text_notes"] == ""

    async def test_create_note_without_auth(self, client: AsyncClient):
        """Test note creation without authentication fails."""
        response = await client.post(
            "/api/notes",
            json={"title": "Unauthorized Note"}
        )

        assert response.status_code == 401

    async def test_create_note_invalid_title(self, client: AsyncClient, test_user: dict):
        """Test note creation with empty title fails."""
        response = await client.post(
            "/api/notes",
            json={"title": ""},
            headers=test_user["headers"]
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestGetNotes:
    """Tests for GET /api/notes endpoint."""

    async def test_get_notes_empty(self, client: AsyncClient, test_user: dict):
        """Test getting notes when none exist."""
        response = await client.get(
            "/api/notes",
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_notes_with_data(self, client: AsyncClient, test_user: dict, test_note):
        """Test getting notes when they exist."""
        response = await client.get(
            "/api/notes",
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_note.id
        assert data[0]["title"] == test_note.title

    async def test_get_notes_without_auth(self, client: AsyncClient):
        """Test getting notes without authentication fails."""
        response = await client.get("/api/notes")

        assert response.status_code == 401

    async def test_get_notes_pagination(self, client: AsyncClient, test_user: dict, db_session):
        """Test pagination of notes."""
        from app.db.models import AudioNote

        # Create 5 notes
        for i in range(5):
            note = AudioNote(
                user_id=test_user["user_id"],
                title=f"Note {i}",
                tags="test",
                status="pending",
                file_path=f"test{i}.mp3"
            )
            db_session.add(note)
        await db_session.commit()

        # Get first page (limit=2)
        response = await client.get(
            "/api/notes",
            params={"limit": 2, "skip": 0},
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Get second page
        response = await client.get(
            "/api/notes",
            params={"limit": 2, "skip": 2},
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.asyncio
class TestGetNoteById:
    """Tests for GET /api/notes/{note_id} endpoint."""

    async def test_get_note_success(self, client: AsyncClient, test_user: dict, test_note):
        """Test getting specific note by ID."""
        response = await client.get(
            f"/api/notes/{test_note.id}",
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_note.id
        assert data["title"] == test_note.title

    async def test_get_note_not_found(self, client: AsyncClient, test_user: dict):
        """Test getting non-existent note."""
        response = await client.get(
            "/api/notes/99999",
            headers=test_user["headers"]
        )

        assert response.status_code == 404

    async def test_get_note_without_auth(self, client: AsyncClient, db_session):
        """Test getting note without authentication fails."""
        from app.db.models import AudioNote, User

        # Create user and note directly without test_user fixture to avoid auth override
        user = User(id="unauth-user-id", email="unauth@example.com")
        db_session.add(user)
        await db_session.commit()

        note = AudioNote(
            user_id=user.id,
            title="Test Note",
            tags="test",
            status="pending",
            file_path="test.mp3"
        )
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        response = await client.get(f"/api/notes/{note.id}")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateNote:
    """Tests for PATCH /api/notes/{note_id} endpoint."""

    async def test_update_note_success(self, client: AsyncClient, test_user: dict, test_note):
        """Test successful note update."""
        response = await client.patch(
            f"/api/notes/{test_note.id}",
            json={
                "title": "Updated Title",
                "tags": "updated,new",
                "text_notes": "Updated text"
            },
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["tags"] == "updated,new"
        assert data["text_notes"] == "Updated text"

    async def test_update_note_partial(self, client: AsyncClient, test_user: dict, test_note):
        """Test partial note update (only title)."""
        original_tags = test_note.tags

        response = await client.patch(
            f"/api/notes/{test_note.id}",
            json={"title": "New Title Only"},
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title Only"
        # Tags should remain unchanged (partial update)
        assert data["tags"] == original_tags

    async def test_update_note_not_found(self, client: AsyncClient, test_user: dict):
        """Test updating non-existent note."""
        response = await client.patch(
            "/api/notes/99999",
            json={"title": "New Title"},
            headers=test_user["headers"]
        )

        assert response.status_code == 404

    async def test_update_note_without_auth(self, client: AsyncClient, db_session):
        """Test updating note without authentication fails."""
        from app.db.models import AudioNote, User

        # Create user and note directly without test_user fixture to avoid auth override
        user = User(id="unauth-user-id", email="unauth@example.com")
        db_session.add(user)
        await db_session.commit()

        note = AudioNote(
            user_id=user.id,
            title="Test Note",
            tags="test",
            status="pending",
            file_path="test.mp3"
        )
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        response = await client.patch(
            f"/api/notes/{note.id}",
            json={"title": "Unauthorized Update"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeleteNote:
    """Tests for DELETE /api/notes/{note_id} endpoint."""

    async def test_delete_note_success(self, client: AsyncClient, test_user: dict, test_note):
        """Test successful note deletion."""
        response = await client.delete(
            f"/api/notes/{test_note.id}",
            headers=test_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Note deleted successfully"

        # Verify note is deleted
        get_response = await client.get(
            f"/api/notes/{test_note.id}",
            headers=test_user["headers"]
        )
        assert get_response.status_code == 404

    async def test_delete_note_not_found(self, client: AsyncClient, test_user: dict):
        """Test deleting non-existent note."""
        response = await client.delete(
            "/api/notes/99999",
            headers=test_user["headers"]
        )

        assert response.status_code == 404

    async def test_delete_note_without_auth(self, client: AsyncClient, db_session):
        """Test deleting note without authentication fails."""
        from app.db.models import AudioNote, User

        # Create user and note directly without test_user fixture to avoid auth override
        user = User(id="unauth-user-id", email="unauth@example.com")
        db_session.add(user)
        await db_session.commit()

        note = AudioNote(
            user_id=user.id,
            title="Test Note",
            tags="test",
            status="pending",
            file_path="test.mp3"
        )
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)

        response = await client.delete(f"/api/notes/{note.id}")

        assert response.status_code == 401
