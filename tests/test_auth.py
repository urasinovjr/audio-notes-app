"""
Tests for authentication functionality.

This module tests:
1. Protected endpoint access control
2. User data isolation
3. Authentication dependencies
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id
from app.db.models import AudioNote, User
from app.main import app


@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Tests for protected endpoints requiring authentication."""

    async def test_get_notes_without_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Test accessing GET /api/notes without authentication."""
        # Clear all dependency overrides to test real auth
        app.dependency_overrides.clear()

        # Override only get_db, not get_current_user_id
        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.get("/api/notes")

        # Should return 401 Unauthorized
        assert response.status_code == 401

    async def test_get_notes_with_invalid_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test accessing protected endpoint with invalid token."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.get(
            "/api/notes", headers={"Authorization": "Bearer invalid.token.here"}
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401

    async def test_create_note_without_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Test creating note without authentication."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.post("/api/notes", json={"title": "Unauthorized Note"})

        assert response.status_code == 401

    async def test_get_note_without_auth(
        self, client: AsyncClient, test_note: AudioNote, db_session: AsyncSession
    ):
        """Test getting specific note without authentication."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.get(f"/api/notes/{test_note.id}")

        assert response.status_code == 401

    async def test_update_note_without_auth(
        self, client: AsyncClient, test_note: AudioNote, db_session: AsyncSession
    ):
        """Test updating note without authentication."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.patch(f"/api/notes/{test_note.id}", json={"title": "Updated Title"})

        assert response.status_code == 401

    async def test_delete_note_without_auth(
        self, client: AsyncClient, test_note: AudioNote, db_session: AsyncSession
    ):
        """Test deleting note without authentication."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.delete(f"/api/notes/{test_note.id}")

        assert response.status_code == 401

    async def test_search_notes_without_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Test searching notes without authentication."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.get("/api/notes?search=test")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUserDataIsolation:
    """Tests for user data isolation - users should only see their own data."""

    async def test_user_can_only_see_own_notes(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that users can only see their own notes."""
        # Create notes for test_user
        note1 = AudioNote(
            user_id=test_user["user_id"],
            title="User's Note 1",
            tags="personal",
            status="pending",
            file_path="user_note1.mp3",
        )
        note2 = AudioNote(
            user_id=test_user["user_id"],
            title="User's Note 2",
            tags="work",
            status="completed",
            file_path="user_note2.mp3",
        )
        db_session.add(note1)
        db_session.add(note2)
        await db_session.commit()

        # Create note for different user
        other_user_id = str(uuid.uuid4())
        other_user = User(id=other_user_id, email="other@example.com")
        db_session.add(other_user)
        await db_session.commit()

        other_note = AudioNote(
            user_id=other_user_id,
            title="Other User's Note",
            tags="private",
            status="pending",
            file_path="other_note.mp3",
        )
        db_session.add(other_note)
        await db_session.commit()

        # Get notes as test_user
        response = await client.get("/api/notes", headers=test_user["headers"])

        assert response.status_code == 200
        data = response.json()

        # Should only see own notes
        assert len(data) == 2
        assert all(n["user_id"] == test_user["user_id"] for n in data)

        # Verify other user's note is not visible
        note_ids = [n["id"] for n in data]
        assert other_note.id not in note_ids

    async def test_user_cannot_access_other_users_note_by_id(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that users cannot access other users' notes by ID."""
        # Create note for different user
        other_user_id = str(uuid.uuid4())
        other_user = User(id=other_user_id, email="other2@example.com")
        db_session.add(other_user)
        await db_session.commit()

        other_note = AudioNote(
            user_id=other_user_id,
            title="Other User's Private Note",
            tags="confidential",
            status="pending",
            file_path="private_note.mp3",
        )
        db_session.add(other_note)
        await db_session.commit()

        # Try to get other user's note as test_user
        response = await client.get(f"/api/notes/{other_note.id}", headers=test_user["headers"])

        # Should return 404 (not found) to avoid leaking information
        # Some implementations might return 403 (forbidden) instead
        assert response.status_code in [404, 403]

    async def test_user_cannot_update_other_users_note(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that users cannot update other users' notes."""
        # Create note for different user
        other_user_id = str(uuid.uuid4())
        other_user = User(id=other_user_id, email="other3@example.com")
        db_session.add(other_user)
        await db_session.commit()

        other_note = AudioNote(
            user_id=other_user_id,
            title="Original Title",
            tags="work",
            status="pending",
            file_path="note.mp3",
        )
        db_session.add(other_note)
        await db_session.commit()
        original_title = other_note.title

        # Try to update other user's note
        response = await client.patch(
            f"/api/notes/{other_note.id}",
            json={"title": "Hacked Title"},
            headers=test_user["headers"],
        )

        # Should fail with 404 or 403
        assert response.status_code in [404, 403]

        # Verify note was not modified
        await db_session.refresh(other_note)
        assert other_note.title == original_title

    async def test_user_cannot_delete_other_users_note(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that users cannot delete other users' notes."""
        # Create note for different user
        other_user_id = str(uuid.uuid4())
        other_user = User(id=other_user_id, email="other4@example.com")
        db_session.add(other_user)
        await db_session.commit()

        other_note = AudioNote(
            user_id=other_user_id,
            title="Important Note",
            tags="critical",
            status="pending",
            file_path="important.mp3",
        )
        db_session.add(other_note)
        await db_session.commit()
        note_id = other_note.id

        # Try to delete other user's note
        response = await client.delete(f"/api/notes/{note_id}", headers=test_user["headers"])

        # Should fail with 404 or 403
        assert response.status_code in [404, 403]

        # Verify note still exists
        from sqlalchemy import select

        result = await db_session.execute(select(AudioNote).where(AudioNote.id == note_id))
        note = result.scalar_one_or_none()
        assert note is not None
        assert note.title == "Important Note"

    async def test_search_only_returns_users_notes(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that search only returns current user's notes."""
        # Create notes for test_user with searchable term
        user_note = AudioNote(
            user_id=test_user["user_id"],
            title="Important Meeting",
            tags="meeting",
            status="pending",
            file_path="meeting1.mp3",
        )
        db_session.add(user_note)
        await db_session.commit()

        # Create note for other user with same searchable term
        other_user_id = str(uuid.uuid4())
        other_user = User(id=other_user_id, email="other5@example.com")
        db_session.add(other_user)
        await db_session.commit()

        other_note = AudioNote(
            user_id=other_user_id,
            title="Important Conference",
            tags="meeting",
            status="pending",
            file_path="meeting2.mp3",
        )
        db_session.add(other_note)
        await db_session.commit()

        # Search for "Important"
        response = await client.get("/api/notes?search=Important", headers=test_user["headers"])

        assert response.status_code == 200
        data = response.json()

        # Should only return user's notes
        assert len(data) == 1
        assert data[0]["user_id"] == test_user["user_id"]
        assert data[0]["id"] == user_note.id


@pytest.mark.asyncio
class TestAuthenticationDependency:
    """Tests for authentication dependency behavior."""

    async def test_authenticated_request_includes_user_id(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that authenticated requests properly identify the user."""
        # Create a note
        response = await client.post(
            "/api/notes",
            json={
                "title": "Test Note",
                "tags": "test",
            },
            headers=test_user["headers"],
        )

        assert response.status_code == 201
        data = response.json()

        # Verify the note belongs to the authenticated user
        assert data["user_id"] == test_user["user_id"]

    async def test_user_can_perform_crud_on_own_notes(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test full CRUD operations on user's own notes."""
        # CREATE
        create_response = await client.post(
            "/api/notes",
            json={
                "title": "CRUD Test Note",
                "tags": "test,crud",
                "text_notes": "Testing CRUD operations",
            },
            headers=test_user["headers"],
        )
        assert create_response.status_code == 201
        note_id = create_response.json()["id"]

        # READ (single)
        get_response = await client.get(f"/api/notes/{note_id}", headers=test_user["headers"])
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "CRUD Test Note"

        # UPDATE
        update_response = await client.patch(
            f"/api/notes/{note_id}",
            json={"title": "Updated CRUD Test"},
            headers=test_user["headers"],
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Updated CRUD Test"

        # DELETE
        delete_response = await client.delete(f"/api/notes/{note_id}", headers=test_user["headers"])
        assert delete_response.status_code == 200

        # Verify deletion
        verify_response = await client.get(f"/api/notes/{note_id}", headers=test_user["headers"])
        assert verify_response.status_code == 404


@pytest.mark.asyncio
class TestMultipleUsers:
    """Tests for multiple users working simultaneously."""

    async def test_multiple_users_isolated_data(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that multiple users have completely isolated data."""
        # Create two different users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        user1 = User(id=user1_id, email="user1@example.com")
        user2 = User(id=user2_id, email="user2@example.com")
        db_session.add(user1)
        db_session.add(user2)

        # Create notes for both users
        note1 = AudioNote(
            user_id=user1_id,
            title="User 1 Note",
            tags="user1",
            status="pending",
            file_path="user1.mp3",
        )
        note2 = AudioNote(
            user_id=user2_id,
            title="User 2 Note",
            tags="user2",
            status="pending",
            file_path="user2.mp3",
        )
        db_session.add(note1)
        db_session.add(note2)
        await db_session.commit()

        # Mock user1 authentication
        async def override_get_current_user_id_user1():
            return user1_id

        app.dependency_overrides[get_current_user_id] = override_get_current_user_id_user1

        # Get notes as user1
        response1 = await client.get("/api/notes")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 1
        assert data1[0]["user_id"] == user1_id
        assert data1[0]["title"] == "User 1 Note"

        # Mock user2 authentication
        async def override_get_current_user_id_user2():
            return user2_id

        app.dependency_overrides[get_current_user_id] = override_get_current_user_id_user2

        # Get notes as user2
        response2 = await client.get("/api/notes")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) == 1
        assert data2[0]["user_id"] == user2_id
        assert data2[0]["title"] == "User 2 Note"

    async def test_users_with_similar_note_titles_isolated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test isolation even when users have notes with identical titles."""
        # Create two users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        user1 = User(id=user1_id, email="alice@example.com")
        user2 = User(id=user2_id, email="bob@example.com")
        db_session.add(user1)
        db_session.add(user2)

        # Both users create notes with same title
        note1 = AudioNote(
            user_id=user1_id,
            title="Meeting Notes",
            tags="work",
            status="pending",
            file_path="alice_meeting.mp3",
        )
        note2 = AudioNote(
            user_id=user2_id,
            title="Meeting Notes",
            tags="work",
            status="pending",
            file_path="bob_meeting.mp3",
        )
        db_session.add(note1)
        db_session.add(note2)
        await db_session.commit()

        # Mock user1 authentication
        async def override_get_current_user_id_user1():
            return user1_id

        app.dependency_overrides[get_current_user_id] = override_get_current_user_id_user1

        # User1 searches for "Meeting"
        response1 = await client.get("/api/notes?search=Meeting")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 1
        assert data1[0]["user_id"] == user1_id
        assert data1[0]["file_path"] == "alice_meeting.mp3"

        # Mock user2 authentication
        async def override_get_current_user_id_user2():
            return user2_id

        app.dependency_overrides[get_current_user_id] = override_get_current_user_id_user2

        # User2 searches for "Meeting"
        response2 = await client.get("/api/notes?search=Meeting")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) == 1
        assert data2[0]["user_id"] == user2_id
        assert data2[0]["file_path"] == "bob_meeting.mp3"


@pytest.mark.asyncio
class TestAuthenticationEdgeCases:
    """Tests for edge cases in authentication."""

    async def test_empty_auth_header(self, client: AsyncClient, db_session: AsyncSession):
        """Test request with empty Authorization header."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.get("/api/notes", headers={"Authorization": ""})

        assert response.status_code == 401

    async def test_malformed_auth_header(self, client: AsyncClient, db_session: AsyncSession):
        """Test request with malformed Authorization header."""
        app.dependency_overrides.clear()

        from app.db.database import get_db

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        response = await client.get("/api/notes", headers={"Authorization": "NotBearer token"})

        assert response.status_code == 401

    async def test_user_id_consistency_across_requests(
        self, client: AsyncClient, test_user: dict, db_session: AsyncSession
    ):
        """Test that user_id remains consistent across multiple requests."""
        # Create multiple notes
        note_ids = []
        for i in range(3):
            response = await client.post(
                "/api/notes",
                json={
                    "title": f"Note {i}",
                    "tags": f"test{i}",
                },
                headers=test_user["headers"],
            )
            assert response.status_code == 201
            note_ids.append(response.json()["id"])

        # Verify all notes belong to the same user
        response = await client.get("/api/notes", headers=test_user["headers"])
        assert response.status_code == 200
        notes = response.json()

        user_ids = [note["user_id"] for note in notes]
        assert len(set(user_ids)) == 1  # All should be the same user_id
        assert user_ids[0] == test_user["user_id"]
