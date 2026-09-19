# Project Overview — AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform

## Executive Summary

The **AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform** is a full-stack, production-grade predictive intelligence system designed to empower power grid operators, energy analysts, and utility engineers with real-time meteorological insight, load forecasting, anomaly detection, scenario stress-testing, and automated incident response capabilities.

---

## Technical Stack Overview

| Component Layer | Technologies & Frameworks | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit, Plotly, HTML/CSS | Interactive 10-view Control Room dashboard with reactive theme engine and web audio alerts. |
| **REST Backend API** | FastAPI, Pydantic V2, Uvicorn | High-performance asynchronous REST API (`/api/v1`) with request-id tracking and Swagger docs (`/docs`). |
| **Application Services** | Python 3.11+, Pandas, NumPy, SciPy | Modular domain services for ingestion, quality auditing, scenario simulation, and alert lifecycle management. |
| **Machine Learning** | Scikit-Learn (LogReg), LightGBM | Machine learning models for 3-hour rain classification and multi-step 24-hour load forecasting. |
| **Database & ORM** | PostgreSQL 16, SQLite, SQLAlchemy | Declarative ORM repositories, indexing, unique constraints, and schema migrations. |
| **Containerization** | Docker, Docker Compose | Decoupled multi-service container orchestration (`db`, `backend`, `frontend`). |
| **Quality Assurance** | Pytest, TestClient | Automated test suite with 114 unit, integration, API, and E2E tests (100% pass rate). |

---

## 15-Stage System Development Lifecycle

1. **Stage 1 — Skeleton Architecture**: Database ORM models, configuration settings, and CLI launcher.
2. **Stage 2 — Data Ingestion**: REST ingestion for meteorological and power grid telemetries.
3. **Stage 3 — Data Quality Engine**: Range validation, duplicate filtering, linear interpolation, and audit metrics.
4. **Stage 4 — Rain Prediction ML**: Calibrated 3-hour precipitation probability classifier.
5. **Stage 5 — Energy Demand Forecaster**: Multi-step 24-hour LightGBM time-series load forecasting.
6. **Stage 6 — Anomaly Detection**: Statistical Z-Score and Isolation Forest engines for grid/weather extremes.
7. **Stage 7 — Weather Impact Analytics**: Load sensitivity metrics, correlation matrices, and HDD/CDD calculations.
8. **Stage 8 — What-If Scenario Simulator**: Grid stress-testing under hypothetical weather shocks without model retraining.
9. **Stage 9 — AI Energy Analyst**: Grounded LLM copilot with daily executive briefings and deterministic fallback.
10. **Stage 10 — Smart Alert Center**: Multi-tier alert engine with SHA-256 fingerprint deduplication and state tracking.
11. **Stage 11 — Dynamic Control Room UI**: Weather-reactive Streamlit dashboard with 10 interactive views.
12. **Stage 12 — FastAPI Backend**: Decoupled REST API layer with Pydantic V2 schemas and middleware.
13. **Stage 13 — Final Application Integration**: Decoupled frontend API client re-export facade (`api_client.py`).
14. **Stage 14 — Complete Testing & Audit**: Comprehensive quality audit and 100% test pass rate across 114 tests.
15. **Stage 15 — Production Deployment**: Docker multi-container orchestration, DB init script, and production API testing.

---

## Repository Structure

```
energy-intelligence-platform/
├── app/
│   ├── analytics/          # Weather impact & correlation engines
│   ├── backend/            # FastAPI routers, schemas, dependencies, middleware
│   ├── config/             # Pydantic settings management
│   ├── data/               # Ingestion, validation, and data quality modules
│   ├── database/           # ORM models, session engine, and repositories
│   ├── frontend/           # Streamlit Control Room views, components, API client
│   ├── models/             # ML inference models (Rain, Forecast, Anomaly, AI Analyst)
│   ├── services/           # Application service orchestration
│   └── utils/              # Formatting and logging utilities
├── docs/                   # Full system & module documentation
├── saved_models/           # Pre-trained ML model joblib artifacts
├── scripts/                # Utility scripts (init DB, train models, test endpoints)
├── tests/                  # Automated pytest test suite (114 tests)
├── Dockerfile              # Backend API Dockerfile
├── Dockerfile.frontend     # Streamlit UI Dockerfile
├── docker-compose.yml      # Multi-service container orchestration
├── .env.example            # Production environment template
├── requirements.txt        # Python package dependencies
└── run.py                  # Main runnable CLI launcher
```
