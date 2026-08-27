from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
from sqlalchemy.orm import Session
import os
import json
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import AgentOrchestrator
from database import Report, SessionLocal, get_db, ensure_tables

orchestrator = AgentOrchestrator()


# ---------------------------------------------------------------------------
# App lifecycle – create dev tables on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_tables()
    yield


app = FastAPI(title="DevScout AI API", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS – read allowed origins from environment variable
# ---------------------------------------------------------------------------
_cors_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in _cors_raw.split(",") if origin.strip()
]

# Add CORS middleware
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
    "hackernews", "github-repo"
}

# Optional API key auth (read from env; empty string = disabled)
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


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def run_research_pipeline(job_id: str, query: str, research_type: str):
    logger.info(f"Running job {job_id} in background")

    db = SessionLocal()
    try:
        job = db.query(Report).filter(Report.job_id == job_id).first()

        if not job:
            return

        job.stage = "researching"
        db.commit()

        result = orchestrator.run_pipeline(query, research_type)
        job.status = result["status"]

        if result["status"] == "completed":
            job.stage = "completed"
            job.report_markdown = result["report"]
            job.raw_data = json.dumps({
                "researcher": result.get("raw_data"),
                "analysis": result.get("analysis")
            })
        elif result["status"] == "rate_limited":
            job.stage = "rate_limited"
            job.error_message = result.get("error", "Rate limited by Gemini.")
            job.report_markdown = result.get("error", "Rate limited by Gemini.")
        elif result["status"] == "failed":
            job.stage = "failed"
            job.error_message = result.get("error", "Pipeline failed.")

        db.commit()
        logger.info(f"Job {job_id} finished with status: {result['status']}")
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job.status = "failed"
        job.error_message = str(e)
        job.stage = "failed"
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "DevScout AI API is online"}


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "devscout-api"}


@app.post("/api/v1/research", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(default=None),
    db: Session = Depends(get_db),
):
    # --- API Key Auth (optional) ---
    if API_SECRET_KEY:
        if x_api_key != API_SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")

    # --- Input Validation ---
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

    # --- Email format validation for OSINT ---
    if request.type == "email":
        from agents.email_osint import validate_email
        is_valid, val_err = validate_email(query)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"Malformed email input: {val_err}"
            )

    job_id = "job_" + os.urandom(4).hex()

    logger.info(f"Starting {request.type} research for: {query}")

    new_job = Report(
        job_id=job_id,
        research_type=request.type,
        query=query,
        status="pending",
        stage="queued",
    )
    db.add(new_job)
    db.commit()

    background_tasks.add_task(run_research_pipeline, job_id, query, request.type)

    return ResearchResponse(job_id=job_id, status="pending")


@app.get("/api/v1/research/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Report).filter(Report.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    raw_data = None
    if job.raw_data:
        try:
            raw_data = json.loads(job.raw_data)
        except (json.JSONDecodeError, TypeError):
            raw_data = None

    return {
        "job_id": job.job_id,
        "status": job.status,
        "stage": job.stage,
        "report": job.report_markdown,
        "raw_data": raw_data,
        "research_type": job.research_type,
        "error": job.error_message,
    }


@app.get("/api/v1/history")
async def get_history(db: Session = Depends(get_db)):
    """Returns the last 20 research reports ordered by creation time (newest first)."""
    jobs = (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "job_id": job.job_id,
            "research_type": job.research_type,
            "query": job.query,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]


@app.get("/api/v1/research/report/{job_id}")
async def get_report(job_id: str, db: Session = Depends(get_db)):
    """Returns the full report_markdown for a completed job."""
    job = db.query(Report).filter(Report.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "research_type": job.research_type,
        "query": job.query,
        "status": job.status,
        "report_markdown": job.report_markdown,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@app.delete("/api/v1/research/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Permanently deletes a research job from the database."""
    job = db.query(Report).filter(Report.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"deleted": True, "job_id": job_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
