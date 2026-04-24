"""
Validators for input validation
"""

import uuid
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def validate_media_id(media_id: str) -> Tuple[bool, str]:
    """
    Validate media ID format.
    
    Args:
        media_id: Media ID to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not media_id:
        return False, "Media ID cannot be empty"
    
    if not isinstance(media_id, str):
        return False, "Media ID must be a string"
    
    # Optionally validate UUID format
    try:
        uuid.UUID(media_id)
    except ValueError:
        return False, "Media ID must be a valid UUID"
    
    return True, ""


def validate_media_input(title: str, uploader: str, object_key: str, 
                        file_size: int, media_type: str) -> Tuple[bool, str]:
    """
    Validate media creation input.
    
    Args:
        title: Media title
        uploader: Uploader name
        object_key: S3 object key
        file_size: File size in bytes
        media_type: Media type (image/video)
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not title or not isinstance(title, str):
        return False, "Title must be a non-empty string"
    
    if len(title) > 255:
        return False, "Title must be less than 255 characters"
    
    if not uploader or not isinstance(uploader, str):
        return False, "Uploader must be a non-empty string"
    
    if len(uploader) > 255:
        return False, "Uploader name must be less than 255 characters"
    
    if not object_key or not isinstance(object_key, str):
        return False, "Object key must be a non-empty string"
    
    if file_size <= 0:
        return False, "File size must be greater than 0"
    
    # Check for maximum file size (e.g., 5GB)
    max_size = 5 * 1024 * 1024 * 1024  # 5GB
    if file_size > max_size:
        return False, f"File size exceeds maximum limit of {max_size} bytes"
    
    valid_types = ['image', 'video']
    if media_type not in valid_types:
        return False, f"Media type must be one of {valid_types}"
    
    return True, ""


def validate_status(status: str) -> Tuple[bool, str]:
    """
    Validate status value.
    
    Args:
        status: Status to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    valid_statuses = ['pending', 'processing', 'done', 'error']
    
    if status not in valid_statuses:
        return False, f"Status must be one of {valid_statuses}"
    
    return True, ""
