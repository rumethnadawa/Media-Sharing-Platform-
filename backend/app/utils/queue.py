"""
Queue utilities for message queue operations
Simulates SQS operations for local development
"""

import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MockSQS:
    """Mock SQS implementation for local development."""
    
    def __init__(self, queue_name: str = "media-processing-queue"):
        """Initialize mock SQS."""
        self.queue_name = queue_name
        self.messages: List[Dict] = []
        logger.info(f"MockSQS initialized: {queue_name}")
    
    def send_message(self, body: dict, message_attributes: Optional[dict] = None) -> str:
        """
        Send a message to the queue.
        
        Args:
            body: Message body (dict)
            message_attributes: Optional message attributes
            
        Returns:
            Message ID
        """
        try:
            message_id = str(uuid.uuid4())
            message = {
                'MessageId': message_id,
                'Body': json.dumps(body),
                'Attributes': {
                    'ApproximateReceiveCount': '0',
                    'SentTimestamp': str(int(datetime.utcnow().timestamp() * 1000))
                },
                'MessageAttributes': message_attributes or {}
            }
            self.messages.append(message)
            logger.info(f"Message sent: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    def receive_messages(self, max_number: int = 1) -> List[Dict]:
        """
        Receive messages from the queue.
        
        Args:
            max_number: Maximum number of messages to retrieve
            
        Returns:
            List of messages
        """
        try:
            messages = self.messages[:max_number]
            logger.info(f"Received {len(messages)} messages")
            return messages
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            return []
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message from the queue.
        
        Args:
            message_id: Message ID to delete
            
        Returns:
            True if successful
        """
        try:
            self.messages = [m for m in self.messages if m['MessageId'] != message_id]
            logger.info(f"Message deleted: {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False
    
    def get_queue_size(self) -> int:
        """Get number of messages in queue."""
        return len(self.messages)
    
    def clear_queue(self):
        """Clear all messages from queue."""
        self.messages = []
        logger.info("Queue cleared")
