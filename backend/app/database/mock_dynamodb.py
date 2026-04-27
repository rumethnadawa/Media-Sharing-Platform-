"""
Mock DynamoDB Database Layer
Group A - Media Sharing Platform
Backend Developer: PHDB Nayanakantha

This module provides a local DynamoDB simulation for development and testing.
In production, replace with actual AWS DynamoDB client.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MockDynamoDB:
    """
    Mock DynamoDB implementation for local development and testing.
    Simulates DynamoDB table operations with JSON file storage.
    """

    def __init__(self, storage_file: str = "media_db.json"):
        """
        Initialize mock DynamoDB.
        
        Args:
            storage_file: JSON file to store media records
        """
        self.storage_file = storage_file
        self.data: Dict[str, dict] = {}
        self.load_from_file()

    def load_from_file(self):
        """Load data from JSON file if it exists."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    self.data = json.load(f)
                logger.info(f"Loaded {len(self.data)} records from {self.storage_file}")
            except Exception as e:
                logger.error(f"Error loading from file: {e}")
                self.data = {}
        else:
            self.data = {}

    def save_to_file(self):
        """Save data to JSON file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.debug(f"Saved {len(self.data)} records to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving to file: {e}")

    def put_item(self, item_id: str, item: dict) -> bool:
        """
        Store or update an item in the mock database.
        
        Args:
            item_id: Primary key (media_id)
            item: Item data as dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.load_from_file()  # Reload first to avoid overwriting sibling worker writes
            self.data[item_id] = item
            self.save_to_file()
            logger.info(f"Put item: {item_id}")
            return True
        except Exception as e:
            logger.error(f"Error putting item: {e}")
            return False

    def get_item(self, item_id: str) -> Optional[dict]:
        """
        Retrieve an item from the mock database.
        
        Args:
            item_id: Primary key (media_id)
            
        Returns:
            Item data or None if not found
        """
        try:
            self.load_from_file()  # Always read fresh from disk
            item = self.data.get(item_id)
            if item:
                logger.info(f"Got item: {item_id}")
            else:
                logger.warning(f"Item not found: {item_id}")
            return item
        except Exception as e:
            logger.error(f"Error getting item: {e}")
            return None

    def update_item(self, item_id: str, updates: dict) -> bool:
        """
        Update an existing item.
        
        Args:
            item_id: Primary key (media_id)
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False if item not found
        """
        try:
            self.load_from_file()  # Reload first to avoid overwriting sibling worker writes
            if item_id not in self.data:
                logger.warning(f"Item not found for update: {item_id}")
                return False

            # Update the item
            self.data[item_id].update(updates)
            # Always update the updated_at timestamp
            self.data[item_id]['updated_at'] = datetime.utcnow().isoformat()
            
            self.save_to_file()
            logger.info(f"Updated item: {item_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating item: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """
        Delete an item from the mock database.
        
        Args:
            item_id: Primary key (media_id)
            
        Returns:
            True if successful, False if item not found
        """
        try:
            self.load_from_file()  # Reload first to avoid overwriting sibling worker writes
            if item_id in self.data:
                del self.data[item_id]
                self.save_to_file()
                logger.info(f"Deleted item: {item_id}")
                return True
            else:
                logger.warning(f"Item not found for deletion: {item_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting item: {e}")
            return False

    def scan(self) -> List[dict]:
        """
        Retrieve all items from the mock database.
        
        Returns:
            List of all items
        """
        try:
            self.load_from_file()  # Always read fresh from disk
            items = list(self.data.values())
            logger.info(f"Scanned {len(items)} items")
            return items
        except Exception as e:
            logger.error(f"Error scanning: {e}")
            return []

    def query_by_status(self, status: str) -> List[dict]:
        """
        Query items by status (without index, linear scan).
        
        Args:
            status: Status value to filter by
            
        Returns:
            List of items with matching status
        """
        try:
            self.load_from_file()  # Always read fresh from disk
            items = [item for item in self.data.values() if item.get('status') == status]
            logger.info(f"Queried {len(items)} items with status: {status}")
            return items
        except Exception as e:
            logger.error(f"Error querying by status: {e}")
            return []

    def query_by_uploader(self, uploader: str) -> List[dict]:
        """
        Query items by uploader (without index, linear scan).
        
        Args:
            uploader: Uploader name to filter by
            
        Returns:
            List of items uploaded by the specified user
        """
        try:
            self.load_from_file()  # Always read fresh from disk
            items = [item for item in self.data.values() if item.get('uploader') == uploader]
            logger.info(f"Queried {len(items)} items by uploader: {uploader}")
            return items
        except Exception as e:
            logger.error(f"Error querying by uploader: {e}")
            return []

    def count(self) -> int:
        """Get total count of items."""
        self.load_from_file()  # Always read fresh from disk
        return len(self.data)

    def clear(self):
        """Clear all data (for testing)."""
        self.data = {}
        self.save_to_file()
        logger.info("Database cleared")

    def export_data(self) -> dict:
        """Export all data as dictionary."""
        return dict(self.data)

    def import_data(self, data: dict):
        """Import data from dictionary."""
        self.data = data
        self.save_to_file()
        logger.info(f"Imported {len(data)} records")
