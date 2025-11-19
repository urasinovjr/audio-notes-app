"""
Summarization worker for transcribed audio notes using Gemini API.

This worker receives tasks from the "summarization" queue and creates brief summaries
of transcribed text using Google Gemini.
"""

import asyncio
import json
import signal
import sys
import time

import aio_pika
import google.generativeai as genai
from loguru import logger
from sqlalchemy import select, update
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.db.database import async_session
from app.db.models import AudioNote

# Constants
QUEUE_PREFETCH_COUNT = 1
SUMMARIZATION_QUEUE_NAME = "summarization"
GEMINI_TIMEOUT = 30.0
LOG_ROTATION = "1 day"
LOG_RETENTION = "7 days"
LOG_COMPRESSION = "zip"
TRANSCRIPTION_PREVIEW_LENGTH = 200
SUMMARY_PREVIEW_LENGTH = 100

# Graceful shutdown event
shutdown_event = asyncio.Event()


def shutdown_handler(sig: int, frame: object) -> None:
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()


# Register signal handlers
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Configure logging
logger.remove()  # Remove default handler

# Console output (colored)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# File logging (with rotation)
logger.add(
    "/app/logs/summarization_worker_{time:YYYY-MM-DD}.log",
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION,
    compression=LOG_COMPRESSION,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

# Configure Gemini API
if not settings.GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not set in environment!")
    raise ValueError("Missing GEMINI_API_KEY")

logger.info("Gemini API key configured", key_prefix=settings.GEMINI_API_KEY[:10])

genai.configure(api_key=settings.GEMINI_API_KEY)

# List of models to try (in priority order)
# Note: SDK automatically adds "models/" prefix to names
GEMINI_MODELS = [
    "gemini-flash-latest",  # -> models/gemini-flash-latest
    "gemini-2.5-flash",  # -> models/gemini-2.5-flash
    "gemini-pro-latest",  # -> models/gemini-pro-latest
    "gemini-2.5-pro",  # -> models/gemini-2.5-pro
    "gemini-2.0-flash",  # -> models/gemini-2.0-flash
]


def get_working_model():
    """
    Find a working Gemini model from the list of available models.

    Returns:
        genai.GenerativeModel: Working model instance

    Raises:
        RuntimeError: If no model works
    """
    for model_name in GEMINI_MODELS:
        try:
            logger.info("Trying to initialize model", model=model_name)
            test_model = genai.GenerativeModel(model_name)
            # Check model availability without making an actual request
            logger.info("Model initialized successfully", model=model_name)
            return test_model
        except Exception as e:
            logger.warning("Model failed to initialize", model=model_name, error=str(e))
            continue

    # If no model worked
    raise RuntimeError(
        f"No Gemini model available. Tried models: {', '.join(GEMINI_MODELS)}. "
        f"Check: https://ai.google.dev/models/gemini"
    )


# Initialize model at startup
try:
    model = get_working_model()
    logger.info("Using Gemini model", model=model.model_name)
except Exception as e:
    logger.error("Failed to initialize any Gemini model", error=str(e))
    model = None  # Will retry at runtime


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def summarize_with_retry(transcription: str, note_id: int) -> str:
    """
    Summarize transcription with retry logic.

    Retries up to 3 times with exponential backoff.

    Args:
        transcription: Text to summarize
        note_id: ID of the note being summarized

    Returns:
        Summary text

    Raises:
        Exception: If summarization fails after all retries
    """
    try:
        logger.info(f"Attempting summarization (note_id={note_id})")

        # Create prompt for Gemini (in Russian for Russian transcriptions)
        prompt = f"""
Ты — ассистент для создания кратких и информативных саммари аудио-заметок.

Текст транскрипции:
{transcription}

Задача: Создай краткое саммари (2-3 предложения), выделяя ключевые моменты и основную идею заметки.

Саммари:
"""

        # Get working model (try global model or get a new one)
        current_model = model if model is not None else get_working_model()

        logger.info("Calling Gemini API", note_id=note_id, model=current_model.model_name)

        # Call Gemini API with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(current_model.generate_content, prompt), timeout=GEMINI_TIMEOUT
        )
        summary = response.text.strip()

        logger.info(
            "Summary generated",
            note_id=note_id,
            summary_length=len(summary),
            summary_preview=summary[:SUMMARY_PREVIEW_LENGTH],
        )

        return summary

    except Exception as e:
        logger.error(f"Summarization attempt failed: {e}", note_id=note_id)
        raise


