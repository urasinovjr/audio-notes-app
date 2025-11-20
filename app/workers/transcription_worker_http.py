"""
Transcription worker (HTTP version).

Alternative implementation using direct HTTP requests to Deepgram API
instead of the SDK. Use this if the SDK has issues.
"""

import asyncio
import json

import aio_pika
import httpx
from google import generativeai as genai
from sqlalchemy import update

from app.core.config import settings
from app.db.database import async_session
from app.db.models import AudioNote

# Initialize Gemini API client
genai.configure(api_key=settings.GEMINI_API_KEY)


async def process_transcription(task_data: dict):
    """
    Process a transcription task using HTTP requests.

    This function:
    1. Updates the note status to "processing"
    2. Transcribes the audio file using Deepgram HTTP API
    3. Generates a summary using Google Gemini
    4. Updates the database with results
    5. Sets status to "completed" or "failed"

    Args:
        task_data: Dictionary containing note_id, file_path, and user_id
    """
    note_id = task_data["note_id"]
    file_path = task_data["file_path"]

    print(f"[Worker] Processing note {note_id}")

    async with async_session() as db:
        # 1. Update status to "processing"
        await db.execute(
            update(AudioNote).where(AudioNote.id == note_id).values(status="processing")
        )
        await db.commit()
        print("[Worker] Status updated to 'processing'")

        try:
            # 2. Transcription via Deepgram HTTP API
            print(f"[Worker] Starting transcription for {file_path}")

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    with open(file_path, "rb") as audio:
                        files = {"file": audio}
                        headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}

                        response = await client.post(
                            "https://api.deepgram.com/v1/listen?model=nova-2&language=ru&smart_format=true",
                            files=files,
                            headers=headers,
                        )

                        response.raise_for_status()
                        result = response.json()
                        transcription = result["results"]["channels"][0]["alternatives"][0][
                            "transcript"
                        ]
                        print(f"[Worker] Transcription completed: {len(transcription)} chars")

            except httpx.HTTPError as e:
                print(f"[Worker] Deepgram HTTP error: {e}")
                raise
            except Exception as e:
                print(f"[Worker] Deepgram error: {e}")
                raise

            # 3. Summarization via Gemini
            print("[Worker] Starting summarization")
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            prompt = f"""Создай краткое содержание следующего текста в 2-3 предложениях:

{transcription}

Краткое содержание:"""

            gemini_response = model.generate_content(prompt)
            summary = gemini_response.text.strip()
            print(f"[Worker] Summary generated: {len(summary)} chars")

            # 4. Save results to database
            await db.execute(
                update(AudioNote)
                .where(AudioNote.id == note_id)
                .values(transcription=transcription, summary=summary, status="completed")
            )
            await db.commit()
            print(f"[Worker] Note {note_id} completed successfully")

        except Exception as e:
            print(f"[Worker] Error processing note {note_id}: {e}")
            import traceback

            traceback.print_exc()

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
    print("[Worker] Starting transcription worker (HTTP version)...")
    print(f"[Worker] Connecting to RabbitMQ at {settings.RABBITMQ_URL}")

    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        # Create channel
        channel = await connection.channel()

        # Set QoS to process one message at a time
        await channel.set_qos(prefetch_count=1)

        # Declare queue
        queue = await channel.declare_queue("transcription", durable=True)

        print(f"[Worker] Listening on queue '{queue.name}'")
        print("[Worker] Waiting for messages... Press CTRL+C to exit")

        # Start consuming messages
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        # Decode and parse task data
                        task_data = json.loads(message.body.decode())

                        print(f"\n[Worker] Received task: {task_data}")

                        # Process the task
                        await process_transcription(task_data)

                    except Exception as e:
                        print(f"[Worker] Error processing task: {e}")
                        import traceback

                        traceback.print_exc()


if __name__ == "__main__":
    """
    Run the worker directly.

    Usage:
        python -m app.workers.transcription_worker_http
    """
    asyncio.run(start_worker())
