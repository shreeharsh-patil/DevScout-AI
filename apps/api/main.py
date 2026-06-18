from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from loguru import logger
import os

from agent_reach.core import AgentReach
from agents.orchestrator import AgentOrchestrator

app = FastAPI(title="DevScout AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent Reach and Orchestrator
agent_reach = AgentReach()
orchestrator = AgentOrchestrator()

# In-memory storage for reports (Mocking DB for now)
job_store: Dict[str, Dict] = {}

class ResearchRequest(BaseModel):
    query: str
    type: str  # developer, startup, youtube, reddit, idea, resume
    depth: str = "standard"

class ResearchResponse(BaseModel):
    job_id: str
    status: str

def run_research_pipeline(job_id: str, query: str, research_type: str):
    logger.info(f"Running job {job_id} in background")
    result = orchestrator.run_pipeline(query, research_type)
    job_store[job_id] = result
    logger.info(f"Job {job_id} finished with status: {result['status']}")

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
    
    job_store[job_id] = {"status": "pending"}
    background_tasks.add_task(run_research_pipeline, job_id, request.query, request.type)
    
    return ResearchResponse(job_id=job_id, status="pending")

@app.get("/api/v1/research/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store[job_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
