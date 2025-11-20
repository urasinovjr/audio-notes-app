"""
Authentication helper endpoints.

This module provides helper endpoints for authentication,
specifically for Swagger/API testing purposes.
"""

from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from supertokens_python.recipe.emailpassword.asyncio import sign_in, sign_up

router = APIRouter(tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response model with access token for Bearer authentication."""

    access_token: str
    user_id: str
    token_type: str = "Bearer"

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJraWQiOiJkLTE3NjM1NTIwODc0NzUi...",
                "user_id": "fb382527-dfb6-43ac-8560-55f99edf407b",
                "token_type": "Bearer",
            }
        }


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Get authentication token (for Swagger/API testing)",
    description="""
    Get authentication token by email and password.

    This endpoint is specifically designed for Swagger UI and API testing.
    It performs signin using SuperTokens and returns an access token.

    **How to use in Swagger:**
    1. Call this endpoint with your credentials
    2. Copy the `access_token` from response
    3. Click "Authorize" button at the top of Swagger UI
    4. Paste the token (without "Bearer" prefix)
    5. Click "Authorize" and "Close"
    6. Now you can call protected endpoints

    **Note:** For web applications, use the standard SuperTokens flow with cookies.
    """,
)
async def get_auth_token(request: Request, credentials: LoginRequest) -> TokenResponse:
    """
    Authenticate user and get access token using SuperTokens SDK.
    """
    try:
        # Sign in using SuperTokens SDK
        result = await sign_in("public", credentials.email, credentials.password)

        # Check for wrong credentials error
        if hasattr(result, "status") and result.status == "WRONG_CREDENTIALS_ERROR":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        # Check if we have a user (successful sign in)
        # Note: sign_in might return different result types depending on version/config
        if hasattr(result, "user"):
            # Create JWT token for API testing
            # This is a simplified token for Swagger/API testing purposes
            now = datetime.utcnow()
            payload = {
                "sub": str(result.user.id),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=7)).timestamp()),
            }

            # Use a simple secret for JWT signing (for testing purposes only)
            secret = "testing-secret-key-for-swagger-auth"
            access_token = jwt.encode(payload, secret, algorithm="HS256")

            return TokenResponse(access_token=access_token, user_id=str(result.user.id))

        # If we get here, something unexpected happened
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}",
        ) from e


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user (for Swagger/API testing)",
    description="""
    Register a new user and get authentication token.

    This endpoint is specifically designed for Swagger UI and API testing.
    It performs signup using SuperTokens and returns an access token.

    **How to use in Swagger:**
    1. Call this endpoint with new user credentials
    2. Copy the `access_token` from response
    3. Click "Authorize" button at the top
    4. Paste the token
    5. Now you can call protected endpoints

    If user already exists, it will automatically signin instead.
    """,
)
async def register_user(request: Request, credentials: LoginRequest) -> TokenResponse:
    """
    Register new user and get access token using SuperTokens SDK.
    """
    try:
        # Try to sign up using SuperTokens SDK
        result = await sign_up("public", credentials.email, credentials.password)

        # If user already exists, signin instead
        if hasattr(result, "status") and result.status == "EMAIL_ALREADY_EXISTS_ERROR":
            return await get_auth_token(request, credentials)

        if hasattr(result, "user") and hasattr(result, "status") and result.status == "OK":
            # Create JWT token for API testing
            # This is a simplified token for Swagger/API testing purposes
            now = datetime.utcnow()
            payload = {
                "sub": str(result.user.id),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=7)).timestamp()),
            }

            # Use a simple secret for JWT signing (for testing purposes only)
            secret = "testing-secret-key-for-swagger-auth"
            access_token = jwt.encode(payload, secret, algorithm="HS256")

            return TokenResponse(access_token=access_token, user_id=str(result.user.id))

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}",
        ) from e
