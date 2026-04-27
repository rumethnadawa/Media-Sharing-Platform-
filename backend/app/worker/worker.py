"""
Media Worker — Core Asynchronous Processing Engine
Group A — Media Sharing Platform
Worker/Processor Developer: DMPT Dissanayake

This module implements the MediaWorker class which:
  1. Polls the SQS queue for new processing jobs
  2. Downloads the media file from S3
  3. Generates a thumbnail (image or video)
  4. Uploads the thumbnail back to S3
  5. Updates the database record (status + thumbnail_key)
  6. Deletes the message from the queue on success
  7. Retries on failure up to MAX_RETRIES times
  8. Records error state after all retries are exhausted
"""

import json
import os
import time
import tempfile
import logging
from typing import Optional, Dict

from app.services import MediaService
from app.utils import MockSQS
from app.config import (
    MAX_RETRIES,
    RETRY_DELAY,
    QUEUE_POLL_INTERVAL,
    THUMBNAIL_SIZE,
    PROCESSING_TIMEOUT
)
from app.worker.processor import generate_thumbnail
from app.worker.storage import MockS3Storage

logger = logging.getLogger(__name__)


class MediaWorker:
    """
    Background worker that consumes messages from the queue and
    processes media files (thumbnail generation).

    Usage:
        worker = MediaWorker(service, queue, storage)
        worker.start()          # blocking — runs until stop() is called
        worker.stop()           # graceful shutdown

        # Or run a single poll cycle (useful for testing):
        worker.poll_and_process()
    """

    def __init__(self, service: MediaService, queue: MockSQS,
                 storage: MockS3Storage,
                 max_retries: int = MAX_RETRIES,
                 retry_delay: int = RETRY_DELAY,
                 poll_interval: int = QUEUE_POLL_INTERVAL,
                 thumbnail_size: tuple = THUMBNAIL_SIZE,
                 use_placeholder: bool = True):
        """
        Initialize the MediaWorker.

        Args:
            service:         MediaService instance for database operations
            queue:           MockSQS instance for message consumption
            storage:         MockS3Storage instance for file operations
            max_retries:     Maximum retry attempts per message
            retry_delay:     Seconds to wait between retries
            poll_interval:   Seconds between queue polls
            thumbnail_size:  (width, height) for generated thumbnails
            use_placeholder: If True, generate placeholder thumbnails
                             when real files are unavailable
        """
        self.service = service
        self.queue = queue
        self.storage = storage
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.poll_interval = poll_interval
        self.thumbnail_size = thumbnail_size
        self.use_placeholder = use_placeholder

        self._running = False
        self._processed_count = 0
        self._error_count = 0

        logger.info(
            f"MediaWorker initialized  "
            f"[retries={max_retries}, delay={retry_delay}s, "
            f"poll={poll_interval}s, thumb={thumbnail_size}]"
        )

    # ------------------------------------------------------------------
    #  PUBLIC API
    # ------------------------------------------------------------------

    def start(self, max_cycles: Optional[int] = None):
        """
        Start the worker polling loop.

        This is a **blocking** call. It will keep polling the queue until
        `stop()` is called or `max_cycles` iterations have been completed.

        Args:
            max_cycles: If set, stop after this many poll iterations
                        (useful for testing). None = run forever.
        """
        self._running = True
        cycle = 0
        logger.info("Worker started — listening for messages...")

        try:
            while self._running:
                self.poll_and_process()
                cycle += 1

                if max_cycles is not None and cycle >= max_cycles:
                    logger.info(f"Reached max_cycles ({max_cycles}), stopping.")
                    break

                if self._running and self.queue.get_queue_size() == 0:
                    # No messages — wait before polling again
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Worker interrupted by user (Ctrl+C)")
        finally:
            self._running = False
            logger.info(
                f"Worker stopped.  Processed: {self._processed_count}  "
                f"Errors: {self._error_count}"
            )

    def stop(self):
        """Signal the worker to stop after the current cycle."""
        logger.info("Worker stop requested")
        self._running = False

    def poll_and_process(self):
        """
        Execute one poll cycle:
          1. Receive messages from the queue (up to 1)
          2. Process each message

        This is the method to call if you want to drive the worker
        manually (e.g. in tests) rather than using start().
        """
        messages = self.queue.receive_messages(max_number=1)

        if not messages:
            logger.debug("No messages in queue")
            return

        for message in messages:
            self.process_message(message)

    def process_message(self, message: Dict):
        """
        Full processing pipeline for a single queue message.

        Steps:
            1. Parse message body (media_id, object_key, action)
            2. Update database status → 'processing'
            3. Download file from S3
            4. Generate thumbnail
            5. Upload thumbnail to S3
            6. Update database → 'done' + thumbnail_key
            7. Delete message from queue

        On failure, retries up to max_retries times. After exhausting
        retries, marks the media as 'error' in the database.

        Args:
            message: Queue message dict with 'Body', 'MessageId', etc.
        """
        try:
            body = json.loads(message['Body'])
            media_id = body.get('media_id')
            object_key = body.get('object_key', '')
            action = body.get('action', 'generate_thumbnail')
            message_id = message.get('MessageId', 'unknown')

            logger.info(
                f"Processing message {message_id}: "
                f"media_id={media_id}, action={action}"
            )

            if not media_id:
                logger.error("Message has no media_id — skipping")
                self.queue.delete_message(message_id)
                return

            # Step 1: Mark as processing
            success, msg = self.service.update_media_status(media_id, 'processing')
            if not success:
                logger.error(f"Failed to mark media as processing: {msg}")
                # Don't process if we can't update status
                self._handle_failure(
                    media_id, f"Cannot update status: {msg}", message, attempt=self.max_retries
                )
                return

            logger.info(f"[{media_id}] Status → processing")

            # Step 2–5: Download → Thumbnail → Upload (with retries)
            last_error = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    thumbnail_key = self._do_processing(media_id, object_key)
                    # Success!
                    self._handle_success(media_id, thumbnail_key, message_id)
                    return

                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"[{media_id}] Attempt {attempt}/{self.max_retries} failed: {e}"
                    )

                    if attempt < self.max_retries:
                        logger.info(
                            f"[{media_id}] Retrying in {self.retry_delay}s..."
                        )
                        time.sleep(self.retry_delay)

            # All retries exhausted
            self._handle_failure(media_id, last_error, message, attempt=self.max_retries)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid message body (not JSON): {e}")
            # Remove the bad message so it doesn't block the queue
            self.queue.delete_message(message.get('MessageId', ''))
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}")

    # ------------------------------------------------------------------
    #  INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _do_processing(self, media_id: str, object_key: str) -> str:
        """
        Core processing logic: download → generate thumbnail → upload.

        Args:
            media_id:   The media record ID
            object_key: S3 key of the original media file

        Returns:
            The S3 URI of the uploaded thumbnail

        Raises:
            Exception: If any step fails
        """
        # Create a temp directory for this processing job
        with tempfile.TemporaryDirectory(prefix=f"worker_{media_id[:8]}_") as tmpdir:
            local_media_path = os.path.join(tmpdir, f"{media_id}_original")
            local_thumb_path = os.path.join(tmpdir, f"{media_id}_thumb.jpg")

            # Determine media type from the object key
            media_type = self._detect_media_type(object_key)

            # Step 2: Download from S3
            logger.info(f"[{media_id}] Downloading from storage: {object_key}")
            downloaded = self.storage.download_file(object_key, local_media_path)

            # Step 3: Generate thumbnail
            logger.info(f"[{media_id}] Generating {media_type} thumbnail...")
            use_placeholder = self.use_placeholder or not downloaded

            success = generate_thumbnail(
                input_path=local_media_path,
                output_path=local_thumb_path,
                media_type=media_type,
                media_id=media_id,
                size=self.thumbnail_size,
                use_placeholder=use_placeholder
            )

            if not success:
                raise Exception(f"Thumbnail generation failed for {media_id}")

            # Step 4: Upload thumbnail to S3
            thumbnail_s3_key = f"thumbnails/{media_id}_thumb.jpg"
            logger.info(f"[{media_id}] Uploading thumbnail: {thumbnail_s3_key}")

            s3_uri = self.storage.upload_file(local_thumb_path, thumbnail_s3_key)

            if not s3_uri:
                raise Exception(f"Thumbnail upload failed for {media_id}")

            return s3_uri

    def _handle_success(self, media_id: str, thumbnail_key: str, message_id: str):
        """
        Handle successful processing: update DB and delete queue message.

        Args:
            media_id:      The media record ID
            thumbnail_key: S3 URI of the generated thumbnail
            message_id:    Queue message ID to delete
        """
        # Update database: status → done, set thumbnail_key
        success, msg = self.service.update_media_processing(
            media_id,
            thumbnail_key=thumbnail_key
        )

        if success:
            logger.info(f"[{media_id}] ✓ Processing complete — thumbnail: {thumbnail_key}")
        else:
            logger.error(f"[{media_id}] DB update failed after processing: {msg}")

        # Delete message from queue
        self.queue.delete_message(message_id)
        logger.info(f"[{media_id}] Message {message_id} deleted from queue")

        self._processed_count += 1

    def _handle_failure(self, media_id: str, error_msg: str,
                        message: Dict, attempt: int):
        """
        Handle processing failure: update DB with error and optionally
        remove the message.

        In production, failed messages would go to a Dead Letter Queue
        (DLQ). In this mock implementation, we delete the message after
        recording the error.

        Args:
            media_id:  The media record ID
            error_msg: Description of the failure
            message:   The original queue message
            attempt:   Which attempt number this failure occurred on
        """
        full_error = f"Processing failed after {attempt} attempt(s): {error_msg}"

        # Update database: status → error, set error_message
        success, msg = self.service.update_media_processing(
            media_id,
            error_message=full_error
        )

        if success:
            logger.error(f"[{media_id}] ✗ {full_error}")
        else:
            logger.error(
                f"[{media_id}] ✗ Processing AND DB update failed: {msg}"
            )

        # In production: leave message for DLQ. Here: delete to unblock queue.
        message_id = message.get('MessageId', '')
        if message_id:
            self.queue.delete_message(message_id)
            logger.info(f"[{media_id}] Failed message {message_id} removed from queue")

        self._error_count += 1

    @staticmethod
    def _detect_media_type(object_key: str) -> str:
        """
        Detect whether the media is an image or video based on the
        file extension in the S3 key.

        Args:
            object_key: S3-style key (e.g. 'uploads/video.mp4')

        Returns:
            'image' or 'video'
        """
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}

        ext = os.path.splitext(object_key.lower())[1]

        if ext in image_exts:
            return "image"
        elif ext in video_exts:
            return "video"
        else:
            logger.warning(f"Unknown extension '{ext}', defaulting to 'image'")
            return "image"

    # ------------------------------------------------------------------
    #  STATS
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        """Return worker processing statistics."""
        return {
            'processed': self._processed_count,
            'errors': self._error_count,
            'total': self._processed_count + self._error_count,
            'running': self._running,
            'queue_size': self.queue.get_queue_size()
        }
