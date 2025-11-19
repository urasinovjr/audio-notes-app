# WebSocket Upload Test Script

## Description

This script tests the audio file upload functionality via WebSocket for the audio-notes-app backend.

## Features

- ✅ Automatic user signup/signin with SuperTokens
- ✅ REST API note creation
- ✅ WebSocket file upload with chunking (8KB chunks)
- ✅ Real-time progress display
- ✅ Automatic upload completion trigger
- ✅ Wait for worker processing
- ✅ Final status check with transcription and summary
- ✅ Comprehensive error handling
- ✅ Colored console output

## Prerequisites

1. Backend must be running on `http://localhost:8000`
2. Test audio file must exist at `uploads/test_audio_100.mp3`
3. Python 3.8+ installed
4. Required Python packages installed

## Installation

```bash
# Install dependencies
pip install -r test-requirements.txt
```

## Usage

```bash
# Run the test script
python upload_test.py

# Or if made executable:
./upload_test.py
```

## What the script does

1. **Authentication**: Signs up (if needed) and signs in with test credentials
2. **Create Note**: Creates a new audio note via POST `/api/notes`
3. **Upload File**: Uploads the audio file via WebSocket at `/api/notes/{note_id}/upload`
   - Sends file in 8KB chunks
   - Shows progress for each chunk
4. **Mark Complete**: Calls POST `/api/notes/{note_id}/upload-complete` to trigger processing
5. **Wait**: Waits 5 seconds for worker to process
6. **Check Status**: Gets final note status via GET `/api/notes/{note_id}`
7. **Display Results**: Shows transcription and summary (if available)

## Expected Output

```
============================================================
Audio Notes WebSocket Upload Test
============================================================

[HH:MM:SS] ℹ Test file: uploads/test_audio_100.mp3
[HH:MM:SS] ℹ Backend URL: http://localhost:8000
[HH:MM:SS] ℹ Step 1: Authentication
[HH:MM:SS] ✓ User signed up: test@example.com
[HH:MM:SS] ✓ Signed in as: test@example.com
[HH:MM:SS] ℹ Step 2: Creating note
[HH:MM:SS] ✓ Created note with ID: 5
[HH:MM:SS] ℹ Step 3: Uploading file via WebSocket
[HH:MM:SS] ℹ File size: 216.0 KB
[HH:MM:SS] ✓ WebSocket connection established
[HH:MM:SS] ↓ Uploading: 8.0 KB / 216.0 KB (3.7%)
[HH:MM:SS] ↓ Uploading: 16.0 KB / 216.0 KB (7.4%)
...
[HH:MM:SS] ↓ Uploading: 216.0 KB / 216.0 KB (100.0%)
[HH:MM:SS] ✓ File fully uploaded: 216.0 KB
[HH:MM:SS] ✓ Server response: status=completed, filepath=uploads/user_xxx/note_5.mp3
[HH:MM:SS] ✓ WebSocket connection closed
[HH:MM:SS] ℹ Step 4: Marking upload complete
[HH:MM:SS] ✓ Upload marked complete: Transcription task queued
[HH:MM:SS] ℹ Step 5: Waiting for worker processing (5 seconds)...
[HH:MM:SS] ℹ Step 6: Checking final status

📋 Note Details:
  ID: 5
  Title: Test Audio Upload
  Status: completed
  Tags: test,websocket,upload
  Transcription: [Transcribed text will appear here...]
  Summary: [AI-generated summary will appear here...]
  File Path: uploads/user_xxx/note_5.mp3
  Created: 2025-11-19T15:30:00.000000

[HH:MM:SS] ✓ Processing completed successfully!
============================================================
Test completed
============================================================
```

## Configuration

You can modify these constants in the script:

```python
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
TEST_FILE = "uploads/test_audio_100.mp3"
CHUNK_SIZE = 8192  # 8 KB
UPLOAD_TIMEOUT = 30
PROCESSING_WAIT = 5

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
```

## Troubleshooting

### "Test file not found"
- Ensure `uploads/test_audio_100.mp3` exists
- Or change `TEST_FILE` to point to your audio file

### "Authentication failed"
- Check if backend is running: `docker ps`
- Verify SuperTokens is running
- Check backend logs: `docker logs audio-notes-backend`

### "WebSocket upload failed"
- Check WebSocket endpoint implementation
- Verify authentication cookies are being sent
- Check backend logs for errors

### "Processing in progress"
- The workers might be slow or not running
- Wait longer and check again manually: `curl http://localhost:8000/api/notes/{note_id}`
- Check worker logs: `docker logs audio-notes-worker`

## Testing with different files

```python
# Modify TEST_FILE to use a different audio file
TEST_FILE = "path/to/your/audio.mp3"
```

## Notes

- The script creates a new note each time it runs
- Test credentials are hardcoded for convenience
- Cookies are automatically managed by aiohttp
- Progress is shown in real-time during upload
- Worker processing time may vary based on file size
