# Stage 12 — FastAPI REST API Architecture & Endpoint Documentation

## Overview

The **AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform** includes a production-grade REST API backend built with **FastAPI** and **Pydantic V2**. 

The API layer acts as a decoupled interface between frontend applications (such as the Streamlit Energy Control Room) and core backend services, ML models, and repository layers.

---

## System Architecture

```
                               ┌────────────────────────────────┐
                               │   Streamlit / External UI      │
                               └───────────────┬────────────────┘
                                               │ HTTP / REST
                                               ▼
                               ┌────────────────────────────────┐
                               │     FastAPI Backend Router     │
                               │          (/api/v1)             │
                               └───────────────┬────────────────┘
                                               │ Middleware / Dependencies
                                               ▼
                               ┌────────────────────────────────┐
                               │      Application Services      │
                               │   (Forecast, Rain, AI, etc.)   │
                               └───────────────┬────────────────┘
                                               │ ORM Repositories
                                               ▼
                               ┌────────────────────────────────┐
                               │       SQLite Database          │
                               └────────────────────────────────┘
```

### Architectural Principles
1. **Zero Business Logic in Routes**: Route handlers delegate 100% of analytical calculations, ML invocations, and database queries to `app.services.*` and `app.database.repository.*`.
2. **Pydantic V2 Schema Validation**: Strict request and response schemas ensure type safety, validated query parameters, and predictable JSON payloads.
3. **Decoupled Client**: The Streamlit UI communicates with FastAPI via `app/frontend/api_client.py` with automatic fallback to local service execution if the API server is unavailable.

---

## Middleware & Global Handlers

### 1. Request ID & Latency Tracking (`RequestIDAndLoggingMiddleware`)
- Generates a unique `UUIDv4` for every incoming HTTP request (or respects incoming `X-Request-ID` headers).
- Attaches `X-Request-ID` and `X-Response-Time-MS` to response headers.
- Logs structured request metadata (HTTP method, path, status code, latency).

### 2. CORS Security (`CORSMiddleware`)
- Configured via `CORS_ALLOWED_ORIGINS` in `app/config/settings.py`.
- Restricts cross-origin browser requests to trusted origins.

### 3. Global Exception Handler (`global_exception_handler`)
- Catches uncaught runtime exceptions gracefully.
- Returns a standardized JSON response (`500 Internal Server Error`) with the `X-Request-ID` trace reference without leaking sensitive tracebacks.

---

## Base Configuration

- **API Base Prefix**: `/api/v1`
- **Interactive Documentation**:
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

---

## Route Groups & Endpoints

### 1. System Health (`/health`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Overall system operational status check |
| `GET` | `/health/db` | Database connection ping and query health check |
| `GET` | `/health/services` | Internal service readiness inspection |

### 2. Weather Analytics (`/api/v1/weather`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/weather/latest` | Retrieve most recent weather observations by region |
| `GET` | `/api/v1/weather/history` | Historical weather observations with date range filtering |
| `GET` | `/api/v1/weather/regions` | List all available monitored geographical regions |

### 3. Energy Demand (`/api/v1/energy`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/energy/latest` | Current energy consumption metrics |
| `GET` | `/api/v1/energy/history` | Historical energy consumption time-series |
| `GET` | `/api/v1/energy/peak-demand` | Peak energy demand analysis and threshold breaches |

### 4. Energy Demand Forecasting (`/api/v1/forecast`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/forecast/demand` | Generate energy demand forecast for specified horizon (6h, 12h, 24h, 48h, 72h) |
| `GET` | `/api/v1/forecast/accuracy` | Model accuracy evaluation metrics (MAE, RMSE, MAPE) |

### 5. Rain Prediction ML (`/api/v1/rain`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/rain/predict` | ML precipitation probability & classification for given weather inputs |
| `GET` | `/api/v1/rain/feature-importance` | Model feature importance rankings for precipitation prediction |

### 6. Anomaly Detection (`/api/v1/anomalies`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/anomalies/detect` | Run real-time energy & weather anomaly detection |
| `GET` | `/api/v1/anomalies/recent` | Fetch recently logged anomalies with severity levels |

### 7. Smart Alert Center (`/api/v1/alerts`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/alerts` | Query system alerts (filter by severity, status, category) |
| `GET` | `/api/v1/alerts/summary` | Alert distribution summary counts by severity |
| `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | Acknowledge active alert state transition |
| `POST` | `/api/v1/alerts/{alert_id}/resolve` | Resolve active or acknowledged alert |

### 8. What-If Scenario Simulator (`/api/v1/simulator`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/simulator/run` | Execute custom what-if weather scenario simulation |

### 9. AI Energy Analyst (`/api/v1/ai`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/ai/analyze` | Request natural language energy insights & analytical summaries |

### 10. Weather Impact Analytics (`/api/v1/analytics`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/correlations` | Compute Pearson/Spearman correlation matrix between weather & energy |
| `GET` | `/api/v1/analytics/summary` | Executive weather impact analytical summary |

### 11. Data Quality & Pipeline (`/api/v1/data-quality`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/data-quality/metrics` | Retrieve pipeline data quality validation scores |
| `GET` | `/api/v1/data-quality/quarantine` | Inspect quarantined data records failing quality checks |

---

## Running the API Server

To start the FastAPI backend server independently:

```bash
# Using Python runner script
py run.py api

# Or directly using Uvicorn
uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Running Verification Tests

To verify all REST API endpoints and integration tests:

```bash
py run.py test
```
