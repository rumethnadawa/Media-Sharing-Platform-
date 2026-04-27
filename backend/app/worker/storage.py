"""
Mock S3 Storage — Local File Storage Simulation
Group A — Media Sharing Platform
Worker/Processor Developer: DMPT Dissanayake

This module provides a local filesystem-based simulation of AWS S3.
It implements the same operations the worker needs (download, upload,
exists) so the processing pipeline can run end-to-end without a real
AWS account.

In production, replace MockS3Storage with a real boto3 S3 client wrapper
that exposes the same interface.
"""

import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MockS3Storage:
    """
    Local file-system simulation of AWS S3 for development and testing.

    Directory layout mirrors S3 bucket structure:
        <base_dir>/
        ├── uploads/          ← original uploaded files
        │   └── <media_id>.<ext>
        └── thumbnails/       ← generated thumbnails
            └── <media_id>_thumb.jpg
    """

    def __init__(self, base_dir: str = "worker_storage"):
        """
        Initialize mock S3 storage.

        Args:
            base_dir: Root directory for the local file store
        """
        self.base_dir = base_dir
        self._ensure_structure()
        logger.info(f"MockS3Storage initialized at: {os.path.abspath(base_dir)}")

    def _ensure_structure(self):
        """Create the directory structure if it doesn't exist."""
        os.makedirs(os.path.join(self.base_dir, "uploads"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "thumbnails"), exist_ok=True)

    # ------------------------------------------------------------------
    #  DOWNLOAD (S3 → local)
    # ------------------------------------------------------------------

    def download_file(self, object_key: str, local_path: str) -> bool:
        """
        Simulate downloading a file from S3 to a local path.

        In real AWS this would call s3.download_file(bucket, key, path).
        Here we copy from our local store if the file exists.

        Args:
            object_key: S3-style key (e.g. 'uploads/abc123.mp4')
            local_path: Destination path on the local filesystem

        Returns:
            True if the file was copied, False if the source doesn't exist
        """
        try:
            # Strip s3://bucket/ prefix if present
            clean_key = self._clean_key(object_key)
            source = os.path.join(self.base_dir, clean_key)

            if os.path.exists(source):
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                shutil.copy2(source, local_path)
                logger.info(f"Downloaded (mock): {object_key} → {local_path}")
                return True
            else:
                logger.warning(
                    f"Source file not found in mock storage: {source}. "
                    f"This is expected in simulation mode."
                )
                return False

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    # ------------------------------------------------------------------
    #  UPLOAD (local → S3)
    # ------------------------------------------------------------------

    def upload_file(self, local_path: str, object_key: str) -> Optional[str]:
        """
        Simulate uploading a file from the local filesystem to S3.

        In real AWS this would call s3.upload_file(path, bucket, key).
        Here we copy the file into our local store.

        Args:
            local_path:  Source path on the local filesystem
            object_key:  S3-style destination key (e.g. 'thumbnails/abc_thumb.jpg')

        Returns:
            The full S3-style URI (s3://bucket/key) on success, or None on failure
        """
        try:
            clean_key = self._clean_key(object_key)
            destination = os.path.join(self.base_dir, clean_key)

            os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
            shutil.copy2(local_path, destination)

            s3_uri = f"s3://media-sharing-bucket/{clean_key}"
            logger.info(f"Uploaded (mock): {local_path} → {s3_uri}")
            return s3_uri

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    # ------------------------------------------------------------------
    #  UTILITY
    # ------------------------------------------------------------------

    def file_exists(self, object_key: str) -> bool:
        """
        Check whether a file exists in the mock store.

        Args:
            object_key: S3-style key

        Returns:
            True if the file exists locally
        """
        clean_key = self._clean_key(object_key)
        return os.path.exists(os.path.join(self.base_dir, clean_key))

    def get_local_path(self, object_key: str) -> str:
        """
        Return the absolute local path corresponding to an S3 key.

        Args:
            object_key: S3-style key

        Returns:
            Absolute path in the local store
        """
        clean_key = self._clean_key(object_key)
        return os.path.abspath(os.path.join(self.base_dir, clean_key))

    def list_files(self, prefix: str = "") -> list:
        """
        List all files in the mock store, optionally filtered by prefix.

        Args:
            prefix: Key prefix to filter by (e.g. 'thumbnails/')

        Returns:
            List of relative key paths
        """
        results = []
        search_dir = os.path.join(self.base_dir, prefix)

        if not os.path.exists(search_dir):
            return results

        for root, _, files in os.walk(search_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, self.base_dir).replace("\\", "/")
                results.append(rel)

        return results

    def clear(self):
        """Remove all files from the mock store (for testing)."""
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
        self._ensure_structure()
        logger.info("MockS3Storage cleared")

    @staticmethod
    def _clean_key(object_key: str) -> str:
        """
        Strip the s3://bucket/ prefix from an object key if present.

        Examples:
            's3://media-sharing-bucket/uploads/abc.jpg' → 'uploads/abc.jpg'
            'uploads/abc.jpg'                           → 'uploads/abc.jpg'
        """
        if object_key.startswith("s3://"):
            # Remove 's3://' and the bucket name
            parts = object_key[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else ""
        return object_key
