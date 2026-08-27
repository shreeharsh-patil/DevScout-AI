from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import AgentOrchestrator
from database import Report, SessionLocal, get_db, ensure_tables, User, Workspace, WorkspaceMember, UsageLog
from auth import (
    get_current_auth,
    get_current_user,
    get_current_workspace,
    verify_report_access,
    check_and_deduct_credits,
    create_jwt_token,
    get_or_create_default_tenant
)
from queue_manager import enqueue_research_job, get_queue_health, is_redis_available
from tasks import execute_research_job

orchestrator = AgentOrchestrator()


# ---------------------------------------------------------------------------
# App lifecycle – create dev tables on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_tables()
    yield


app = FastAPI(title="DevScout AI SaaS API", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS – read allowed origins from environment variable
# ---------------------------------------------------------------------------
_cors_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in _cors_raw.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Valid research types (single source of truth)
# ---------------------------------------------------------------------------
VALID_RESEARCH_TYPES = {
    "developer", "startup", "email", "youtube",
    "reddit", "idea", "social", "linkedin", "npm",
    "hackernews", "github-repo", "repository"
}

API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str
    type: str
    depth: str = "standard"


class ResearchResponse(BaseModel):
    job_id: str
    status: str


class TokenRequest(BaseModel):
    email: str
    name: Optional[str] = None
    workspace_name: Optional[str] = None


class WorkspaceCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None


class UpdateReportRequest(BaseModel):
    custom_title: Optional[str] = None
    is_saved: Optional[bool] = None
    tags: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Base & Health Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "DevScout AI API is online"}


@app.get("/health")
@app.get("/api/v1/health")
async def health(db: Session = Depends(get_db)):
    """Comprehensive health check including database and queue/worker status."""
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    queue_health = get_queue_health()

    return {
        "status": "ok" if db_ok else "degraded",
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

    # Input Validation
    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="'query' must not be empty.")
    if len(query) > 500:
        raise HTTPException(status_code=422, detail="'query' must be 500 characters or fewer.")
    if request.type not in VALID_RESEARCH_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid research type '{request.type}'. Must be one of: {', '.join(sorted(VALID_RESEARCH_TYPES))}."
        )

    # Email format validation for OSINT
    if request.type == "email":
        from agents.email_osint import validate_email
        is_valid, val_err = validate_email(query)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"Malformed email input: {val_err}"
            )

    job_id = "job_" + os.urandom(4).hex()

    # Credit & Usage Check
    check_and_deduct_credits(workspace, user, job_id, action=f"research_{request.type}", credits_cost=1, db=db)

    logger.info(f"Starting {request.type} research for: {query} (Job ID: {job_id}, Workspace: {workspace.id})")

    # 1. Create database job record with multi-tenant ownership
    new_job = Report(
        job_id=job_id,
        user_id=user.id,
        workspace_id=workspace.id,
        research_type=request.type,
        query=query,
        status="pending",
        stage="queued",
    )
    db.add(new_job)
    db.commit()

    # 2. Push into durable queue (or graceful fallback for local development)
    enqueue_res = enqueue_research_job(job_id, query, request.type)
    if not enqueue_res.get("queued"):
        logger.info(f"Running job {job_id} via local background executor (Redis queue unavailable)")
        background_tasks.add_task(execute_research_job, job_id, query, request.type)

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
