import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from database import Report, User, Workspace, WorkspaceMember, UsageLog, SessionLocal, ensure_tables
from auth import create_jwt_token, get_or_create_default_tenant


@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()
    yield
    db = SessionLocal()
    try:
        db.query(UsageLog).filter(UsageLog.workspace_id.like("test_%")).delete()
        db.query(Report).filter(Report.job_id.like("test_%")).delete()
        db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id.like("test_%")).delete()
        db.query(Workspace).filter(Workspace.id.like("test_%")).delete()
        db.query(User).filter(User.id.like("test_%")).delete()
        db.commit()
    finally:
        db.close()


class TestSaaSAuthAndIsolation:
    """Test user authentication, workspace tenancy, report isolation, and credit tracking."""

    def test_default_tenant_provisioning(self):
        client = TestClient(app)
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert "user" in data
        assert "workspace" in data
        assert data["workspace"]["plan_tier"] == "free"
        assert data["workspace"]["monthly_credit_limit"] == 50

    def test_token_generation_and_login(self):
        client = TestClient(app)
        res = client.post(
            "/api/v1/auth/token",
            json={"email": "alice@example.com", "name": "Alice Developer"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"

        token = data["access_token"]
        # Authenticate using token
        res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        me = res_me.json()
        assert me["user"]["email"] == "alice@example.com"
        assert me["user"]["name"] == "Alice Developer"

    def test_cross_tenant_report_isolation_and_403_forbidden(self):
        client = TestClient(app)
        db = SessionLocal()

        # 1. Create User A & Workspace A
        user_a = User(id="test_usr_a", email="a@tenant.com", name="User A")
        ws_a = Workspace(id="test_ws_a", name="Tenant A", slug="tenant-a", owner_id=user_a.id)
        mem_a = WorkspaceMember(id="test_mem_a", workspace_id=ws_a.id, user_id=user_a.id, role="owner")

        # 2. Create User B & Workspace B
        user_b = User(id="test_usr_b", email="b@tenant.com", name="User B")
        ws_b = Workspace(id="test_ws_b", name="Tenant B", slug="tenant-b", owner_id=user_b.id)
        mem_b = WorkspaceMember(id="test_mem_b", workspace_id=ws_b.id, user_id=user_b.id, role="owner")

        # 3. Create private Report belonging to Workspace A
        report_a = Report(
            job_id="test_job_secret_a",
            user_id=user_a.id,
            workspace_id=ws_a.id,
            research_type="startup",
            query="https://secret-project-a.com",
            status="completed",
            stage="completed",
            report_markdown="# Confidential Project A Report",
            is_saved=False
        )

        # Tokens (generate while session is active)
        token_a = create_jwt_token({"sub": user_a.id, "user_id": user_a.id, "workspace_id": ws_a.id})
        token_b = create_jwt_token({"sub": user_b.id, "user_id": user_b.id, "workspace_id": ws_b.id})
        job_id_a = report_a.job_id

        db.add_all([user_a, ws_a, mem_a, user_b, ws_b, mem_b, report_a])
        db.commit()
        db.close()

        # User A can access their own report
        res_a = client.get(
            f"/api/v1/research/report/{job_id_a}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert res_a.status_code == 200

        # User B CANNOT access User A's private report (Must return 403 Forbidden)
        res_b = client.get(
            f"/api/v1/research/report/{job_id_a}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_b.status_code == 403

        # User B's history must NOT contain User A's report
        res_hist_b = client.get(
            "/api/v1/history",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_hist_b.status_code == 200
        hist_b = res_hist_b.json()
        assert not any(item["job_id"] == job_id_a for item in hist_b)

    def test_saved_rename_and_delete_lifecycle(self):
        client = TestClient(app)
        db = SessionLocal()

        user = User(id="test_usr_c", email="c@tenant.com", name="User C")
        ws = Workspace(id="test_ws_c", name="Tenant C", slug="tenant-c", owner_id=user.id)
        mem = WorkspaceMember(id="test_mem_c", workspace_id=ws.id, user_id=user.id, role="owner")
        job = Report(
            job_id="test_job_crud",
            user_id=user.id,
            workspace_id=ws.id,
            research_type="developer",
            query="torvalds",
            status="completed",
            stage="completed",
            report_markdown="# Developer Report",
            is_saved=False
        )
        token = create_jwt_token({"sub": user.id, "user_id": user.id, "workspace_id": ws.id})
        job_id = job.job_id

        db.add_all([user, ws, mem, job])
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {token}"}

        # 1. Rename and bookmark report
        res_patch = client.patch(
            f"/api/v1/reports/{job_id}",
            json={"custom_title": "Linus Torvalds Deep Dive", "is_saved": True, "tags": ["linux", "core"]},
            headers=headers
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["custom_title"] == "Linus Torvalds Deep Dive"
        assert res_patch.json()["is_saved"] is True

        # 2. Get saved reports
        res_saved = client.get("/api/v1/reports/saved", headers=headers)
        assert res_saved.status_code == 200
        saved_list = res_saved.json()
        assert len(saved_list) == 1
        assert saved_list[0]["custom_title"] == "Linus Torvalds Deep Dive"

        # 3. Delete report
        res_del = client.delete(f"/api/v1/reports/{job_id}", headers=headers)
        assert res_del.status_code == 200

        # 4. Confirm deleted
        res_after = client.get(f"/api/v1/research/status/{job_id}", headers=headers)
        assert res_after.status_code == 404

    def test_credit_deduction_and_usage_tracking(self):
        client = TestClient(app)
        db = SessionLocal()

        user = User(id="test_usr_credits", email="credits@tenant.com", name="Credit User")
        ws = Workspace(
            id="test_ws_credits",
            name="Credit WS",
            slug="credit-ws",
            owner_id=user.id,
            monthly_credit_limit=2,
            credits_used=0
        )
        mem = WorkspaceMember(id="test_mem_credits", workspace_id=ws.id, user_id=user.id, role="owner")
        token = create_jwt_token({"sub": user.id, "user_id": user.id, "workspace_id": ws.id})
        ws_id = ws.id

        db.add_all([user, ws, mem])
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {token}"}


        # 1. First query (Credits: 1/2)
        with patch("main.enqueue_research_job", return_value={"queued": True}):
            res1 = client.post(
                "/api/v1/research",
                json={"query": "react", "type": "npm"},
                headers=headers
            )
            assert res1.status_code == 200

            # 2. Second query (Credits: 2/2)
            res2 = client.post(
                "/api/v1/research",
                json={"query": "vue", "type": "npm"},
                headers=headers
            )
            assert res2.status_code == 200

            # 3. Third query (Limit exceeded -> 402 Payment Required)
            res3 = client.post(
                "/api/v1/research",
                json={"query": "angular", "type": "npm"},
                headers=headers
            )
            assert res3.status_code == 402
            assert "Credit limit exceeded" in res3.json()["detail"]

        # Check usage endpoint
        res_usage = client.get(f"/api/v1/workspaces/{ws_id}/usage", headers=headers)
        assert res_usage.status_code == 200

        usage_data = res_usage.json()
        assert usage_data["credits_used"] == 2
        assert usage_data["credits_remaining"] == 0
        assert len(usage_data["usage_logs"]) == 2
