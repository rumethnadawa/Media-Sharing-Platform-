"""
Database abstraction layer
Provides interface for database operations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class DatabaseInterface(ABC):
    """Abstract base class for database operations."""

    @abstractmethod
    def put_item(self, item_id: str, item: dict) -> bool:
        """Store or update an item."""
        pass

    @abstractmethod
    def get_item(self, item_id: str) -> Optional[dict]:
        """Retrieve an item."""
        pass

    @abstractmethod
    def update_item(self, item_id: str, updates: dict) -> bool:
        """Update an item."""
        pass

    @abstractmethod
    def delete_item(self, item_id: str) -> bool:
        """Delete an item."""
        pass

    @abstractmethod
    def scan(self) -> List[dict]:
        """Retrieve all items."""
        pass

    @abstractmethod
    def query_by_status(self, status: str) -> List[dict]:
        """Query items by status."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Get total count of items."""
        pass
