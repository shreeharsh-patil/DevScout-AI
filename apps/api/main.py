from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import os
import json
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import AgentOrchestrator
from database import SessionLocal, Report

app = FastAPI(title="DevScout AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = AgentOrchestrator()

# ---------------------------------------------------------------------------
# Valid research types (single source of truth)
# ---------------------------------------------------------------------------
VALID_RESEARCH_TYPES = {
    "developer", "startup", "email", "youtube",
    "reddit", "idea", "social", "linkedin", "npm"
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
    job = db.query(Report).filter(Report.job_id == job_id).first()
    
    if not job:
        db.close()
        return

    try:
        result = orchestrator.run_pipeline(query, research_type)
        job.status = result["status"]
        if result["status"] == "completed":
            job.report_markdown = result["report"]
            job.raw_data = json.dumps(result["raw_data"])
        elif result["status"] == "rate_limited":
            # Store the error message so the frontend can surface it
            job.report_markdown = result.get("error", "Rate limited by Gemini.")
        db.commit()
        logger.info(f"Job {job_id} finished with status: {result['status']}")
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job.status = "failed"
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "DevScout AI API is online"}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/research", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(default=None),
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

    job_id = "job_" + os.urandom(4).hex()
    logger.info(f"Starting {request.type} research for: {query}")
    
    db = SessionLocal()
    new_job = Report(job_id=job_id, research_type=request.type, query=query, status="pending")
    db.add(new_job)
    db.commit()
    db.close()
    
    background_tasks.add_task(run_research_pipeline, job_id, query, request.type)
    
    return ResearchResponse(job_id=job_id, status="pending")


@app.get("/api/v1/research/status/{job_id}")
async def get_job_status(job_id: str):
    db = SessionLocal()
    job = db.query(Report).filter(Report.job_id == job_id).first()
    db.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": job.job_id,
        "status": job.status,
        "report": job.report_markdown
    }


@app.get("/api/v1/history")
async def get_history():
    """Returns the last 20 research reports ordered by creation time (newest first)."""
    db = SessionLocal()
    try:
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
    finally:
        db.close()


@app.get("/api/v1/research/report/{job_id}")
async def get_report(job_id: str):
    """Returns the full report_markdown for a completed job."""
    db = SessionLocal()
    try:
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
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
