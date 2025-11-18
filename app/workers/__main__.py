"""
Worker entry point.

This module allows running the transcription worker as a module:
    python -m app.workers
"""

import asyncio

from app.workers.transcription_worker import start_worker

if __name__ == "__main__":
    asyncio.run(start_worker())
