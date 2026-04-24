"""
Media Data Model
Group A - Media Sharing Platform
Backend Developer: PHDB Nayanakantha

This module defines the Media data model with all required fields for
the media sharing system.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class MediaStatus(Enum):
    """Media processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Media:
    """
    Media data model representing a media file record.
    
    Fields:
        media_id: Unique identifier (UUID)
        title: Title of the media file
        uploader: Name of the uploader
        object_key: S3 object key/path for the media file
        status: Current processing status
        thumbnail_key: S3 object key for the thumbnail (if generated)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
        file_size: Size of the media file in bytes
        media_type: Type of media (image/video)
        description: Optional description of the media
        error_message: Error message if processing failed
    """
    
    media_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    uploader: str = ""
    object_key: str = ""
    status: str = field(default=MediaStatus.PENDING.value)
    thumbnail_key: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    file_size: int = 0
    media_type: str = ""
    description: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate media object after initialization."""
        if not self.media_id:
            self.media_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        self.update_timestamp()

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """
        Convert Media object to dictionary.
        
        Returns:
            Dictionary representation of the Media object
        """
        return {
            'media_id': self.media_id,
            'title': self.title,
            'uploader': self.uploader,
            'object_key': self.object_key,
            'status': self.status,
            'thumbnail_key': self.thumbnail_key,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'file_size': self.file_size,
            'media_type': self.media_type,
            'description': self.description,
            'error_message': self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Media':
        """
        Create Media object from dictionary.
        
        Args:
            data: Dictionary containing media data
            
        Returns:
            Media object
        """
        return cls(
            media_id=data.get('media_id', str(uuid.uuid4())),
            title=data.get('title', ''),
            uploader=data.get('uploader', ''),
            object_key=data.get('object_key', ''),
            status=data.get('status', MediaStatus.PENDING.value),
            thumbnail_key=data.get('thumbnail_key'),
            created_at=data.get('created_at', datetime.utcnow().isoformat()),
            updated_at=data.get('updated_at', datetime.utcnow().isoformat()),
            file_size=data.get('file_size', 0),
            media_type=data.get('media_type', ''),
            description=data.get('description'),
            error_message=data.get('error_message')
        )

    def mark_processing(self):
        """Mark media as being processed."""
        self.status = MediaStatus.PROCESSING.value
        self.update_timestamp()

    def mark_done(self, thumbnail_key: str = None):
        """Mark media as successfully processed."""
        self.status = MediaStatus.DONE.value
        if thumbnail_key:
            self.thumbnail_key = thumbnail_key
        self.error_message = None
        self.update_timestamp()

    def mark_error(self, error_msg: str):
        """Mark media as failed with error message."""
        self.status = MediaStatus.ERROR.value
        self.error_message = error_msg
        self.update_timestamp()

    def is_pending(self) -> bool:
        """Check if media is in pending state."""
        return self.status == MediaStatus.PENDING.value

    def is_processing(self) -> bool:
        """Check if media is being processed."""
        return self.status == MediaStatus.PROCESSING.value

    def is_done(self) -> bool:
        """Check if media processing is complete."""
        return self.status == MediaStatus.DONE.value

    def is_error(self) -> bool:
        """Check if media processing failed."""
        return self.status == MediaStatus.ERROR.value

    def __str__(self) -> str:
        """String representation of Media object."""
        return f"Media(id={self.media_id}, title={self.title}, status={self.status})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()
