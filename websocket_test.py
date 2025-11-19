#!/usr/bin/env python3
"""
Test script for uploading audio files via WebSocket to audio-notes-app backend.

This script:
1. Creates a new note via REST API (with authentication)
2. Uploads audio file via WebSocket in chunks
3. Waits for processing
4. Checks final status with transcription and summary
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import httpx
import websockets

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


# Configuration
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
TEST_FILE = "uploads/test_audio_100.mp3"
CHUNK_SIZE = 8192  # 8 KB
UPLOAD_TIMEOUT = 30
PROCESSING_WAIT = 5

# Test credentials - Generated uniquely for EACH run to avoid conflicts
TIMESTAMP = int(time.time())
EMAIL = f"test_{TIMESTAMP}@example.com"
PASSWORD = "SecureTest123!@#"  # Strong password to meet SuperTokens requirements


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def log_step(emoji: str, message: str, color: str = Colors.END):
    """Print formatted log message."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {emoji} {message}{Colors.END}")


def log_error(message: str):
    """Print error message."""
    log_step("✗", message, Colors.RED)


def log_success(message: str):
    """Print success message."""
    log_step("✓", message, Colors.GREEN)


def log_info(message: str):
    """Print info message."""
    log_step("ℹ", message, Colors.BLUE)


def log_progress(message: str):
    """Print progress message."""
    log_step("↓", message, Colors.YELLOW)


