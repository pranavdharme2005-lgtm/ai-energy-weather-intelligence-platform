"""
FastAPI Backend API Dependencies.

Provides database session dependency and query validation utilities.
"""

from typing import Generator
from fastapi import Query
from sqlalchemy.orm import Session
from app.database.session import get_db


def get_database_session() -> Generator[Session, None, None]:
    """Yields a database session from SessionLocal generator."""
    yield from get_db()


class PaginationParams:
    """Common pagination and limit parameters for list endpoints."""
    def __init__(
        self,
        limit: int = Query(default=50, ge=1, le=500, description="Maximum records to return"),
        offset: int = Query(default=0, ge=0, description="Offset position for pagination")
    ):
        self.limit = limit
        self.offset = offset
