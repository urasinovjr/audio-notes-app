"""
RabbitMQ queue service.

This module provides RabbitMQ integration for task queuing.
"""

import json
from typing import Dict

import aio_pika

from app.core.config import settings


class QueueService:
    """Service for managing RabbitMQ connections and task publishing."""

    def __init__(self):
        """Initialize the queue service."""
        self.connection = None
        self.channel = None

    async def connect(self):
        """
        Connect to RabbitMQ.

        Establishes a robust connection to RabbitMQ that will automatically
        reconnect on connection failures.
        """
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self.channel = await self.connection.channel()

    async def disconnect(self):
        """
        Disconnect from RabbitMQ.

        Closes the connection to RabbitMQ gracefully.
        """
        if self.connection:
            await self.connection.close()

    async def send_task(self, queue_name: str, task_data: Dict):
        """
        Send a task to a queue.

        Args:
            queue_name: Name of the queue to send the task to
            task_data: Task data to be sent (will be JSON serialized)

        Raises:
            Exception: If connection is not established or message cannot be sent
        """
        if not self.channel:
            raise Exception("Queue service not connected. Call connect() first.")

        # Declare queue (ensures it exists)
        queue = await self.channel.declare_queue(queue_name, durable=True)

        # Create message
        message = aio_pika.Message(
            body=json.dumps(task_data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        # Publish to default exchange with routing_key = queue_name
        await self.channel.default_exchange.publish(
            message,
            routing_key=queue_name,
        )


# Global queue service instance
queue_service = QueueService()
