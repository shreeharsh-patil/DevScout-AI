# DevScout AI – Backend API & Worker (`apps/api`)

FastAPI multi-agent intelligence backend and durable research worker engine powering DevScout AI.

---

## 🏗️ Architecture Overview

```
[ Next.js Frontend ] ──HTTP──> [ FastAPI API Server ]
                                       │
                                (Enqueue Task)
                                       │
                                       ▼
                              [ Redis Job Queue ] (RQ)
                                       │
                                (Picks Up Job)
                                       │
                                       ▼
                           [ Research Worker Process ]
                                       │
                            (Orchestrates Agents)
                                       │
                                       ▼
                             [ PostgreSQL / SQLite ]
                                       │
                             (Polled by Next.js)
```

### Job State Cycle:
```
[queued] ──> [researching] ──> [analyzing] ──> [reporting] ──> [completed]
                                                           └──> [failed / rate_limited]
```

---

## 🛠️ Local Development

### 1. Create and Activate Virtual Environment
```powershell
cd "apps/api"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment
```powershell
Copy-Item .env.example .env
```

### 4. (Optional) Run Redis Locally
- **With Docker:**
  ```bash
  docker run -d --name devscout-redis -p 6379:6379 redis:alpine
  ```
- **Zero-Dependency Fallback:**
  If Redis is not running or `REDIS_URL` is omitted, the API automatically runs tasks via local background threads.

### 5. Start API Server
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start Worker Process (When using Redis)
In a separate terminal:
```powershell
python worker.py
```

---

## 🚀 Production Deployment (Railway / Render / Cloud)

### 1. Web Service (FastAPI)
- **Build / Install Command:**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
  ```

### 2. Background Worker Service
- **Build / Install Command:**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  python worker.py
  ```

---

## 🩺 Health & Worker Monitoring

- `GET /health` or `GET /api/v1/health`: API, database, and queue health check.
- `GET /api/v1/worker/health`: Worker status, active workers count, queued & failed jobs.

Example health response:
```json
{
  "status": "ok",
  "service": "devscout-api",
  "database": "connected",
  "queue": {
    "status": "healthy",
    "redis_connected": true,
    "mode": "redis_rq",
    "queue_name": "devscout-research",
    "active_workers": 1,
    "jobs_queued": 0,
    "jobs_failed": 0
  }
}
```

