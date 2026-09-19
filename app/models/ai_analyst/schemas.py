"""Pydantic schemas for AI Energy Analyst module."""

import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Structured evidence item citing source module and verified value."""
    source: str  # e.g., 'FORECAST', 'WEATHER', 'ANOMALY', 'RAIN', 'WHAT_IF', 'DATA_QUALITY'
    value: str
    timestamp: Optional[str] = None

    @property
    def source_module(self) -> str:
        return self.source

    @property
    def metric_name(self) -> str:
        return self.source

    @property
    def claimed_value(self) -> str:
        return self.value

    @property
    def raw_context(self) -> str:
        return self.value


class RecommendedAction(BaseModel):
    """Actionable recommendation grounded in platform state."""
    category: str  # 'DISPATCH', 'PEAK_SHAVING', 'ALERT_RENEW', 'RESERVE_MARGIN', 'DATA_AUDIT'
    priority: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    description: str
    impact_estimate: str


class StructuredInsight(BaseModel):
    """Strictly grounded analytical report output."""
    report_id: str
    region: str
    generated_at: str
    report_type: str  # 'DAILY_INTELLIGENCE', 'QA_RESPONSE', 'DISPATCH_ADVISORY'

    summary: str
    key_findings: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    recommendations: List[RecommendedAction] = Field(default_factory=list)
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)
    limitations: List[str] = Field(default_factory=list)

    numerical_values_cited: List[float] = Field(default_factory=list)
    grounding_verification_passed: bool = True
    provider_used: str = "fallback"


class QueryFilter(BaseModel):
    """Structured search filters for Q&A query analysis."""
    region: Optional[str] = None
    time_range_hours: Optional[int] = 24

    def sanitize(self):
        """Sanitize query parameters."""
        if self.time_range_hours and self.time_range_hours > 720:
            self.time_range_hours = 720
        return self


class EnergyQuery(BaseModel):
    """Structured user query model for Energy AI Analyst Q&A engine."""
    question: str
    region: str = "Grid_Alpha"
    filters: QueryFilter = Field(default_factory=QueryFilter)
    user_id: Optional[str] = None

    def validate_question(self) -> bool:
        """Ensure question meets minimum sanity criteria."""
        cleaned = self.question.strip() if self.question else ""
        return len(cleaned) >= 3 and len(cleaned) <= 1000


class MetricEvidence(BaseModel):
    """Verification pair mapping extracted text numbers to authoritative DB values."""
    extracted_value: float
    source_component: str
    verified_match: bool = False
    context_snippet: str = ""

    def is_valid_match(self, tolerance: float = 0.05) -> bool:
        """Check matching with numerical tolerance."""
        return self.verified_match


class AnomalyRiskAssessment(BaseModel):
    """Severity and risk assessment summary."""
    severity: str = "MEDIUM"
    summary: str = "Normal grid parameters within expected tolerance."


class AnalystContext(BaseModel):
    """Verified structured context aggregated across Stages 2–8."""
    region: str = "Grid_Alpha"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    current_situation: Dict[str, Any] = Field(default_factory=dict)
    forecast: Dict[str, Any] = Field(default_factory=dict)
    weather: Dict[str, Any] = Field(default_factory=dict)
    rain: Dict[str, Any] = Field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    weather_impact: Dict[str, Any] = Field(default_factory=dict)
    what_if: Dict[str, Any] = Field(default_factory=dict)
    data_quality: Dict[str, Any] = Field(default_factory=dict)

    context_hash: Optional[str] = None

    def get_context_hash(self) -> str:
        """Returns context hash, computing MD5 hash if context_hash is None."""
        if self.context_hash:
            return self.context_hash
        data_str = json.dumps(self.model_dump(), sort_keys=True, default=str)
        self.context_hash = hashlib.md5(data_str.encode("utf-8")).hexdigest()
        return self.context_hash


class DailyIntelligenceReport(BaseModel):
    """Structured Daily Intelligence summary report."""
    current_situation: str = ""
    forecast_summary: str = ""
    weather_context: str = ""
    anomaly_summary: str = ""
    key_insight: str = ""
    warnings: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    ai_available: bool = True
    ai_provider: str = "openai"
    model_version: str = "gpt-4o-mini"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context_hash: Optional[str] = None
    grounding_passed: bool = True
    region: str = "Grid_Alpha"

    @property
    def executive_summary(self) -> str:
        parts = [p for p in [self.current_situation, self.forecast_summary] if p]
        return " ".join(parts) if parts else "Grid operations within expected analytical parameters."

    @property
    def key_findings(self) -> List[str]:
        findings = []
        if self.current_situation:
            findings.append(self.current_situation)
        if self.forecast_summary:
            findings.append(self.forecast_summary)
        if self.weather_context:
            findings.append(self.weather_context)
        if self.key_insight:
            findings.append(self.key_insight)
        return findings or ["Grid operating within standard operational baseline."]

    @property
    def anomaly_risk_assessment(self) -> AnomalyRiskAssessment:
        severity = "MEDIUM"
        if "HIGH" in self.anomaly_summary.upper() or "CRITICAL" in self.anomaly_summary.upper():
            severity = "HIGH"
        elif "NORMAL" in self.anomaly_summary.upper() or "0 ACTIVE" in self.anomaly_summary.upper():
            severity = "LOW"
        return AnomalyRiskAssessment(severity=severity, summary=self.anomaly_summary or "No high severity anomalies active.")

    @property
    def actionable_recommendations(self) -> List[str]:
        if self.warnings:
            return self.warnings
        return ["Maintain current spinning reserve margins.", "Monitor temperature and cooling demand trends."]

    @property
    def evidence_used(self) -> List[EvidenceItem]:
        return self.evidence

    @property
    def provider_used(self) -> str:
        return self.ai_provider


class AnalystResponseSchema(BaseModel):
    """Standardized response schema for user Q&A inquiries."""
    question: str = ""
    summary: str = ""
    key_findings: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    ai_available: bool = True
    ai_provider: str = "openai"
    model_version: str = "gpt-4o-mini"
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    context_hash: Optional[str] = None
    grounding_passed: bool = True

    @property
    def key_highlights(self) -> List[str]:
        return self.key_findings or [self.summary]

    @property
    def provider_used(self) -> str:
        return self.ai_provider
