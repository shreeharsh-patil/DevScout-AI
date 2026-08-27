# DevScout AI – Backend API (`apps/api`)

FastAPI multi-agent intelligence backend powering DevScout AI.

---

## 🛠️ Quickstart (Windows PowerShell)

### 1. Create and Activate Virtual Environment
```powershell
cd "apps/api"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API keys:
```powershell
Copy-Item .env.example .env
```

### 4. Start Development Server
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

---

## 🚀 Production Deployment (Render / Railway / Cloud)

### Build / Install Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

---

## 🩺 Health Check Endpoints

- `GET /health`: Lightweight service status check
- `GET /api/v1/health`: API versioned health check endpoint

Both endpoints return:
```json
{
  "status": "ok",
  "service": "devscout-api"
}
```
