"""
WebSocket endpoints for real-time communication.

This module provides WebSocket endpoints for audio file uploads.
"""

import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings

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
