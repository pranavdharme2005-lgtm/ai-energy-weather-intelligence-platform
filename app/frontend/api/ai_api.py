"""AI Energy Analyst REST API Client wrapper."""

from typing import Dict, Any, Optional
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.services.ai_analyst_service import AIEnergyAnalystService
from app.database.session import SessionLocal


class AIAnalystAPIClient:
    """API Client for AI Energy Analyst endpoints with fallback to service."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def ask_ai_analyst(self, question: str, region: Optional[str] = None, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Posts to /ai/analyze endpoint."""
        reg = region or settings.DEFAULT_REGION
        loc = location or settings.DEFAULT_LOCATION
        payload = {"question": question, "region": reg, "location": loc}
        res = self.client.post("/ai/analyze", json_data=payload)
        if res:
            return res

        db = SessionLocal()
        try:
            svc = AIEnergyAnalystService(db)
            if "briefing" in question.lower() or "summary" in question.lower():
                report = svc.generate_daily_report(region=reg, location=loc)
                return report.model_dump()
            resp = svc.ask_question(question, region=reg, location=loc)
            return resp.model_dump()
        except Exception:
            return None
        finally:
            db.close()
