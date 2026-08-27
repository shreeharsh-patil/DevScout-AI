from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Header, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
import json
import sys
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import AgentOrchestrator
from database import Report, get_db, ensure_tables, User, Workspace, WorkspaceMember, UsageLog
from auth import (
    get_current_auth,
    verify_report_access,
    check_and_deduct_credits,
    create_jwt_token
)
from queue_manager import enqueue_research_job, get_queue_health
from tasks import execute_research_job
from middleware import RateLimitMiddleware, RequestContextMiddleware
from security import validate_public_url
from settings import (
    ALLOW_LOCAL_QUEUE_FALLBACK,
    API_SECRET_KEY,
    ENABLE_DEV_TOKEN_AUTH,
    LOG_JSON,
    REQUIRE_QUEUE,
    cors_origins,
    validate_runtime_config,
)

orchestrator = AgentOrchestrator()


# ---------------------------------------------------------------------------
# App lifecycle – create dev tables on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_config()
    logger.remove()
    logger.add(sys.stderr, serialize=LOG_JSON, level=os.getenv("LOG_LEVEL", "INFO"))
    ensure_tables()
    yield


app = FastAPI(title="DevScout AI SaaS API", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS – read allowed origins from environment variable
# ---------------------------------------------------------------------------
CORS_ORIGINS = cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-Id", "X-Workspace-Id"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

# ---------------------------------------------------------------------------
# Valid research types (single source of truth)
# ---------------------------------------------------------------------------
VALID_RESEARCH_TYPES = {
    "developer", "startup", "email", "email_intelligence", "youtube",
    "reddit", "idea", "social", "linkedin", "npm",
    "hackernews", "github-repo", "repository"
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=500)
    type: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,31}$")
    depth: str = Field(default="standard", pattern=r"^(standard)$")


    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in VALID_RESEARCH_TYPES:
            raise ValueError(f"Unsupported research type: {value}")
        return value


class ResearchResponse(BaseModel):
    job_id: str
    status: str


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    name: Optional[str] = Field(default=None, max_length=255)
    workspace_name: Optional[str] = Field(default=None, max_length=255)


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=63, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class UpdateReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    custom_title: Optional[str] = Field(default=None, max_length=255)
    is_saved: Optional[bool] = None
    tags: Optional[List[str]] = Field(default=None, max_length=20)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        cleaned = list(dict.fromkeys(tag.strip() for tag in value if tag.strip()))
        if any(len(tag) > 50 for tag in cleaned):
            raise ValueError("Tags must be 50 characters or fewer")
        return cleaned


# ---------------------------------------------------------------------------
# Base & Health Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "DevScout AI API is online"}


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    """Liveness probe: succeeds when the API process can serve requests."""
    return {"status": "ok", "service": "devscout-api", "queue": {"status": "not_checked"}}


@app.get("/api/v1/ready")
async def readiness(response: Response, db: Session = Depends(get_db)):
    """Readiness probe for database and required queue dependencies."""
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    queue_health = get_queue_health()

    queue_ok = queue_health.get("redis_connected", False) or not REQUIRE_QUEUE
    ready = db_ok and queue_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "service": "devscout-api",
        "database": "connected" if db_ok else "disconnected",
        "queue": queue_health,
    }


@app.get("/api/v1/worker/health")
async def worker_health():
    """Returns real-time health and metrics for Redis RQ workers."""
    return get_queue_health()


# ---------------------------------------------------------------------------
# Auth & Multi-Tenancy Routes
# ---------------------------------------------------------------------------

