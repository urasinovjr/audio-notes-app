"""
WebSocket endpoints for real-time communication.

This module provides WebSocket endpoints for audio file uploads.
"""

import json
import os

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.db.database import async_session
from app.db.models import AudioNote

router = APIRouter()


@router.websocket("/ws/upload")
async def websocket_upload_audio(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for uploading audio files.

    Query parameters:
        note_id: ID of the audio note
        user_id: ID of the user (optional, defaults to 1)

    The client should send audio file data in chunks as binary messages.
    The server will respond with progress updates and a completion message.

    Example client usage:
        ws = new WebSocket('ws://localhost:8000/ws/upload?note_id=1&user_id=1')
        ws.send(audioChunk)  // Send binary data
    """
    await websocket.accept()

    try:
        # Get parameters from query string
        note_id = websocket.query_params.get("note_id")
        user_id = websocket.query_params.get("user_id", "1")

        if not note_id:
            await websocket.send_json({"status": "error", "message": "note_id is required"})
            await websocket.close()
            return

        # Ensure uploads directory exists
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        # Create file path
        file_path = os.path.join(upload_dir, f"user_{user_id}_note_{note_id}.mp3")

        # Track total bytes received
        total_bytes = 0

        # Open file for writing in binary mode
        with open(file_path, "wb") as audio_file:
            while True:
                try:
                    # Receive binary data from client
                    data = await websocket.receive_bytes()

                    if not data:
                        break

                    # Write chunk to file
                    audio_file.write(data)
                    total_bytes += len(data)

                    # Send acknowledgment to client
                    await websocket.send_json(
                        {"status": "received", "bytes": len(data), "total_bytes": total_bytes}
                    )

                except WebSocketDisconnect:
                    # Client disconnected, break the loop
                    break

        # Send completion message
        await websocket.send_json(
            {
                "status": "completed",
                "file_path": file_path,
                "note_id": note_id,
                "total_bytes": total_bytes,
            }
        )

    except Exception as e:
        # Send error message
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        except Exception:
            # If we can't send the error, just pass
            pass

    finally:
        # Close the WebSocket connection
        try:
            await websocket.close()
        except Exception:
            # Connection might already be closed
            pass


@router.websocket("/ws/upload/{note_id}")
async def websocket_upload_audio_with_auth(websocket: WebSocket, note_id: int) -> None:
    """
    WebSocket endpoint for uploading audio files with Bearer token authentication.

    Path parameters:
        note_id: ID of the audio note

    Query parameters:
        token: Bearer JWT token for authentication

    Protocol:
        1. Client connects with token in query params
        2. Server validates token and note ownership
        3. Client sends metadata JSON: {"filename": "...", "size": 123}
        4. Server responds with {"status": "ready"}
        5. Client sends audio data in binary chunks
        6. Client sends completion JSON: {"action": "done"}
        7. Server responds with {"status": "received"/"processing"/"completed"}

    Example:
        ws = new WebSocket('ws://localhost:8000/ws/upload/123?token=eyJ...')
        ws.send(JSON.stringify({filename: "audio.wav", size: 12345}))
        ws.send(audioBinaryData)
        ws.send(JSON.stringify({action: "done"}))
    """
    await websocket.accept()

    try:
        # Get token from query params
        token = websocket.query_params.get("token")

        if not token:
            await websocket.send_json(
                {
                    "status": "error",
                    "message": "Authentication token required. Add ?token=YOUR_TOKEN to WebSocket URL",
                }
            )
            await websocket.close()
            return

        # Decode and validate token
        try:
            secret = "testing-secret-key-for-swagger-auth"
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            user_id = payload.get("sub")

            if not user_id:
                await websocket.send_json(
                    {"status": "error", "message": "Invalid token: missing user ID"}
                )
                await websocket.close()
                return

        except jwt.ExpiredSignatureError:
            await websocket.send_json(
                {
                    "status": "error",
                    "message": "Token expired. Please get a new token from /auth/token",
                }
            )
            await websocket.close()
            return
        except jwt.InvalidTokenError as e:
            await websocket.send_json({"status": "error", "message": f"Invalid token: {str(e)}"})
            await websocket.close()
            return

        # Verify note exists and belongs to user
        async with async_session() as session:
            result = await session.execute(
                select(AudioNote).where(AudioNote.id == note_id, AudioNote.user_id == user_id)
            )
            note = result.scalar_one_or_none()

            if not note:
                await websocket.send_json(
                    {"status": "error", "message": f"Note {note_id} not found or access denied"}
                )
                await websocket.close()
                return

        # Wait for metadata
        metadata_msg = await websocket.receive_text()
        metadata = json.loads(metadata_msg)

        filename = metadata.get("filename", f"audio_{note_id}.wav")

        # Send ready confirmation
        await websocket.send_json(
            {"status": "ready", "note_id": note_id, "message": "Ready to receive audio data"}
        )

        # Prepare file path
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"user_{user_id}_note_{note_id}_{filename}")

        # Receive audio data
        total_bytes = 0

        with open(file_path, "wb") as audio_file:
            while True:
                try:
                    # Try to receive as text first (for JSON messages)
                    try:
                        message = await websocket.receive_text()
                        msg_data = json.loads(message)

                        # Check for completion signal
                        if msg_data.get("action") == "done":
                            break

                    except Exception:
                        # Not a JSON message, receive as binary
                        data = await websocket.receive_bytes()

                        if not data:
                            break

                        audio_file.write(data)
                        total_bytes += len(data)

                except WebSocketDisconnect:
                    break

        # Update note in database
        async with async_session() as session:
            result = await session.execute(select(AudioNote).where(AudioNote.id == note_id))
            note = result.scalar_one_or_none()

            if note:
                note.file_path = file_path
                note.status = "processing"
                await session.commit()

        # Send completion message
        await websocket.send_json(
            {
                "status": "received",
                "file_path": file_path,
                "note_id": note_id,
                "total_bytes": total_bytes,
                "message": f"Audio file uploaded successfully ({total_bytes} bytes)",
            }
        )

    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "message": f"Upload error: {str(e)}"})
        except Exception:
            pass

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
