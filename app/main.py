"""
Audio Notes API main application.

This module sets up the FastAPI application with authentication,
database connections, and message queue services.
"""

import signal
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

from app.api import router as api_router
from app.api.routes import websocket
from app.core.config import settings
from app.core.exceptions import (
    AudioNotesException,
    audio_notes_exception_handler,
    general_exception_handler,
    http_exception_handler,
)
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.core.security import SecurityHeadersMiddleware
from app.core.supertokens import init_supertokens
from app.db.database import connect_db, disconnect_db
from app.services.queue import queue_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Audio notes application with AI transcription and summarization",
)

# Initialize Supertokens
init_supertokens()

# Initialize rate limiter
app.state.limiter = limiter

# Register exception handlers
app.add_exception_handler(AudioNotesException, audio_notes_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware (configured once with Supertokens headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] + settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type"] + get_all_cors_headers(),
)

# Add Supertokens middleware
app.add_middleware(get_middleware())

# Add rate limiting middleware
app.add_middleware(SlowAPIMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Include API routes
app.include_router(api_router)
app.include_router(websocket.router)


# Graceful shutdown handler
def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, closing connections...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.on_event("startup")
async def startup_event():
    """Initialize database and queue connections on application startup."""
    await connect_db()
    await queue_service.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database and queue connections on application shutdown."""
    logger.info("Application shutting down...")
    await disconnect_db()
    await queue_service.disconnect()
    logger.info("All connections closed gracefully")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Audio Notes API is running", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
