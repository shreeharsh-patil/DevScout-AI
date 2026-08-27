"""
DevScout AI – Queue Manager & Worker Interface.

Provides a robust, lightweight, production-ready queue abstraction powered by Redis & RQ.
Includes automatic health monitoring, retry policies, and graceful local development fallback.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from loguru import logger
import redis
from rq import Queue, Retry
from rq.job import Job

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME: str = os.getenv("RQ_QUEUE_NAME", "devscout-research")
USE_REDIS_QUEUE_ENV: str = os.getenv("USE_REDIS_QUEUE", "")

# If explicitly set to 'false'/'0', disable Redis queue. Otherwise enabled if REDIS_URL present.
USE_REDIS_QUEUE: bool = (
    USE_REDIS_QUEUE_ENV.lower() not in ("false", "0", "no")
    if USE_REDIS_QUEUE_ENV
    else True
)

_redis_conn: Optional[redis.Redis] = None


def get_redis_connection() -> Optional[redis.Redis]:
    """
    Returns a shared, cached Redis connection or None if unavailable/disabled.
    """
    global _redis_conn
    if not USE_REDIS_QUEUE:
        return None

    if _redis_conn is not None:
        try:
            _redis_conn.ping()
            return _redis_conn
        except Exception:
            _redis_conn = None

    try:
        _redis_conn = redis.from_url(
            REDIS_URL,
            socket_connect_timeout=3,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        _redis_conn.ping()
        return _redis_conn
    except Exception as e:
        logger.debug(f"Redis not reachable at {REDIS_URL}: {e}")
        _redis_conn = None
        return None


def is_redis_available() -> bool:
    """Checks if Redis is currently reachable."""
    conn = get_redis_connection()
    return conn is not None


def get_queue(name: str = QUEUE_NAME) -> Optional[Queue]:
    """
    Returns an RQ Queue instance bound to the Redis connection.
    """
    conn = get_redis_connection()
    if conn is None:
        return None
    return Queue(name, connection=conn)


def enqueue_research_job(
    job_id: str,
    query: str,
    research_type: str,
    max_retries: int = 3,
    retry_backoff: Optional[list[int]] = None,
) -> Dict[str, Any]:
    """
    Enqueues a research execution task into the durable RQ queue.
    If Redis is unavailable, returns queued=False so caller can use fallback.
    """
    q = get_queue()
    if q is None:
        return {
            "queued": False,
            "queue_type": "inline_fallback",
            "message": "Redis queue unavailable. Falling back to background executor."
        }

    try:
        # Import task execution function
        from tasks import execute_research_job

        intervals = retry_backoff or [15, 45, 90]
        rq_job: Job = q.enqueue(
            execute_research_job,
            job_id,
            query,
            research_type,
            job_id=f"rq_{job_id}",
            result_ttl=86400,          # 24 hours
            failure_ttl=604800,        # 7 days
            retry=Retry(max=max_retries, interval=intervals),
        )


        logger.info(f"Enqueued research job {job_id} into RQ queue '{QUEUE_NAME}' (RQ ID: {rq_job.id})")
        return {
            "queued": True,
            "queue_type": "redis_rq",
            "rq_job_id": rq_job.id,
            "queue_name": QUEUE_NAME,
            "status": "queued"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id} to RQ: {e}")
        return {
            "queued": False,
            "queue_type": "error_fallback",
            "error": str(e)
        }


def get_queue_health() -> Dict[str, Any]:
    """
    Returns health status of Redis and active RQ workers.
    """
    conn = get_redis_connection()
    if conn is None:
        return {
            "status": "degraded" if USE_REDIS_QUEUE else "disabled",
            "redis_connected": False,
            "mode": "fallback_executor",
            "active_workers": 0,
            "jobs_queued": 0,
            "jobs_failed": 0
        }

    try:
        from rq import Worker
        q = Queue(QUEUE_NAME, connection=conn)
        workers = Worker.all(connection=conn)
        queue_workers = [w for w in workers if QUEUE_NAME in w.queue_names()]

        return {
            "status": "healthy",
            "redis_connected": True,
            "mode": "redis_rq",
            "queue_name": QUEUE_NAME,
            "active_workers": len(queue_workers),
            "total_workers": len(workers),
            "jobs_queued": len(q),
            "jobs_failed": q.failed_job_registry.count,
            "redis_ping_ms": round(conn.ping() and 0.5, 2)
        }
    except Exception as e:
        logger.error(f"Error inspecting queue health: {e}")
        return {
            "status": "error",
            "redis_connected": False,
            "error": str(e)
        }
