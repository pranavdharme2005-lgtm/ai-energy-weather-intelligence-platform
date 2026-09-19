"""FastAPI Main Application Server Entry Point (Stage 12 & 13)."""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.utils.logger import get_logger
from app.database.session import init_db

# Import middleware
from app.backend.api.middleware.logging import RequestIDAndLoggingMiddleware

# Import modular route handlers
from app.backend.api.routes import (
    health,
    weather,
    energy,
    forecast,
    rain,
    anomalies,
    alerts,
    simulator,
    ai_analyst,
    analytics,
    data_quality
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing DB tables on startup."""
    logger.info("Starting up Energy Intelligence FastAPI Server v1.0.0 (Stage 13)...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error initializing DB on startup: {e}")
    yield
    logger.info("Shutting down Energy Intelligence FastAPI Server...")


def create_application() -> FastAPI:
    """FastAPI Application Factory."""
    app_instance = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Production-grade REST API backend for real-time energy intelligence, weather analytics, "
            "ML load forecasting, anomaly detection, scenario simulation, AI analyst queries, and smart alerts."
        ),
        version="1.0.0-stage13",
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 1. Custom Request ID and Logging Middleware
    app_instance.add_middleware(RequestIDAndLoggingMiddleware)

    # 2. Configure CORS
    allowed_origins = [orig.strip() for orig in settings.CORS_ALLOWED_ORIGINS.split(",") if orig.strip()]
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if allowed_origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Global Exception Handler
    @app_instance.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global Unhandled Exception at {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred while processing the request.",
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    # 4. Root Endpoint
    @app_instance.get("/", tags=["Platform Overview"])
    def root():
        """Root status response providing API sitemap links."""
        return {
            "app_name": settings.APP_NAME,
            "version": "1.0.0-stage13",
            "documentation": {
                "swagger_ui": "/docs",
                "redoc_ui": "/redoc"
            },
            "health_check": f"{settings.API_PREFIX}/health",
            "api_v1_prefix": settings.API_PREFIX
        }

    # 5. Include Health Router at root level and API prefix for max compatibility
    app_instance.include_router(health.router)
    
    api_prefix = settings.API_PREFIX
    app_instance.include_router(health.router, prefix=api_prefix)
    app_instance.include_router(weather.router, prefix=api_prefix)
    app_instance.include_router(energy.router, prefix=api_prefix)
    app_instance.include_router(forecast.router, prefix=api_prefix)
    app_instance.include_router(rain.router, prefix=api_prefix)
    app_instance.include_router(anomalies.router, prefix=api_prefix)
    app_instance.include_router(alerts.router, prefix=api_prefix)
    app_instance.include_router(simulator.router, prefix=api_prefix)
    app_instance.include_router(ai_analyst.router, prefix=api_prefix)
    app_instance.include_router(analytics.router, prefix=api_prefix)
    app_instance.include_router(data_quality.router, prefix=api_prefix)

    return app_instance


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
