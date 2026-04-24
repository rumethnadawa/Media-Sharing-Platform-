"""
Custom exceptions for the application
"""


class MediaError(Exception):
    """Base exception for media operations."""
    pass


class MediaNotFoundError(MediaError):
    """Raised when a media record is not found."""
    pass


class InvalidMediaError(MediaError):
    """Raised when media data is invalid."""
    pass


class DatabaseError(MediaError):
    """Raised when database operation fails."""
    pass


class ValidationError(MediaError):
    """Raised when validation fails."""
    pass


class ProcessingError(MediaError):
    """Raised when media processing fails."""
    pass
