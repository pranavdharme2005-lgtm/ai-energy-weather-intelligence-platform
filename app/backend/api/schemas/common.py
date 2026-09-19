"""Common API Pydantic Schemas."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetails(BaseModel):
    code: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class APIErrorResponse(BaseModel):
    """Standardized API Error Response wrapper."""
    error: ErrorDetails


class HealthResponse(BaseModel):
    """System Liveness Health Response."""
    status: str
    app_name: str
    environment: str
    version: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class DatabaseHealthResponse(BaseModel):
    """Database connectivity health check response."""
    status: str
    database_type: str
    connected: bool
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ServicesHealthResponse(BaseModel):
    """Major internal services availability status response."""
    status: str
    services: Dict[str, str]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list container."""
    total: int
    limit: int
    offset: int
    items: List[T]
