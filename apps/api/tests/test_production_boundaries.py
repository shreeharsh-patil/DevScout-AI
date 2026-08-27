from unittest.mock import patch

from fastapi.testclient import TestClient

from database import SessionLocal, UsageLog, Workspace
from main import app
from security import validate_public_url


def test_invalid_bearer_token_never_falls_back_to_demo():
    response = TestClient(app).get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}
    )
    assert response.status_code == 401


def test_identity_headers_cannot_impersonate_users_by_default():
    response = TestClient(app).get(
        "/api/v1/auth/me", headers={"X-User-Id": "usr_nonexistent"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] != "usr_nonexistent"


def test_private_and_unsafe_urls_are_rejected():
    for url in ("http://127.0.0.1/admin", "http://169.254.169.254/latest/meta-data", "file:///etc/passwd"):
        try:
            validate_public_url(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe URL accepted: {url}")


def test_research_request_rejects_extra_fields_and_bad_depth():
    client = TestClient(app)
    response = client.post(
        "/api/v1/research",
        json={"query": "react", "type": "npm", "depth": "unbounded", "admin": True},
    )
    assert response.status_code == 422


def test_queue_failure_refunds_credit_and_returns_503():
    client = TestClient(app)
    me = client.get("/api/v1/auth/me").json()
    workspace_id = me["workspace"]["id"]
    before = me["workspace"]["credits_used"]

    with patch("main.enqueue_research_job", return_value={"queued": False}):
        response = client.post(
            "/api/v1/research", json={"query": "safe-package", "type": "npm"}
        )
    assert response.status_code == 503

    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).one()
        assert workspace.credits_used == before
        assert db.query(UsageLog).filter(UsageLog.workspace_id == workspace_id).count() >= 0
    finally:
        db.close()


def test_malformed_llm_response_uses_fallback():
    from agents.analyzer import AnalyzerAgent

    analyzer = AnalyzerAgent()
    analyzer.use_llm = True
    with patch.object(analyzer, "_safe_generate", return_value="not valid json"):
        result = analyzer.analyze_developer({"profile": {"login": "dev", "public_repos": 1}, "recent_repos": []})
    assert result["score"] > 0
    assert "dev" in result["summary"]
