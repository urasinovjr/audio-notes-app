"""
Transcription worker.

This module contains the RabbitMQ consumer that processes transcription tasks
using Deepgram for audio transcription. After successful transcription,
it sends the note to the summarization queue.
"""

import asyncio
import json
import os
import signal
import sys
import time

import aio_pika
import httpx
from loguru import logger
from sqlalchemy import update
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.db.database import async_session
from app.db.models import AudioNote
from app.services.queue import QueueService

# Constants
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_MODEL = "nova-2"
DEEPGRAM_LANGUAGE = "ru"
HTTP_TIMEOUT = 60.0
QUEUE_PREFETCH_COUNT = 1
TRANSCRIPTION_QUEUE_NAME = "transcription"
LOG_ROTATION = "1 day"
LOG_RETENTION = "7 days"
LOG_COMPRESSION = "zip"

# Graceful shutdown event
shutdown_event = asyncio.Event()


def shutdown_handler(sig: int, frame: object) -> None:
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()


# Register signal handlers
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Configure logging format
logger.remove()  # Remove default handler

# Console output (colored, for development)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# File logging (with rotation)
logger.add(
    "/app/logs/transcription_worker_{time:YYYY-MM-DD}.log",
    rotation=LOG_ROTATION,  # New file every day
    retention=LOG_RETENTION,  # Keep logs for 7 days
    compression=LOG_COMPRESSION,  # Compress old logs
    level="DEBUG",  # Log all levels
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def transcribe_audio_with_retry(file_path: str, note_id: int) -> tuple[str, float]:
    """
    Transcribe audio with retry logic.

    Retries up to 3 times with exponential backoff.

    Args:
        file_path: Path to the audio file
        note_id: ID of the note being transcribed

    Returns:
        Tuple of (transcription text, confidence score)

    Raises:
        Exception: If transcription fails after all retries
    """
    try:
        file_size = os.path.getsize(file_path)
        logger.info(
            f"Attempting transcription (note_id={note_id})",
            file_path=file_path,
            file_size_bytes=file_size,
        )

        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()

        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "Content-Type": "audio/mpeg",
        }

        url = f"{DEEPGRAM_API_URL}?model={DEEPGRAM_MODEL}&language={DEEPGRAM_LANGUAGE}&smart_format=true"

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                url,
                content=audio_data,
                headers=headers,
            )

            if response.status_code != 200:
                error_msg = f"Deepgram API error: {response.status_code} {response.text}"
                logger.error(error_msg, note_id=note_id)
                raise Exception(error_msg)

            result = response.json()
            transcription = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            confidence = result["results"]["channels"][0]["alternatives"][0].get("confidence", 0.0)

            logger.info(
                "Deepgram response received",
                note_id=note_id,
                transcription_length=len(transcription),
                confidence=confidence,
                transcription_preview=transcription[:100],
            )

            return transcription, confidence

    except Exception as e:
        logger.error(f"Transcription attempt failed: {e}", note_id=note_id)
        raise


async def process_transcription(task_data: dict, queue_service: QueueService):
    """
    Process a transcription task.

    This function:
    1. Updates the note status to "processing"
    2. Transcribes the audio file using Deepgram
    3. Updates the database with transcription
    4. Sends task to summarization queue
    5. Sets status to "pending_summarization" or "failed"

    Args:
        task_data: Dictionary containing note_id, file_path, and user_id
        queue_service: QueueService instance for sending summarization tasks
    """
    note_id = task_data["note_id"]
    file_path = task_data["file_path"]
    user_id = task_data["user_id"]

    start_time = time.time()
    logger.info("Processing note", note_id=note_id, user_id=user_id, file_path=file_path)

    async with async_session() as db:
        # 1. Update status to "processing"
        await db.execute(
            update(AudioNote).where(AudioNote.id == note_id).values(status="processing")
        )
        await db.commit()
        logger.debug("Status updated to 'processing'", note_id=note_id)

        try:
            # 2. Transcription via Deepgram with retry logic
            logger.debug("Calling Deepgram API with retry", note_id=note_id, file_path=file_path)
            transcription, confidence = await transcribe_audio_with_retry(file_path, note_id)

            # 3. Save transcription to database
            logger.debug("Saving transcription to database", note_id=note_id)
            await db.execute(
                update(AudioNote)
                .where(AudioNote.id == note_id)
                .values(transcription=transcription, status="pending_summarization")
            )
            await db.commit()
            logger.info("Transcription saved", note_id=note_id, status="pending_summarization")

            # 4. Send task to summarization queue
            try:
                await queue_service.send_task("summarization", {"note_id": note_id})
                logger.info("Sent summarization task", note_id=note_id)
            except Exception as e:
                logger.error("Failed to send summarization task", note_id=note_id, error=str(e))
                # Don't fail the transcription if we can't queue summarization
                # The transcription is already saved

            # Calculate and log processing duration
            duration = time.time() - start_time
            logger.info(
                "Transcription completed successfully",
                note_id=note_id,
                duration_seconds=round(duration, 2),
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                "Error processing note",
                note_id=note_id,
                error=str(e),
                duration_seconds=round(duration, 2),
            )

            # Update status to "failed"
            await db.execute(
                update(AudioNote).where(AudioNote.id == note_id).values(status="failed")
            )
            await db.commit()


async def start_worker():
    """
    Start the transcription worker.

    This function connects to RabbitMQ and starts consuming messages
    from the transcription queue. Each message is processed by the
    process_transcription function.
    """
    logger.info("Transcription worker starting...")
    logger.info("Connecting to RabbitMQ", url=settings.RABBITMQ_URL)

    # Initialize queue service for sending summarization tasks
    queue_service = QueueService()
    await queue_service.connect()

    # Connect to RabbitMQ for consuming
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        logger.info("Connected to RabbitMQ successfully")

        # Create channel
        channel = await connection.channel()

        # Set QoS to process one message at a time
        await channel.set_qos(prefetch_count=QUEUE_PREFETCH_COUNT)

        # Declare queue
        queue = await channel.declare_queue(TRANSCRIPTION_QUEUE_NAME, durable=True)

        logger.info("Listening on queue 'transcription'", queue_name=queue.name)
        logger.info("Waiting for messages... Press CTRL+C to exit")

        # Start consuming messages with graceful shutdown support
        try:
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    # Check for shutdown signal
                    if shutdown_event.is_set():
                        logger.info("Shutdown signal received, stopping message processing")
                        break

                    async with message.process():
                        try:
                            # Decode and parse task data
                            task_data = json.loads(message.body.decode())

                            logger.info("Received task", task_data=task_data)

                            # Process the task
                            await process_transcription(task_data, queue_service)

                        except Exception as e:
                            logger.exception("Error processing task", error=str(e))
        except Exception as e:
            logger.exception("Worker error", exc_info=e)
        finally:
            logger.info("Worker shutting down gracefully")


if __name__ == "__main__":
    """
    Run the worker directly.

    Usage:
        python -m app.workers.transcription_worker
    """
    asyncio.run(start_worker())