async def process_summarization(note_id: int) -> None:
    """
    Process summarization for a note.

    Args:
        note_id: ID of the note to summarize
    """
    async with async_session() as db:
        try:
            # 1. Fetch note from database
            result = await db.execute(select(AudioNote).where(AudioNote.id == note_id))
            note = result.scalar_one_or_none()

            if not note:
                logger.error("Note not found", note_id=note_id)
                return

            if not note.transcription:
                logger.error("Note has no transcription", note_id=note_id)
                await db.execute(
                    update(AudioNote).where(AudioNote.id == note_id).values(status="failed")
                )
                await db.commit()
                return

            logger.info(
                "Summarizing note", note_id=note.id, transcription_length=len(note.transcription)
            )

            # 2. Update status to processing
            await db.execute(
                update(AudioNote).where(AudioNote.id == note_id).values(status="processing_summary")
            )
            await db.commit()

            # 3. Summarize with retry logic
            start_time = time.time()
            try:
                summary = await summarize_with_retry(note.transcription, note_id)
                duration = time.time() - start_time
                logger.info(
                    "Summarization completed", note_id=note_id, duration_seconds=round(duration, 2)
                )

            except Exception as e:
                # If all retries failed, use fallback summary
                logger.error(
                    "All summarization attempts failed, using fallback",
                    note_id=note_id,
                    error=str(e),
                )
                max_len = TRANSCRIPTION_PREVIEW_LENGTH
                transcription_preview = (
                    note.transcription[:max_len] + "..."
                    if len(note.transcription) > max_len
                    else note.transcription
                )
                summary = f"Audio note. Content: {transcription_preview}"

            # 4. Update note in database
            await db.execute(
                update(AudioNote)
                .where(AudioNote.id == note_id)
                .values(summary=summary, status="completed")
            )
            await db.commit()

            logger.info(
                "Note summarization completed", note_id=note_id, summary_length=len(summary)
            )

        except Exception as e:
            logger.error("Error summarizing note", note_id=note_id, error=str(e), exc_info=True)
            # Update status to failed
            try:
                await db.execute(
                    update(AudioNote).where(AudioNote.id == note_id).values(status="failed")
                )
                await db.commit()
            except Exception as db_error:
                logger.error(
                    "Failed to update status to failed", note_id=note_id, error=str(db_error)
                )


async def start_worker() -> None:
    """
    Start the summarization worker.

    This function connects to RabbitMQ and starts consuming messages
    from the summarization queue. Each message is processed by the
    process_summarization function.
    """
    logger.info("Summarization worker starting...")
    logger.info("Connecting to RabbitMQ", url=settings.RABBITMQ_URL)

    # Connect to RabbitMQ for consuming
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        logger.info("Connected to RabbitMQ successfully")

        # Create channel
        channel = await connection.channel()

        # Set QoS to process one message at a time
        await channel.set_qos(prefetch_count=QUEUE_PREFETCH_COUNT)

        # Declare queue
        queue = await channel.declare_queue(SUMMARIZATION_QUEUE_NAME, durable=True)

        logger.info("Listening on queue 'summarization'", queue_name=queue.name)
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

                            logger.info("Received task", task=task_data)
                            note_id = task_data.get("note_id")

                            if not note_id:
                                logger.warning("Received message without note_id", task=task_data)
                                continue

                            # Process the task
                            await process_summarization(note_id)

                        except Exception as e:
                            logger.error("Error processing task", error=str(e), exc_info=True)
        except Exception as e:
            logger.exception("Worker error", exc_info=e)
        finally:
            logger.info("Worker shutting down gracefully")


if __name__ == "__main__":
    """
    Run the worker directly.

    Usage:
        python -m app.workers.summarization_worker
    """
    asyncio.run(start_worker())
