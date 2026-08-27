"""
DevScout AI – Standalone Research Worker.

Runs in a separate process in production (e.g. Render / Railway background worker service),
listening on the Redis RQ queue for long-running research jobs.

Usage:
    python worker.py
    # or
    python -m worker
    # or using the RQ CLI:
    rq worker devscout-research --url redis://localhost:6379/0
"""

import os
import sys
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from queue_manager import get_redis_connection, QUEUE_NAME, REDIS_URL
from database import ensure_tables


def start_worker():
    """Starts the RQ worker process."""
    logger.info("Initializing DevScout AI Research Worker...")
    ensure_tables()

    conn = get_redis_connection()
    if conn is None:
        logger.error(
            f"Cannot start worker: Redis is unreachable at '{REDIS_URL}'. "
            "Please ensure Redis is running and REDIS_URL is correctly configured."
        )
        sys.exit(1)

    from rq import Worker, Queue

    queues = [Queue(QUEUE_NAME, connection=conn)]
    worker = Worker(queues, connection=conn, name=f"devscout-worker-{os.getpid()}")

    logger.info(f"DevScout AI Worker '{worker.name}' active and listening on queue: '{QUEUE_NAME}'")
    logger.info(f"Connected to Redis at: {REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL}")

    # Start listening for jobs
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    start_worker()
