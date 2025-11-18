"""
Transcription worker.

This module contains the RabbitMQ consumer that processes transcription tasks.
"""

import asyncio
import json

import aio_pika

from app.core.config import settings


async def process_transcription_task(task: dict):
    """
    Process a transcription task.

    Args:
        task: Task data containing note_id, file_path, and user_id

    Note:
        This is a placeholder implementation. Actual transcription logic
        will be added later using Deepgram API.
    """
    note_id = task.get("note_id")
    file_path = task.get("file_path")
    user_id = task.get("user_id")

    print(f"Processing transcription task:")
    print(f"  Note ID: {note_id}")
    print(f"  File Path: {file_path}")
    print(f"  User ID: {user_id}")

    # TODO: Implement actual transcription logic
    # 1. Read audio file from file_path
    # 2. Send to Deepgram API
    # 3. Get transcription result
    # 4. Update database with transcription
    # 5. Queue summarization task

    # Simulate processing
    await asyncio.sleep(1)

    print(f"Transcription task completed for note {note_id}")


async def start_worker():
    """
    Start the transcription worker.

    This function connects to RabbitMQ and starts consuming messages
    from the transcription queue.
    """
    print("Starting transcription worker...")
    print(f"Connecting to RabbitMQ at {settings.RABBITMQ_URL}")

    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        # Create channel
        channel = await connection.channel()

        # Set QoS to process one message at a time
        await channel.set_qos(prefetch_count=1)

        # Declare queue
        queue = await channel.declare_queue("transcription", durable=True)

        print(f"Worker is ready. Waiting for messages in '{queue.name}' queue...")

        # Start consuming messages
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        # Decode and parse task data
                        task = json.loads(message.body.decode())

                        print(f"\nReceived task: {task}")

                        # Process the task
                        await process_transcription_task(task)

                    except Exception as e:
                        print(f"Error processing task: {e}")
                        # TODO: Implement error handling and retry logic


if __name__ == "__main__":
    """
    Run the worker directly.

    Usage:
        python -m app.workers.transcription_worker
    """
    asyncio.run(start_worker())
