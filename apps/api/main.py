from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import os
import json

from agent_reach.core import AgentReach
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

agent_reach = AgentReach()
orchestrator = AgentOrchestrator()

class ResearchRequest(BaseModel):
    query: str
    type: str
    depth: str = "standard"

class ResearchResponse(BaseModel):
    job_id: str
    status: str

def run_research_pipeline(job_id: str, query: str, research_type: str):
    logger.info(f"Running job {job_id} in background")
    
    db = SessionLocal()
    job = db.query(Report).filter(Report.job_id == job_id).first()
    
    if not job:
        db.close()
        return

    try:
        result = orchestrator.run_pipeline(query, research_type)
        job.status = result['status']
        if result['status'] == 'completed':
            job.report_markdown = result['report']
            job.raw_data = json.dumps(result['raw_data'])
        db.commit()
        logger.info(f"Job {job_id} finished with status: {result['status']}")
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job.status = "failed"
        db.commit()
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "DevScout AI API is online"}

@app.get("/api/v1/health")
async def health():
    doctor_report = agent_reach.doctor()
    return {"status": "ok", "agent_reach": doctor_report}

@app.post("/api/v1/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    job_id = "job_" + os.urandom(4).hex()
    logger.info(f"Starting {request.type} research for: {request.query}")
    
    db = SessionLocal()
    new_job = Report(job_id=job_id, research_type=request.type, query=request.query, status="pending")
    db.add(new_job)
    db.commit()
    db.close()
    
    background_tasks.add_task(run_research_pipeline, job_id, request.query, request.type)
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
