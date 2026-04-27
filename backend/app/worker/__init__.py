"""
Worker Package — Asynchronous Media Processing
Group A — Media Sharing Platform
Worker/Processor Developer: DMPT Dissanayake

This package implements the background worker that:
  - Consumes messages from the SQS queue
  - Generates thumbnails for uploaded media
  - Uploads processed files to storage (S3)
  - Updates database status
  - Handles failures with retry mechanisms
"""

from .worker import MediaWorker
from .processor import generate_thumbnail
from .storage import MockS3Storage

__all__ = [
    'MediaWorker',
    'generate_thumbnail',
    'MockS3Storage'
]
