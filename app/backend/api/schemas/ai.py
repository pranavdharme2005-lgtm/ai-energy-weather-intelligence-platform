"""AI Energy Analyst API Pydantic Schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AIQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="User question regarding energy demand, weather, or anomalies")
    region: Optional[str] = "Grid_Alpha"
    location: Optional[str] = "Mumbai"


class AIResponseDTO(BaseModel):
    summary: str
    key_findings: List[str]
    evidence: Dict[str, Any]
    warnings: List[str]
    limitations: str
    provider: str