@app.get("/api/v1/auth/me")
async def get_me(
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Returns the authenticated user, active workspace, permissions, and credit usage."""
    user, workspace = auth

    # Fetch all workspaces the user has access to
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    workspaces = db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all() if workspace_ids else [workspace]

    saved_reports_count = (
        db.query(Report)
        .filter(Report.workspace_id == workspace.id, Report.is_saved == True, Report.is_archived == False)
        .count()
    )
    total_jobs_count = (
        db.query(Report)
        .filter(Report.workspace_id == workspace.id, Report.is_archived == False)
        .count()
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "role": user.role
        },
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "slug": workspace.slug,
            "plan_tier": workspace.plan_tier,
            "monthly_credit_limit": workspace.monthly_credit_limit,
            "credits_used": workspace.credits_used,
            "credits_remaining": max(0, workspace.monthly_credit_limit - workspace.credits_used)
        },
        "workspaces": [
            {
                "id": w.id,
                "name": w.name,
                "slug": w.slug,
                "plan_tier": w.plan_tier,
                "is_active": (w.id == workspace.id)
            }
            for w in workspaces
        ],
        "stats": {
            "total_research_jobs": total_jobs_count,
            "saved_reports": saved_reports_count,
            "credits_used": workspace.credits_used,
            "credit_limit": workspace.monthly_credit_limit
        }
    }


@app.post("/api/v1/auth/token")
async def generate_auth_token(payload: TokenRequest, db: Session = Depends(get_db)):
    """Generates a JWT access token for authentication (used by frontend auth & tests)."""
    if not ENABLE_DEV_TOKEN_AUTH:
        raise HTTPException(status_code=404, detail="Development token authentication is disabled")
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user_id = f"usr_{os.urandom(4).hex()}"
        user = User(
            id=user_id,
            email=email,
            name=payload.name or email.split("@")[0].capitalize(),
            role="member"
        )
        db.add(user)
        db.flush()

        ws_id = f"ws_{os.urandom(4).hex()}"
        workspace = Workspace(
            id=ws_id,
            name=payload.workspace_name or f"{user.name}'s Workspace",
            slug=f"{email.split('@')[0]}-{os.urandom(2).hex()}",
            owner_id=user.id,
            plan_tier="free",
            monthly_credit_limit=50,
            credits_used=0
        )
        db.add(workspace)
        db.flush()

        member = WorkspaceMember(
            id=f"mem_{user.id}_{workspace.id}",
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner"
        )
        db.add(member)
        db.commit()
    else:
        membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
        workspace = db.query(Workspace).filter(Workspace.id == membership.workspace_id).first() if membership else None
        if not workspace:
            workspace = db.query(Workspace).filter(Workspace.owner_id == user.id).first()

    token = create_jwt_token({
        "sub": user.id,
        "user_id": user.id,
        "email": user.email,
        "workspace_id": workspace.id if workspace else None
    })

    return {
        "access_token": token,
        "token_type": "Bearer",
        "user_id": user.id,
        "workspace_id": workspace.id if workspace else None
    }


@app.get("/api/v1/workspaces")
async def list_workspaces(
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Lists all workspaces accessible by the current user."""
    user, _ = auth
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    workspaces = db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()

    return [
        {
            "id": w.id,
            "name": w.name,
            "slug": w.slug,
            "plan_tier": w.plan_tier,
            "monthly_credit_limit": w.monthly_credit_limit,
            "credits_used": w.credits_used,
            "is_owner": (w.owner_id == user.id)
        }
        for w in workspaces
    ]


@app.post("/api/v1/workspaces")
async def create_workspace(
    req: WorkspaceCreateRequest,
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Creates a new isolated workspace for the user."""
    user, _ = auth
    ws_id = f"ws_{os.urandom(4).hex()}"
    slug = req.slug or f"{req.name.lower().replace(' ', '-')}-{os.urandom(2).hex()}"

    workspace = Workspace(
        id=ws_id,
        name=req.name.strip(),
        slug=slug,
        owner_id=user.id,
        plan_tier="free",
        monthly_credit_limit=50,
        credits_used=0
    )
    db.add(workspace)
    db.flush()

    member = WorkspaceMember(
        id=f"mem_{user.id}_{workspace.id}",
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner"
    )
    db.add(member)
    db.commit()

    return {
        "id": workspace.id,
        "name": workspace.name,
        "slug": workspace.slug,
        "plan_tier": workspace.plan_tier
    }


@app.get("/api/v1/workspaces/{workspace_id}/usage")
async def get_workspace_usage(
    workspace_id: str,
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Returns detailed credit usage and action logs for a workspace."""
    user, active_ws = auth
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.user_id == user.id)
        .first()
    )
    if not membership and workspace.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this workspace.")

    logs = (
        db.query(UsageLog)
        .filter(UsageLog.workspace_id == workspace.id)
        .order_by(UsageLog.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "workspace_id": workspace.id,
        "plan_tier": workspace.plan_tier,
        "monthly_credit_limit": workspace.monthly_credit_limit,
        "credits_used": workspace.credits_used,
        "credits_remaining": max(0, workspace.monthly_credit_limit - workspace.credits_used),
        "usage_logs": [
            {
                "id": log.id,
                "action": log.action,
                "job_id": log.job_id,
                "credits_deducted": log.credits_deducted,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }


# ---------------------------------------------------------------------------
# Protected Research Execution & Report Lifecycle
# ---------------------------------------------------------------------------

@app.post("/api/v1/research", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(default=None),
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user, workspace = auth

    # Optional API Key Auth
    if API_SECRET_KEY:
        if x_api_key != API_SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")

    query = request.query

    # Email format validation for OSINT and Email Intelligence
    if request.type in ("email", "email_intelligence"):
        from intelligence.email import EmailValidatorAgent
        val_res = EmailValidatorAgent.validate(query)
        if not val_res.valid:
            raise HTTPException(
                status_code=422,
                detail=f"Malformed email input: {val_res.error}"
            )

    if request.type in {"startup", "linkedin", "youtube"} and ("://" in query or "." in query):
        try:
            query = validate_public_url(query)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    job_id = "job_" + os.urandom(4).hex()

    logger.info("research_job_created", research_type=request.type, job_id=job_id, workspace_id=workspace.id)

    # Create the report and usage entry atomically so PostgreSQL foreign keys and
    # concurrent credit checks cannot leave partial state.
    new_job = Report(
        job_id=job_id,
        user_id=user.id,
        workspace_id=workspace.id,
        research_type=request.type,
        query=query,
        status="pending",
        stage="queued",
    )
    try:
        db.add(new_job)
        db.flush()
        check_and_deduct_credits(workspace, user, job_id, action=f"research_{request.type}", credits_cost=1, db=db)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("research_job_database_write_failed", job_id=job_id)
        raise HTTPException(status_code=503, detail="Research storage is temporarily unavailable")

    # 2. Push into durable queue (or graceful fallback for local development)
    enqueue_res = enqueue_research_job(job_id, query, request.type)
    if not enqueue_res.get("queued"):
        if ALLOW_LOCAL_QUEUE_FALLBACK:
            logger.warning("queue_unavailable_using_local_fallback", job_id=job_id)
            background_tasks.add_task(execute_research_job, job_id, query, request.type)
        else:
            new_job.status = "failed"
            new_job.stage = "failed"
            new_job.error_message = "Research queue is temporarily unavailable"
            workspace.credits_used = max(0, workspace.credits_used - 1)
            db.query(UsageLog).filter(UsageLog.job_id == job_id).delete()
            db.commit()
            raise HTTPException(status_code=503, detail="Research queue is temporarily unavailable")

    return ResearchResponse(job_id=job_id, status="pending")


@app.get("/api/v1/research/status/{job_id}")
async def get_job_status(
    job_id: str,
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    user, workspace = auth
    job = db.query(Report).filter(Report.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Enforce multi-tenancy & ownership check
    verify_report_access(job, user, workspace, db)

    raw_data = None
    if job.raw_data:
        try:
            raw_data = json.loads(job.raw_data)
        except (json.JSONDecodeError, TypeError):
            raw_data = None

    sources = []
    if job.sources:
        try:
            sources = json.loads(job.sources)
        except (json.JSONDecodeError, TypeError):
            sources = []

    tags = []
    if job.tags:
        try:
            tags = json.loads(job.tags)
        except (json.JSONDecodeError, TypeError):
            tags = []

    return {
        "job_id": job.job_id,
        "user_id": job.user_id,
        "workspace_id": job.workspace_id,
        "status": job.status,
        "stage": job.stage,
        "custom_title": job.custom_title,
        "is_saved": job.is_saved,
        "tags": tags,
        "report": job.report_markdown,
        "report_markdown": job.report_markdown,
        "raw_data": raw_data,
        "sources": sources,
        "research_type": job.research_type,
        "error": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@app.get("/api/v1/history")
async def get_history(
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Returns research reports strictly isolated to the user's active workspace."""
    user, workspace = auth
    jobs = (
        db.query(Report)
        .filter(Report.workspace_id == workspace.id, Report.is_archived == False)
        .order_by(Report.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "job_id": job.job_id,
            "research_type": job.research_type,
            "query": job.query,
            "custom_title": job.custom_title,
            "is_saved": job.is_saved,
            "status": job.status,
            "stage": job.stage,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]


@app.get("/api/v1/reports/saved")
async def get_saved_reports(
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Returns bookmarked/saved reports for the active workspace."""
    user, workspace = auth
    saved_jobs = (
        db.query(Report)
        .filter(Report.workspace_id == workspace.id, Report.is_saved == True, Report.is_archived == False)
        .order_by(Report.updated_at.desc())
        .all()
    )
    return [
        {
            "job_id": job.job_id,
            "research_type": job.research_type,
            "query": job.query,
            "custom_title": job.custom_title,
            "is_saved": True,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
        for job in saved_jobs
    ]


@app.get("/api/v1/research/report/{job_id}")
async def get_report(
    job_id: str,
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Returns the full report_markdown for a completed job with authorization checks."""
    user, workspace = auth
    job = db.query(Report).filter(Report.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_report_access(job, user, workspace, db)

    sources = []
    if job.sources:
        try:
            sources = json.loads(job.sources)
        except Exception:
            sources = []

    return {
        "job_id": job.job_id,
        "research_type": job.research_type,
        "query": job.query,
        "custom_title": job.custom_title,
        "is_saved": job.is_saved,
        "status": job.status,
        "report_markdown": job.report_markdown,
        "sources": sources,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@app.patch("/api/v1/reports/{job_id}")
async def update_report(
    job_id: str,
    req: UpdateReportRequest,
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Renames report title, toggles saved bookmark, or updates tags."""
    user, workspace = auth
    job = db.query(Report).filter(Report.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_report_access(job, user, workspace, db)

    if req.custom_title is not None:
        job.custom_title = req.custom_title.strip() or None
    if req.is_saved is not None:
        job.is_saved = req.is_saved
    if req.tags is not None:
        job.tags = json.dumps(req.tags)

    db.commit()

    return {
        "job_id": job.job_id,
        "custom_title": job.custom_title,
        "is_saved": job.is_saved,
        "message": "Report updated successfully."
    }


@app.delete("/api/v1/reports/{job_id}")
@app.delete("/api/v1/research/{job_id}")
async def delete_job(
    job_id: str,
    auth: tuple[User, Workspace] = Depends(get_current_auth),
    db: Session = Depends(get_db)
):
    """Deletes or archives a research job from the active workspace."""
    user, workspace = auth
    job = db.query(Report).filter(Report.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_report_access(job, user, workspace, db)

    job.is_archived = True
    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully", "job_id": job_id}
