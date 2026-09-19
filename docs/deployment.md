# Production Deployment Guide

**Platform**: AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform  
**Version**: 1.0.0 (Stage 15 Production Deployment)  

---

## 1. Target Deployment Architecture

The platform uses a production-ready **multi-tier microservices architecture** composed of decoupled frontend, backend API, ML inference engines, and persistent database storage:

```
                      ┌──────────────────────────────────────┐
                      │   Streamlit Control Room UI          │
                      │   (Frontend Service / Port 8501)     │
                      └──────────────────┬───────────────────┘
                                         │
                                 HTTP REST / JSON
                                         │
                      ┌──────────────────▼───────────────────┐
                      │    FastAPI REST Backend API          │
                      │    (Backend Service / Port 8000)     │
                      └──────────────────┬───────────────────┘
                                         │
                      ┌──────────────────▼───────────────────┐
                      │    Application Services & ML Models  │
                      │    (LightGBM / LogisticRegression)   │
                      └──────────────────┬───────────────────┘
                                         │
                      ┌──────────────────▼───────────────────┐
                      │    PostgreSQL Database 16            │
                      │    (Database Service / Port 5432)    │
                      └──────────────────────────────────────┘
```

---

## 2. Docker & Containerization Setup

### 2.1 Multi-Container Services (`docker-compose.yml`)

1. **`db`**: PostgreSQL 16 Alpine container with persistent storage volume `postgres_data`.
2. **`backend`**: FastAPI REST application container running Uvicorn (`Dockerfile`).
3. **`frontend`**: Streamlit Control Room UI container (`Dockerfile.frontend`).

### 2.2 Docker Build & Launch Commands

```bash
# Build production images and start full stack in detached mode
docker-compose up --build -d

# Verify container liveness and health status
docker-compose ps

# Inspect backend production logs
docker-compose logs -f backend

# Stop production stack
docker-compose down
```

---

## 3. Production Environment Configuration

All production parameters must be injected via environment variables. Copy `.env.example` to `.env` and set environment credentials:

| Environment Variable | Production Setting | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enforces production runtime configuration. |
| `DEBUG` | `False` | Disables debug mode and raw stack trace exposures. |
| `HOST` | `0.0.0.0` | Production network binding interface. |
| `PORT` | `8000` | FastAPI server port. |
| `STREAMLIT_PORT` | `8501` | Streamlit dashboard port. |
| `API_PREFIX` | `/api/v1` | REST API version prefix. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8501,http://frontend:8501` | Restricts cross-origin requests to production UI domain(s). |
| `DATABASE_URL` | `postgresql://user:pass@db:5432/energy_intelligence_db` | PostgreSQL connection string. |
| `WEATHER_API_KEY` | *(Secret Token)* | Optional key for Open-Meteo or commercial weather providers. |
| `ENERGY_API_KEY` | *(Secret Token)* | Optional key for U.S. EIA / Grid data provider. |
| `AI_PROVIDER` | `openai` or `fallback` | LLM provider selector. Falls back to deterministic engine when key is unset. |
| `AI_API_KEY` | *(Secret Token)* | OpenAI or LLM API secret token. |

> [!CAUTION]
> **Secret Security**: Never commit `.env` or hardcode API keys/passwords in source control.

---

## 4. Database Setup & Initialization

To initialize ORM tables, verify foreign keys, and run column schema migration checks on production PostgreSQL / SQLite databases:

```bash
python scripts/init_prod_db.py
```

All 9 required production database tables are automatically initialized:
- `weather_data`
- `energy_data`
- `rain_predictions`
- `energy_forecasts`
- `anomalies`
- `alerts`
- `weather_impact_records`
- `scenario_runs`
- `ai_insights`

---

## 5. Machine Learning Model Artifacts

Pre-trained model artifacts are stored using project-relative paths under `saved_models/`:
- `rain_predictor_v1.joblib` (Logistic Regression rain probability model)
- `energy_forecaster_v1.joblib` (LightGBM 24-hour demand forecaster)

Artifact paths are resolved dynamically relative to the application root directory (`Path(__file__).resolve().parent.parent`).

---

## 6. Live Production Health Checks & Testing

### 6.1 Liveness & DB Connectivity
- `GET /health`: System liveness check (`{"status": "healthy"}`).
- `GET /api/v1/health/db`: Production database connectivity audit.

### 6.2 Manual Verification Commands

```powershell
# Run production API verification script
py scripts/test_prod_backend.py

# Run full automated regression suite
py run.py test
```

---

## 7. Cloud Deployment Options

### 7.1 Render / Railway / Fly.io
- **Backend API**: Deploy `Dockerfile` as a Web Service. Set Environment Variables in dashboard.
- **Frontend**: Deploy `Dockerfile.frontend` as a Web Service pointing `API_BASE_URL` to backend service URL.
- **PostgreSQL**: Provision Managed PostgreSQL service and inject connection URL into `DATABASE_URL`.

### 7.2 AWS ECS / EKS or GCP Cloud Run
- Push container images to ECR / Artifact Registry.
- Deploy task definitions for `backend` and `frontend` with Cloud SQL / RDS PostgreSQL.

---

## 8. Troubleshooting & Known Limitations

1. **Database Fallback**: If PostgreSQL URL is unreachable, `app/database/session.py` logs a warning and falls back to local SQLite file database (`energy_intelligence.db`).
2. **AI Provider Fallback**: If `AI_API_KEY` is omitted, `AI_PROVIDER=fallback` automatically routes query reports through the deterministic rule engine.
3. **Host Machine Docker CLI**: If Docker CLI is omitted on the host machine, the platform can be executed directly in production mode using `py scripts/init_prod_db.py` and `py run.py backend`.
