"""AI Energy Analyst API Router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session
from app.backend.api.schemas.ai import AIQueryRequest, AIResponseDTO
from app.services.ai_analyst_service import AIEnergyAnalystService

router = APIRouter(prefix="/ai", tags=["AI Energy Analyst"])


@router.post("/analyze", response_model=AIResponseDTO, summary="Query Grounded AI Energy Analyst")
def analyze_grid_query(
    request: AIQueryRequest,
    db: Session = Depends(get_database_session)
):
    """Executes Stage 9 AI Energy Analyst query against real grid telemetries and model outputs."""
    service = AIEnergyAnalystService(db)
    
    try:
        resp = service.ask_question(question=request.question, region=request.region or settings.DEFAULT_REGION)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI Analyst processing error: {str(e)}")

    if not resp:
        raise HTTPException(status_code=503, detail="AI Analyst service unavailable.")

    # Convert Pydantic or Dict response schema
    summary_val = getattr(resp, "summary", "No insight generated.")
    key_findings_val = getattr(resp, "key_findings", [])
    evidence_val = getattr(resp, "evidence", {})
    warnings_val = getattr(resp, "warnings", [])
    limitations_val = getattr(resp, "limitations", "Response based on current database state.")
    provider_val = getattr(resp, "provider_used", getattr(resp, "provider", "Stage 9 Rule Engine"))

    if isinstance(evidence_val, list):
        evidence_val = {"details": evidence_val}

    return AIResponseDTO(
        summary=str(summary_val),
        key_findings=[str(kf) for kf in key_findings_val],
        evidence=evidence_val if isinstance(evidence_val, dict) else {},
        warnings=[str(w) for w in warnings_val],
        limitations=str(limitations_val),
        provider=str(provider_val)
    )
