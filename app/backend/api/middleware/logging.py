"""
FastAPI Request ID and Structured Logging Middleware.
"""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestIDAndLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware capturing request duration, generating X-Request-ID header, and structured logging."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
        except Exception as e:
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"[{request_id}] {request.method} {request.url.path} FAILED in {process_time_ms:.2f}ms: {e}")
            raise e

        process_time_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> Status: {response.status_code} ({process_time_ms:.2f}ms)"
        )
        return response