async def signup_user(client: httpx.AsyncClient, email: str, password: str) -> bool:
    """
    Sign up a new user.

    Args:
        client: HTTP client
        email: User email
        password: User password

    Returns:
        True if successful, False otherwise
    """
    try:
        response = await client.post(
            f"{BACKEND_URL}/auth/signup",
            json={
                "formFields": [
                    {"id": "email", "value": email},
                    {"id": "password", "value": password}
                ]
            },
            headers={"Content-Type": "application/json"}
        )

        # Check response status
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "")

            if status == "OK":
                log_success(f"User signed up: {email}")
                return True
            elif status == "EMAIL_ALREADY_EXISTS_ERROR":
                log_info(f"User already exists (EMAIL_ALREADY_EXISTS_ERROR), will skip to signin")
                return True
            elif status == "FIELD_ERROR":
                errors = data.get("formFields", [])
                log_error(f"Signup validation error: {errors}")
                return False
            else:
                log_error(f"Signup failed with status: {status}")
                log_error(f"Full response: {data}")
                return False
        else:
            log_error(f"Signup failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_error(f"Signup error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def signin_user(client: httpx.AsyncClient, email: str, password: str) -> tuple[Optional[str], Optional[str]]:
    """
    Sign in user and get session cookies.

    Args:
        client: HTTP client
        email: User email
        password: User password

    Returns:
        Tuple of (access_token, user_id) if successful, (None, None) otherwise
    """
    try:
        response = await client.post(
            f"{BACKEND_URL}/auth/signin",
            json={
                "formFields": [
                    {"id": "email", "value": email},
                    {"id": "password", "value": password}
                ]
            },
            headers={"Content-Type": "application/json"}
        )

        # ============ FULL RESPONSE DEBUG ============
        print(f"\n{Colors.BOLD}{Colors.YELLOW}{'='*60}")
        print(f"[DEBUG] /auth/signin FULL RESPONSE")
        print(f"{'='*60}{Colors.END}")

        print(f"{Colors.YELLOW}Status: {response.status_code}{Colors.END}")

        # Response body
        try:
            response_data = response.json()
            print(f"{Colors.YELLOW}Body (JSON):{Colors.END}")
            import json as json_lib
            print(f"{Colors.YELLOW}{json_lib.dumps(response_data, indent=2)}{Colors.END}")

            # Check for session/token fields in body
            if "session" in response_data:
                print(f"{Colors.GREEN}[DEBUG] ✓ Session found in body: {str(response_data['session'])[:100]}...{Colors.END}")
            if "accessToken" in response_data:
                print(f"{Colors.GREEN}[DEBUG] ✓ Access token in body: {str(response_data['accessToken'])[:50]}...{Colors.END}")
            if "token" in response_data:
                print(f"{Colors.GREEN}[DEBUG] ✓ Token in body: {str(response_data['token'])[:50]}...{Colors.END}")
            if "user" in response_data:
                print(f"{Colors.GREEN}[DEBUG] ✓ User info in body: {response_data['user']}{Colors.END}")
        except:
            print(f"{Colors.YELLOW}Body (raw): {response.text}{Colors.END}")

        # Response headers
        print(f"\n{Colors.YELLOW}Response Headers:{Colors.END}")
        for header_name, header_value in response.headers.items():
            if 'cookie' in header_name.lower() or 'token' in header_name.lower():
                print(f"  {Colors.GREEN}{header_name}: {header_value}{Colors.END}")
            else:
                print(f"  {Colors.YELLOW}{header_name}: {header_value}{Colors.END}")

        # Set-Cookie header specifically
        set_cookie_header = response.headers.get('set-cookie')
        if set_cookie_header:
            print(f"\n{Colors.GREEN}[DEBUG] ✓ Set-Cookie header found:{Colors.END}")
            print(f"{Colors.GREEN}  {set_cookie_header}{Colors.END}")
        else:
            print(f"\n{Colors.RED}[DEBUG] ✗ No Set-Cookie header in response{Colors.END}")

        # Cookies from response.cookies
        print(f"\n{Colors.YELLOW}Cookies from response.cookies:{Colors.END}")
        if response.cookies:
            for cookie_name, cookie_value in response.cookies.items():
                print(f"  {Colors.GREEN}{cookie_name} = {cookie_value[:50]}...{Colors.END}")
        else:
            print(f"  {Colors.RED}(empty - no cookies in response.cookies){Colors.END}")

        # Cookies in client jar
        print(f"\n{Colors.YELLOW}Cookies in client.cookies.jar after signin:{Colors.END}")
        if client.cookies.jar:
            for cookie in client.cookies.jar:
                print(f"  {Colors.GREEN}Name: {cookie.name}{Colors.END}")
                print(f"  {Colors.GREEN}Value: {cookie.value[:50]}...{Colors.END}")
                print(f"  {Colors.GREEN}Domain: {cookie.domain}, Path: {cookie.path}, Secure: {cookie.secure}{Colors.END}")
                print(f"  {Colors.YELLOW}---{Colors.END}")
        else:
            print(f"  {Colors.RED}(empty - jar size = 0){Colors.END}")

        print(f"{Colors.YELLOW}Total cookies in jar: {len(client.cookies.jar)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.YELLOW}{'='*60}{Colors.END}\n")
        # ============ END FULL RESPONSE DEBUG ============

        if response.status_code == 200:
            # Check status in response body
            try:
                data = response.json()
                status = data.get("status", "")

                if status == "WRONG_CREDENTIALS_ERROR":
                    print(f"\n{Colors.RED}{'='*60}")
                    print(f"[ERROR] Sign in failed: WRONG_CREDENTIALS_ERROR")
                    print(f"{'='*60}{Colors.END}")
                    print(f"{Colors.RED}Email: {email}{Colors.END}")
                    print(f"{Colors.RED}This should NOT happen with unique email strategy!{Colors.END}")
                    print(f"\n{Colors.YELLOW}Причины:{Colors.END}")
                    print(f"  1. Пароль неправильный (не должно быть при уникальном email)")
                    print(f"  2. Пользователь не существует (signup не выполнился)")
                    print(f"  3. Баг в коде: пароли в signup и signin не совпадают")
                    print()
                    log_error(f"Authentication failed with WRONG_CREDENTIALS_ERROR")
                    sys.exit(1)

                if status == "FIELD_ERROR":
                    errors = data.get("formFields", [])
                    log_error(f"Signin validation error: {errors}")
                    sys.exit(1)

                if status != "OK":
                    log_error(f"Signin failed with status: {status}")
                    log_error(f"Full response: {data}")
                    sys.exit(1)

                # Status is OK - successful signin
                log_success(f"Signed in successfully: {email}")

                # ============ EXTRACT USER_ID FROM RESPONSE ============
                user_id = None
                if "user" in data:
                    user_id = data["user"].get("id")
                    if user_id:
                        log_success(f"User ID extracted: {user_id}")
                    else:
                        log_error("User ID not found in response")
                else:
                    log_error("User object not found in response")

                # ============ EXTRACT TOKEN FROM HEADERS (header-based auth) ============
                print(f"\n{Colors.YELLOW}[DEBUG] Extracting authentication token:{Colors.END}")

                # SuperTokens uses header-based authentication
                access_token = response.headers.get("st-access-token")
                refresh_token = response.headers.get("st-refresh-token")

                if access_token:
                    print(f"  {Colors.GREEN}✓ Access token found in headers:{Colors.END}")
                    print(f"    {Colors.GREEN}st-access-token: {access_token[:50]}...{Colors.END}")
                    if refresh_token:
                        print(f"    {Colors.GREEN}st-refresh-token: {refresh_token[:50]}...{Colors.END}")
                    print(f"  {Colors.GREEN}[INFO] Will use header-based authentication (Authorization: Bearer){Colors.END}")
                    return access_token, user_id
                else:
                    # Fallback: check cookies
                    print(f"  {Colors.YELLOW}[WARNING] No st-access-token in headers{Colors.END}")
                    print(f"  {Colors.YELLOW}[DEBUG] Checking cookies...{Colors.END}")
                    cookies_dict = dict(response.cookies)
                    print(f"    Cookies in response: {list(cookies_dict.keys())}")

                    # Fallback: check response body
                    if "session" in data:
                        session_data = data["session"]
                        access_token = session_data.get("accessToken")
                        if access_token:
                            print(f"  {Colors.GREEN}✓ Access token found in response body{Colors.END}")
                            print(f"    {Colors.GREEN}Token: {access_token[:50]}...{Colors.END}")
                            return access_token, user_id

                    print(f"  {Colors.RED}[ERROR] No access token found in headers, cookies, or body!{Colors.END}")
                    sys.exit(1)

            except Exception as e:
                # Response might not be JSON or other error
                log_error(f"Error processing signin response: {e}")
                import traceback
                traceback.print_exc()
                return None, None
        else:
            log_error(f"Signin failed: {response.status_code} - {response.text}")
            sys.exit(1)
    except Exception as e:
        log_error(f"Signin error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def create_note(client: httpx.AsyncClient, access_token: str) -> Optional[int]:
    """
    Create a new audio note via REST API.

    Args:
        client: HTTP client
        access_token: JWT access token for authentication

    Returns:
        Note ID if successful, None otherwise
    """
    try:
        note_data = {
            "title": "Test Audio Upload",
            "tags": "test,websocket,upload",
            "text_notes": "Testing WebSocket file upload functionality"
        }

        # DEBUG: Show authentication header
        print(f"\n{Colors.YELLOW}[DEBUG] POST /api/notes with authentication:{Colors.END}")
        print(f"  {Colors.YELLOW}Authorization: Bearer {access_token[:30]}...{Colors.END}")

        # Try different authentication header formats
        auth_headers = [
            {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            {"st-access-token": access_token, "Content-Type": "application/json"},
            {"Cookie": f"st-access-token={access_token}", "Content-Type": "application/json"},
        ]

        for attempt, headers in enumerate(auth_headers, 1):
            auth_method = list(headers.keys())[0] if headers else "unknown"
            print(f"\n  {Colors.YELLOW}[Attempt {attempt}] Using: {auth_method}{Colors.END}")

            response = await client.post(
                f"{BACKEND_URL}/api/notes",
                json=note_data,
                headers=headers
            )

            # DEBUG: Show request details
            print(f"    {Colors.YELLOW}Status code: {response.status_code}{Colors.END}")

            if response.status_code == 201:
                data = response.json()
                note_id = data.get("id")
                log_success(f"Created note with ID: {note_id}")
                log_success(f"Authentication method that worked: {auth_method}")
                return note_id
            elif response.status_code == 401:
                print(f"    {Colors.RED}✗ 401 Unauthorized with {auth_method}{Colors.END}")
                if attempt < len(auth_headers):
                    print(f"    {Colors.YELLOW}Trying next authentication method...{Colors.END}")
                    continue
                else:
                    # Last attempt failed
                    print(f"\n{Colors.RED}[ERROR] All authentication methods failed!{Colors.END}")
                    print(f"  {Colors.RED}Response body: {response.text}{Colors.END}")
                    print(f"  {Colors.RED}Request headers sent:{Colors.END}")
                    for header_name, header_value in response.request.headers.items():
                        print(f"    {Colors.RED}{header_name}: {header_value}{Colors.END}")
                    log_error(f"Failed to create note: 401 Unauthorized")
                    return None
            else:
                log_error(f"Failed to create note: {response.status_code} - {response.text}")
                return None

        # Should not reach here
        return None
    except Exception as e:
        log_error(f"Error creating note: {e}")
        import traceback
        traceback.print_exc()
        return None


async def upload_file_via_websocket_aiohttp(
    note_id: int,
    file_path: str,
    user_id: str
) -> bool:
    """
    Upload audio file via WebSocket using aiohttp (fallback method).

    Args:
        note_id: ID of the note to upload to
        file_path: Path to the audio file
        user_id: User ID for authentication

    Returns:
        True if successful, False otherwise
    """
    if not AIOHTTP_AVAILABLE:
        log_error("aiohttp is not installed. Install with: pip install aiohttp")
        return False

    try:
        file_size = os.path.getsize(file_path)
        log_info(f"File size: {file_size / 1024:.1f} KB")

        ws_url = f"{WS_URL}/ws/upload?note_id={note_id}&user_id={user_id}"

        async with aiohttp.ClientSession() as session:
            print(f"\n{Colors.YELLOW}[DEBUG] Using aiohttp WebSocket{Colors.END}")
            print(f"  {Colors.YELLOW}URL: {ws_url}{Colors.END}")

            # Connect WITHOUT authentication headers (backend uses query params only)
            async with session.ws_connect(ws_url) as ws:
                log_success("WebSocket connection established using: aiohttp")

                # Wait for initial message from server
                try:
                    msg = await asyncio.wait_for(ws.receive(timeout=5.0), timeout=5.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        log_info(f"Server message: {data.get('message', 'Connected')}")
                except asyncio.TimeoutError:
                    log_info("No initial message from server (continuing...)")

                # Upload file in chunks
                bytes_sent = 0
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        # Send chunk as binary data
                        await ws.send_bytes(chunk)
                        bytes_sent += len(chunk)

                        # Calculate progress
                        progress = (bytes_sent / file_size) * 100
                        log_progress(
                            f"Uploading: {bytes_sent / 1024:.1f} KB / {file_size / 1024:.1f} KB ({progress:.1f}%)"
                        )

                        # Wait for acknowledgment
                        try:
                            msg = await asyncio.wait_for(ws.receive(timeout=1.0), timeout=1.0)
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                if data.get('status') == 'error':
                                    log_error(f"Upload error: {data.get('message')}")
                                    return False
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                log_error(f"WebSocket error: {ws.exception()}")
                                return False
                        except asyncio.TimeoutError:
                            # No response, continue
                            pass

                log_success(f"File fully uploaded: {bytes_sent / 1024:.1f} KB")

                # Wait for final confirmation
                try:
                    msg = await asyncio.wait_for(ws.receive(timeout=5.0), timeout=5.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        log_success(
                            f"Server response: status={data.get('status')}, "
                            f"filepath={data.get('filepath', 'N/A')}"
                        )
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        log_info("WebSocket closed by server")
                except asyncio.TimeoutError:
                    log_info("No final confirmation from server")

                # Close WebSocket
                await ws.close()
                log_success("WebSocket connection closed")

                return True

    except Exception as e:
        log_error(f"aiohttp WebSocket upload error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def upload_file_via_websocket(
    note_id: int,
    file_path: str,
    user_id: str
) -> bool:
    """
    Upload audio file via WebSocket.

    Args:
        note_id: ID of the note to upload to
        file_path: Path to the audio file
        user_id: User ID for authentication

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        log_info(f"File size: {file_size / 1024:.1f} KB")

        # Connect to WebSocket with note_id and user_id in query parameters
        ws_url = f"{WS_URL}/ws/upload?note_id={note_id}&user_id={user_id}"

        print(f"\n{Colors.YELLOW}[DEBUG] WebSocket connection:{Colors.END}")
        print(f"  {Colors.YELLOW}URL: {ws_url}{Colors.END}")

        try:
            # Connect WITHOUT authentication headers (backend uses query params only)
            async with websockets.connect(ws_url) as ws:
                log_success("WebSocket connection established")

                # Wait for initial message from server
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    try:
                        data = json.loads(msg)
                        log_info(f"Server message: {data.get('message', 'Connected')}")
                    except (json.JSONDecodeError, TypeError):
                        log_info("Received non-JSON initial message")
                except asyncio.TimeoutError:
                    log_info("No initial message from server (continuing...)")

                # Upload file in chunks
                bytes_sent = 0
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        # Send chunk as binary data
                        await ws.send(chunk)
                        bytes_sent += len(chunk)

                        # Calculate progress
                        progress = (bytes_sent / file_size) * 100
                        log_progress(
                            f"Uploading: {bytes_sent / 1024:.1f} KB / {file_size / 1024:.1f} KB ({progress:.1f}%)"
                        )

                        # Wait for acknowledgment from server
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            try:
                                data = json.loads(msg)
                                if data.get('status') == 'error':
                                    log_error(f"Server error: {data.get('message')}")
                                    return False
                            except (json.JSONDecodeError, TypeError):
                                # Not JSON, ignore
                                pass
                        except asyncio.TimeoutError:
                            # No response, continue
                            pass

                log_success(f"File fully uploaded: {bytes_sent / 1024:.1f} KB")

                # Wait for completion message from server
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        data = json.loads(msg)

                        if data.get('status') == 'completed':
                            log_success("Upload completed!")
                            log_success(f"File path: {data.get('filepath')}")
                            log_success(f"Note ID: {data.get('note_id')}")
                            break
                        elif data.get('status') == 'error':
                            log_error(f"Server error: {data.get('message')}")
                            return False
                        else:
                            log_info(f"Server status: {data.get('status')}")
                    except asyncio.TimeoutError:
                        log_info("No final confirmation from server")
                        break
                    except (json.JSONDecodeError, TypeError):
                        log_info("Received non-JSON final message")
                        break

                # Close WebSocket
                await ws.close()
                log_success("WebSocket connection closed")

                return True

        except Exception as e:
            log_error(f"WebSocket connection error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        log_error(f"WebSocket upload error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def get_note_status(client: httpx.AsyncClient, note_id: int, access_token: str) -> Optional[dict]:
    """
    Get note status and details.

    Args:
        client: HTTP client
        note_id: ID of the note
        access_token: JWT access token for authentication

    Returns:
        Note data if successful, None otherwise
    """
    try:
        response = await client.get(
            f"{BACKEND_URL}/api/notes/{note_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            log_error(f"Failed to get note: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_error(f"Error getting note: {e}")
        return None


async def mark_upload_complete(client: httpx.AsyncClient, note_id: int, access_token: str) -> bool:
    """
    Mark upload as complete and trigger transcription.

    Args:
        client: HTTP client
        note_id: ID of the note
        access_token: JWT access token for authentication

    Returns:
        True if successful, False otherwise
    """
    try:
        response = await client.post(
            f"{BACKEND_URL}/api/notes/{note_id}/upload-complete",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        if response.status_code == 200:
            data = response.json()
            log_success(f"Upload marked complete: {data.get('message')}")
            return True
        else:
            log_error(f"Failed to mark upload complete: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_error(f"Error marking upload complete: {e}")
        return False


def print_note_details(note: dict):
    """Print formatted note details."""
    print(f"\n{Colors.BOLD}📋 Note Details:{Colors.END}")
    print(f"  {Colors.BOLD}ID:{Colors.END} {note.get('id')}")
    print(f"  {Colors.BOLD}Title:{Colors.END} {note.get('title')}")
    print(f"  {Colors.BOLD}Status:{Colors.END} {note.get('status')}")
    print(f"  {Colors.BOLD}Tags:{Colors.END} {note.get('tags', 'N/A')}")

    transcription = note.get('transcription')
    if transcription:
        print(f"  {Colors.BOLD}Transcription:{Colors.END} {transcription[:200]}..." if len(transcription) > 200 else f"  {Colors.BOLD}Transcription:{Colors.END} {transcription}")
    else:
        print(f"  {Colors.BOLD}Transcription:{Colors.END} (not yet available)")

    summary = note.get('summary')
    if summary:
        print(f"  {Colors.BOLD}Summary:{Colors.END} {summary[:200]}..." if len(summary) > 200 else f"  {Colors.BOLD}Summary:{Colors.END} {summary}")
    else:
        print(f"  {Colors.BOLD}Summary:{Colors.END} (not yet available)")

    print(f"  {Colors.BOLD}File Path:{Colors.END} {note.get('file_path', 'N/A')}")
    print(f"  {Colors.BOLD}Created:{Colors.END} {note.get('created_at', 'N/A')}")
    print()


async def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test WebSocket audio upload with SuperTokens auth")
    parser.add_argument("--static-email", action="store_true",
                       help="Use static email (test@example.com) instead of unique timestamp-based email")
    args = parser.parse_args()

    # Determine email to use
    if args.static_email:
        # Use static email (old behavior, not recommended)
        test_email = "test@example.com"
        log_info(f"Using static email (--static-email mode): {test_email}")
        log_info(f"⚠️  Warning: May cause conflicts if user already exists")
    else:
        # Use unique email with timestamp (DEFAULT behavior)
        test_email = EMAIL

    print(f"\n{Colors.BOLD}{'='*60}")
    print("Audio Notes WebSocket Upload Test")
    print(f"{'='*60}{Colors.END}\n")

    print(f"{Colors.BOLD}[INFO] Using test credentials:{Colors.END}")
    print(f"  {Colors.BOLD}Email:{Colors.END} {test_email}")
    print(f"  {Colors.BOLD}Password:{Colors.END} {PASSWORD}")
    print(f"  {Colors.GREEN}✓ Unique email strategy enabled (timestamp: {TIMESTAMP}){Colors.END}\n")

    # Check if test file exists
    if not os.path.exists(TEST_FILE):
        log_error(f"Test file not found: {TEST_FILE}")
        sys.exit(1)

    log_info(f"Test file: {TEST_FILE}")
    log_info(f"Backend URL: {BACKEND_URL}")

    # Create httpx client - cookies are automatically managed
    async with httpx.AsyncClient(timeout=30.0) as client:

        # Step 1: Sign up (or skip if user exists)
        log_info("Step 1: Authentication - Signup")
        await signup_user(client, test_email, PASSWORD)

        # Step 2: Sign in and get access token and user_id
        log_info("Step 2: Authentication - Signin")
        access_token, user_id = await signin_user(client, test_email, PASSWORD)

        if not access_token or not user_id:
            log_error("Failed to get access token or user_id. Exiting.")
            sys.exit(1)

        # DEBUG: Try alternative SuperTokens endpoints
        print(f"\n{Colors.YELLOW}[DEBUG] Checking alternative SuperTokens endpoints:{Colors.END}")
        alternative_endpoints = [
            "/auth/session/refresh",
            "/recipe/signin",
            "/auth/session",
            "/auth/jwt/refresh"
        ]
        for endpoint in alternative_endpoints:
            try:
                resp = await client.get(f"{BACKEND_URL}{endpoint}")
                print(f"  {Colors.GREEN}✓ {endpoint} exists: {resp.status_code}{Colors.END}")
            except Exception as e:
                print(f"  {Colors.YELLOW}✗ {endpoint}: {str(e)[:50]}{Colors.END}")

        # Step 3: Create note
        log_info("Step 3: Creating note")
        note_id = await create_note(client, access_token)
        if not note_id:
            log_error("Failed to create note. Exiting.")
            sys.exit(1)

        # Step 4: Upload file via WebSocket
        log_info(f"Step 4: Uploading file via WebSocket")
        if not await upload_file_via_websocket(note_id, TEST_FILE, user_id):
            log_error("File upload failed. Exiting.")
            sys.exit(1)

        # Step 5: Mark upload complete
        log_info("Step 5: Marking upload complete")
        if not await mark_upload_complete(client, note_id, access_token):
            log_error("Failed to mark upload complete. Exiting.")
            sys.exit(1)

        # Step 6: Wait for processing
        log_info(f"Step 6: Waiting for worker processing ({PROCESSING_WAIT} seconds)...")
        await asyncio.sleep(PROCESSING_WAIT)

        # Step 7: Check result
        log_info("Step 7: Checking final status")
        note = await get_note_status(client, note_id, access_token)
        if note:
            print_note_details(note)

            # Additional checks
            if note.get('status') == 'completed':
                log_success("Processing completed successfully!")
            elif note.get('status') in ['processing', 'pending', 'pending_summarization', 'processing_summary']:
                log_info(f"Processing in progress: {note.get('status')}")
                log_info("You may need to wait longer for full completion")
            else:
                log_error(f"Unexpected status: {note.get('status')}")
        else:
            log_error("Failed to retrieve note details")

    print(f"{Colors.BOLD}{'='*60}")
    print("Test completed")
    print(f"{'='*60}{Colors.END}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
