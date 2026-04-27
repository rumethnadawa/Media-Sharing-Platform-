#!/usr/bin/env python3
"""
Worker Entry Point — Run the Media Worker Standalone
Group A — Media Sharing Platform
Worker/Processor Developer: DMPT Dissanayake

Usage:
    cd backend
    python -m app.worker.run_worker

This script initialises all dependencies (database, service, queue,
storage) and starts the MediaWorker polling loop.

Environment variables (optional):
    DB_FILE          — Path to the JSON database file (default: media_db.json)
    WORKER_CYCLES    — Number of poll cycles to run (default: unlimited)
    LOG_LEVEL        — Logging level (default: INFO)
"""

import sys
import os
import logging

# Add backend root to path so 'app' package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database import MockDynamoDB
from app.services import MediaService
from app.utils import MockSQS
from app.worker.storage import MockS3Storage
from app.worker.worker import MediaWorker
from app.config import (
    DB_FILE, LOG_LEVEL, LOG_FORMAT,
    MAX_RETRIES, RETRY_DELAY, QUEUE_POLL_INTERVAL, THUMBNAIL_SIZE
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


def main():
    """Initialise components and start the worker."""

    print("=" * 60)
    print("  Media Sharing Platform — Worker / Processor")
    print("  Developer: DMPT Dissanayake")
    print("=" * 60)

    # Read configuration from environment
    db_file = os.getenv('DB_FILE', DB_FILE)
    max_cycles_env = os.getenv('WORKER_CYCLES')
    max_cycles = int(max_cycles_env) if max_cycles_env else None

    # Initialise database
    logger.info(f"Database file: {db_file}")
    db = MockDynamoDB(storage_file=db_file)

    # Initialise service
    service = MediaService(db)

    # Initialise queue
    queue = MockSQS()

    # Initialise mock storage
    storage = MockS3Storage(base_dir="worker_storage")

    # Create and start worker
    worker = MediaWorker(
        service=service,
        queue=queue,
        storage=storage,
        max_retries=MAX_RETRIES,
        retry_delay=RETRY_DELAY,
        poll_interval=QUEUE_POLL_INTERVAL,
        thumbnail_size=THUMBNAIL_SIZE,
        use_placeholder=True  # Use placeholders in local mode
    )

    print(f"\nWorker configuration:")
    print(f"  Max retries:    {MAX_RETRIES}")
    print(f"  Retry delay:    {RETRY_DELAY}s")
    print(f"  Poll interval:  {QUEUE_POLL_INTERVAL}s")
    print(f"  Thumbnail size: {THUMBNAIL_SIZE}")

    if max_cycles:
        print(f"  Max cycles:     {max_cycles}")
    else:
        print(f"  Max cycles:     unlimited (Ctrl+C to stop)")

    print(f"\nListening for messages...\n")

    try:
        worker.start(max_cycles=max_cycles)
    except KeyboardInterrupt:
        print("\n\nShutting down worker...")
        worker.stop()

    # Print final stats
    stats = worker.stats
    print(f"\n{'=' * 60}")
    print(f"  Worker Summary")
    print(f"  Processed: {stats['processed']}")
    print(f"  Errors:    {stats['errors']}")
    print(f"  Total:     {stats['total']}")
    print(f"{'=' * 60}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
