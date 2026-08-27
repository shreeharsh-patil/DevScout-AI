import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from database import Report, SessionLocal, ensure_tables
from tasks import execute_research_job
from queue_manager import get_queue_health, enqueue_research_job


@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()
    yield
    # Clean up test records
    db = SessionLocal()
    try:
        db.query(Report).filter(Report.job_id.like("test_%")).delete()
        db.commit()
    finally:
        db.close()


class TestDurableQueueAndWorker:
    """Tests for durable job queue, worker execution, deduplication, and health checks."""

    def test_job_submission_creates_db_record(self):
        client = TestClient(app)
        with patch("main.enqueue_research_job", return_value={"queued": True}):
            res = client.post(
                "/api/v1/research",
                json={"query": "test_user", "type": "developer"}
            )
        assert res.status_code == 200
        data = res.json()
        job_id = data["job_id"]
        assert data["status"] == "pending"

        db = SessionLocal()
        try:
            job = db.query(Report).filter(Report.job_id == job_id).first()
            assert job is not None
            assert job.research_type == "developer"
            assert job.query == "test_user"
            assert job.status in ("pending", "processing", "completed")
            assert job.stage in ("queued", "researching", "analyzing", "reporting", "completed")
        finally:
            db.close()

    def test_duplicate_execution_prevention(self):
        """Worker should skip jobs that are already completed."""
        db = SessionLocal()
        job_id = "test_dedup_01"
        try:
            job = Report(
                job_id=job_id,
                research_type="developer",
                query="alice",
                status="completed",
                stage="completed",
                report_markdown="# Done"
            )
            db.add(job)
            db.commit()
        finally:
            db.close()

        with patch("tasks.orchestrator.run_pipeline") as mock_pipeline:
            result = execute_research_job(job_id, "alice", "developer")
            assert result["status"] == "skipped"
            mock_pipeline.assert_not_called()

    def test_incremental_stage_progression(self):
        """Job should progress through researching -> analyzing -> reporting -> completed."""
        db = SessionLocal()
        job_id = "test_stages_01"
        try:
            job = Report(
                job_id=job_id,
                research_type="developer",
                query="alice",
                status="pending",
                stage="queued"
            )
            db.add(job)
            db.commit()
        finally:
            db.close()

        stages_recorded = []

        def mock_run_pipeline(query, research_type, on_stage_change=None, **kwargs):
            if on_stage_change:
                on_stage_change("researching")
                stages_recorded.append("researching")
                on_stage_change("analyzing")
                stages_recorded.append("analyzing")
                on_stage_change("reporting")
                stages_recorded.append("reporting")
            return {
                "status": "completed",
                "report": "# Final Report",
                "raw_data": {"user": "alice"},
                "analysis": {"score": 90}
            }

        with patch("tasks.orchestrator.run_pipeline", side_effect=mock_run_pipeline):
            result = execute_research_job(job_id, "alice", "developer")
            assert result["status"] == "completed"

        db = SessionLocal()
        try:
            saved_job = db.query(Report).filter(Report.job_id == job_id).first()
            assert saved_job.status == "completed"
            assert saved_job.stage == "completed"
            assert saved_job.report_markdown == "# Final Report"
            assert "researching" in stages_recorded
            assert "analyzing" in stages_recorded
            assert "reporting" in stages_recorded
        finally:
            db.close()

    def test_safe_error_capture_on_failure(self):
        """Worker should catch exceptions and safely store error message without crashing."""
        db = SessionLocal()
        job_id = "test_error_01"
        try:
            job = Report(
                job_id=job_id,
                research_type="developer",
                query="bad_query",
                status="pending",
                stage="queued"
            )
            db.add(job)
            db.commit()
        finally:
            db.close()

        def mock_failing_pipeline(query, research_type, on_stage_change=None, **kwargs):
            raise ConnectionError("External API connection timed out")


        with patch("tasks.orchestrator.run_pipeline", side_effect=mock_failing_pipeline):
            result = execute_research_job(job_id, "bad_query", "developer")
            assert result["status"] == "failed"

        db = SessionLocal()
        try:
            saved_job = db.query(Report).filter(Report.job_id == job_id).first()
            assert saved_job.status == "failed"
            assert saved_job.stage == "failed"
            assert "ConnectionError" in saved_job.error_message
        finally:
            db.close()

    def test_health_and_worker_endpoints(self):
        client = TestClient(app)
        
        # Test GET /health
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("ok", "degraded")
        assert "queue" in data
        assert "service" in data

        # Test GET /api/v1/worker/health
        res_worker = client.get("/api/v1/worker/health")
        assert res_worker.status_code == 200
        worker_data = res_worker.json()
        assert "status" in worker_data
        assert "redis_connected" in worker_data

    def test_get_job_status_compatibility(self):
        client = TestClient(app)
        db = SessionLocal()
        job_id = "test_status_endpoint"
        try:
            job = Report(
                job_id=job_id,
                research_type="email",
                query="test@domain.com",
                status="completed",
                stage="completed",
                report_markdown="# Email OSINT Report",
                raw_data=json.dumps({"analysis": {"domain": "domain.com"}})
            )
            db.add(job)
            db.commit()
        finally:
            db.close()

        res = client.get(f"/api/v1/research/status/{job_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["stage"] == "completed"
        assert data["report"] == "# Email OSINT Report"
        assert data["report_markdown"] == "# Email OSINT Report"
        assert data["raw_data"]["analysis"]["domain"] == "domain.com"
        assert "created_at" in data
        assert "updated_at" in data
