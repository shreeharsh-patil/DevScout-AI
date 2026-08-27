"""
DevScout AI – Background & Worker Research Execution Tasks.

Provides the durable worker execution routine with atomic duplicate execution prevention,
incremental stage reporting, automatic retry policies, and safe error capture.
"""

from __future__ import annotations

import datetime
import json
from typing import Dict, Any
from loguru import logger

from database import Report, SessionLocal
from agents.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()


class RateLimitError(Exception):
    """Raised when Gemini or downstream API rate limits are encountered for worker retry."""
    pass


def execute_research_job(job_id: str, query: str, research_type: str) -> Dict[str, Any]:
    """
    Executes a research job with durable state tracking and duplicate execution prevention.
    
    Status cycle:
      queued -> researching -> analyzing -> reporting -> completed
      (or failed / rate_limited on error)
    """
    logger.info(f"[Worker] Picking up job {job_id} ({research_type}: '{query}')")
    db = SessionLocal()

    try:
        job = db.query(Report).filter(Report.job_id == job_id).first()
        if not job:
            logger.error(f"[Worker] Job record {job_id} not found in database.")
            return {"status": "error", "message": "Job record not found"}

        # ------------------------------------------------------------------
        # 1. Duplicate Execution Prevention
        # ------------------------------------------------------------------
        if job.status == "completed":
            logger.warning(f"[Worker] Job {job_id} is already completed. Skipping duplicate run.")
            return {"status": "skipped", "message": "Job already completed"}

        now = datetime.datetime.now(datetime.timezone.utc)
        if job.status == "processing" and job.updated_at:
            elapsed_seconds = (now - job.updated_at).total_seconds()
            # If job was updated less than 30 seconds ago by another active worker
            if elapsed_seconds < 30:
                logger.warning(f"[Worker] Job {job_id} is already being processed by another worker ({elapsed_seconds:.1f}s ago). Skipping.")
                return {"status": "skipped", "message": "Job currently active"}

        # Mark job as processing
        job.status = "processing"
        job.stage = "researching"
        job.error_message = None
        job.updated_at = now
        db.commit()

        # ------------------------------------------------------------------
        # 2. Stage Change Listener for Real-time Progress
        # ------------------------------------------------------------------
        def _update_stage(stage: str):
            stage_db = SessionLocal()
            try:
                cur_job = stage_db.query(Report).filter(Report.job_id == job_id).first()
                if cur_job:
                    cur_job.stage = stage
                    cur_job.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    stage_db.commit()
                    logger.info(f"[Worker] Job {job_id} progressed to stage: '{stage}'")
            except Exception as ex:
                logger.warning(f"[Worker] Failed to update stage for job {job_id}: {ex}")
            finally:
                stage_db.close()

        # ------------------------------------------------------------------
        # 3. Lookup Historical Research Snapshot (Same Workspace & Query)
        # ------------------------------------------------------------------
        prev_raw = None
        prev_job_id = None
        prev_created_at = None
        try:
            prev_job = (
                db.query(Report)
                .filter(
                    Report.workspace_id == job.workspace_id,
                    Report.query == query,
                    Report.job_id != job_id,
                    Report.status == "completed"
                )
                .order_by(Report.created_at.desc())
                .first()
            )
            if prev_job and prev_job.raw_data:
                prev_raw = json.loads(prev_job.raw_data)
                prev_job_id = prev_job.job_id
                prev_created_at = prev_job.created_at.isoformat() if prev_job.created_at else None
        except Exception as ex:
            logger.debug(f"[Worker] Previous snapshot lookup exception: {ex}")

        # ------------------------------------------------------------------
        # 4. Execute Multi-Agent Pipeline
        # ------------------------------------------------------------------
        result = orchestrator.run_pipeline(
            query=query,
            research_type=research_type,
            depth="standard",
            on_stage_change=_update_stage,
            previous_data=prev_raw,
            previous_job_id=prev_job_id,
            previous_created_at=prev_created_at
        )

        # Refresh job instance
        job = db.query(Report).filter(Report.job_id == job_id).first()
        if not job:
            return {"status": "error", "message": "Job disappeared during execution"}


        if result.get("status") == "completed":
            job.status = "completed"
            job.stage = "completed"
            job.report_markdown = result.get("report", "")
            try:
                job.raw_data = json.dumps({
                    "researcher": result.get("raw_data"),
                    "analysis": result.get("analysis")
                })
                job.sources = json.dumps(result.get("sources", []))
            except (TypeError, ValueError) as exc:
                raise ValueError("Research pipeline produced non-serializable data") from exc
            job.error_message = None
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            logger.info(f"[Worker] Job {job_id} successfully completed with {len(result.get('sources', []))} sources.")
            return {"status": "completed", "job_id": job_id}


        elif result.get("status") == "rate_limited":
            err_msg = result.get("error", "Rate limit hit. Waiting before retry.")
            job.status = "rate_limited"
            job.stage = "rate_limited"
            job.error_message = err_msg
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            logger.warning(f"[Worker] Job {job_id} hit rate limit: {err_msg}")
            # Raise exception so RQ retry policy triggers backoff
            raise RateLimitError(err_msg)

        else:
            err_msg = result.get("error", "Research pipeline returned unsuccessful status.")
            job.status = "failed"
            job.stage = "failed"
            job.error_message = err_msg
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            logger.error(f"[Worker] Job {job_id} failed: {err_msg}")
            return {"status": "failed", "job_id": job_id, "error": err_msg}

    except RateLimitError:
        raise

    except Exception as e:
        logger.exception(f"[Worker] Unhandled exception processing job {job_id}: {e}")
        try:
            db.rollback()
            job = db.query(Report).filter(Report.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.stage = "failed"
                # Store a clean, safe, sanitized error message
                job.error_message = f"Execution error: {type(e).__name__}: {str(e)[:250]}"
                job.updated_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
        except Exception as db_err:
            logger.error(f"[Worker] Failed to write error status to DB for job {job_id}: {db_err}")

        return {"status": "failed", "job_id": job_id, "error": "Research execution failed"}

    finally:
        db.close()
