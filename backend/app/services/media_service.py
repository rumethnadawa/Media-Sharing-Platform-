"""
Media Service - Core business logic for media operations
Group A - Media Sharing Platform
Backend Developer: PHDB Nayanakantha

This service handles all media-related operations including:
- Creating media records
- Updating media status
- Retrieving media information
- Managing media lifecycle
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from app.models import Media, MediaStatus
from app.database import MockDynamoDB
from app.utils.validators import validate_media_input, validate_media_id
from app.utils.exceptions import (
    MediaNotFoundError,
    InvalidMediaError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class MediaService:
    """
    Service layer for media operations.
    Handles business logic and database interactions.
    """

    def __init__(self, db: MockDynamoDB):
        """
        Initialize MediaService.
        
        Args:
            db: Database instance (MockDynamoDB)
        """
        self.db = db
        logger.info("MediaService initialized")

    def create_media(self, title: str, uploader: str, object_key: str, 
                    file_size: int, media_type: str, 
                    description: Optional[str] = None) -> Tuple[bool, Media, str]:
        """
        Create a new media record.
        
        Args:
            title: Title of the media
            uploader: Name of uploader
            object_key: S3 object key
            file_size: Size of media file in bytes
            media_type: Type of media (image/video)
            description: Optional description
            
        Returns:
            Tuple of (success: bool, media: Media, message: str)
        """
        try:
            # Validate input
            is_valid, error_msg = validate_media_input(
                title=title,
                uploader=uploader,
                object_key=object_key,
                file_size=file_size,
                media_type=media_type
            )
            
            if not is_valid:
                logger.warning(f"Invalid media input: {error_msg}")
                return False, None, error_msg

            # Create media object
            media = Media(
                title=title,
                uploader=uploader,
                object_key=object_key,
                status=MediaStatus.PENDING.value,
                file_size=file_size,
                media_type=media_type,
                description=description
            )

            # Store in database
            success = self.db.put_item(media.media_id, media.to_dict())
            
            if success:
                logger.info(f"Created media: {media.media_id}")
                message = f"Media created successfully. ID: {media.media_id}"
                return True, media, message
            else:
                logger.error("Failed to store media in database")
                return False, None, "Failed to store media in database"

        except Exception as e:
            logger.error(f"Error creating media: {e}")
            return False, None, str(e)

    def get_media(self, media_id: str) -> Tuple[bool, Optional[Media], str]:
        """
        Retrieve a media record by ID.
        
        Args:
            media_id: ID of the media
            
        Returns:
            Tuple of (success: bool, media: Media, message: str)
        """
        try:
            # Validate media_id
            is_valid, error_msg = validate_media_id(media_id)
            if not is_valid:
                logger.warning(f"Invalid media ID: {error_msg}")
                return False, None, error_msg

            # Retrieve from database
            media_dict = self.db.get_item(media_id)
            
            if media_dict:
                media = Media.from_dict(media_dict)
                logger.info(f"Retrieved media: {media_id}")
                return True, media, "Media found"
            else:
                logger.warning(f"Media not found: {media_id}")
                return False, None, f"Media not found: {media_id}"

        except Exception as e:
            logger.error(f"Error retrieving media: {e}")
            return False, None, str(e)

    def list_all_media(self) -> Tuple[bool, List[Media], str]:
        """
        Retrieve all media records.
        
        Returns:
            Tuple of (success: bool, media_list: List[Media], message: str)
        """
        try:
            media_dicts = self.db.scan()
            media_list = [Media.from_dict(m) for m in media_dicts]
            
            logger.info(f"Listed {len(media_list)} media records")
            return True, media_list, f"Found {len(media_list)} media records"

        except Exception as e:
            logger.error(f"Error listing media: {e}")
            return False, [], str(e)

    def list_media_by_status(self, status: str) -> Tuple[bool, List[Media], str]:
        """
        Retrieve media records by status.
        
        Args:
            status: Status to filter by (pending/processing/done/error)
            
        Returns:
            Tuple of (success: bool, media_list: List[Media], message: str)
        """
        try:
            # Validate status
            valid_statuses = [s.value for s in MediaStatus]
            if status not in valid_statuses:
                return False, [], f"Invalid status: {status}"

            media_dicts = self.db.query_by_status(status)
            media_list = [Media.from_dict(m) for m in media_dicts]
            
            logger.info(f"Listed {len(media_list)} media records with status: {status}")
            return True, media_list, f"Found {len(media_list)} media records"

        except Exception as e:
            logger.error(f"Error listing media by status: {e}")
            return False, [], str(e)

    def list_media_by_uploader(self, uploader: str) -> Tuple[bool, List[Media], str]:
        """
        Retrieve media records by uploader.
        
        Args:
            uploader: Uploader name to filter by
            
        Returns:
            Tuple of (success: bool, media_list: List[Media], message: str)
        """
        try:
            media_dicts = self.db.query_by_uploader(uploader)
            media_list = [Media.from_dict(m) for m in media_dicts]
            
            logger.info(f"Listed {len(media_list)} media records for uploader: {uploader}")
            return True, media_list, f"Found {len(media_list)} media records"

        except Exception as e:
            logger.error(f"Error listing media by uploader: {e}")
            return False, [], str(e)

    def update_media_status(self, media_id: str, status: str) -> Tuple[bool, str]:
        """
        Update media processing status.
        
        Args:
            media_id: ID of the media
            status: New status (pending/processing/done/error)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate status
            valid_statuses = [s.value for s in MediaStatus]
            if status not in valid_statuses:
                return False, f"Invalid status: {status}"

            # Update in database
            success = self.db.update_item(media_id, {'status': status})
            
            if success:
                logger.info(f"Updated media status: {media_id} -> {status}")
                return True, f"Status updated to {status}"
            else:
                return False, f"Media not found: {media_id}"

        except Exception as e:
            logger.error(f"Error updating media status: {e}")
            return False, str(e)

    def update_media_processing(self, media_id: str, 
                                thumbnail_key: Optional[str] = None,
                                error_message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update media after processing.
        
        Args:
            media_id: ID of the media
            thumbnail_key: S3 key of thumbnail (if successful)
            error_message: Error message (if failed)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            updates = {}
            
            if error_message:
                updates['status'] = MediaStatus.ERROR.value
                updates['error_message'] = error_message
                logger.warning(f"Media processing failed: {media_id} - {error_message}")
            else:
                updates['status'] = MediaStatus.DONE.value
                if thumbnail_key:
                    updates['thumbnail_key'] = thumbnail_key
                logger.info(f"Media processing completed: {media_id}")

            success = self.db.update_item(media_id, updates)
            
            if success:
                return True, "Media processing updated"
            else:
                return False, f"Media not found: {media_id}"

        except Exception as e:
            logger.error(f"Error updating media processing: {e}")
            return False, str(e)

    def delete_media(self, media_id: str) -> Tuple[bool, str]:
        """
        Delete a media record.
        
        Args:
            media_id: ID of the media
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            success = self.db.delete_item(media_id)
            
            if success:
                logger.info(f"Deleted media: {media_id}")
                return True, "Media deleted"
            else:
                return False, f"Media not found: {media_id}"

        except Exception as e:
            logger.error(f"Error deleting media: {e}")
            return False, str(e)

    def get_statistics(self) -> Dict:
        """
        Get system statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            all_media = self.db.scan()
            
            stats = {
                'total_media': len(all_media),
                'pending': len([m for m in all_media if m['status'] == MediaStatus.PENDING.value]),
                'processing': len([m for m in all_media if m['status'] == MediaStatus.PROCESSING.value]),
                'done': len([m for m in all_media if m['status'] == MediaStatus.DONE.value]),
                'error': len([m for m in all_media if m['status'] == MediaStatus.ERROR.value]),
                'total_size_bytes': sum([m.get('file_size', 0) for m in all_media])
            }
            
            logger.info(f"Statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def health_check(self) -> bool:
        """Check if service is healthy."""
        try:
            # Try to scan database
            self.db.scan()
            logger.info("Health check passed")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
