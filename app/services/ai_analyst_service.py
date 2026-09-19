"""
AI Energy Analyst Service (Stage 9)
===================================

Service orchestrator linking database contexts, LLM/Deterministic Analyst
providers, numerical grounding validators, cache, and ORM persistence.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.repository import AIInsightRepository
from app.models.ai_analyst.schemas import DailyIntelligenceReport, AnalystResponseSchema, AnalystContext
from app.models.ai_analyst.context_builder import build_analyst_context
from app.models.ai_analyst.daily_intelligence import generate_daily_intelligence
from app.models.ai_analyst.qa_engine import ask_energy_analyst
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIEnergyAnalystService:
    """Service layer managing AI Energy Analyst workflows."""

    def __init__(self, db: Optional[Session] = None):
        """Initializes service with an optional database session."""
        self._db = db

    def generate_daily_report(
        self,
        region: str = "Grid_Alpha",
        force_refresh: bool = False,
        save_to_db: bool = True
    ) -> DailyIntelligenceReport:
        """Generates grounded Daily Intelligence Report for given region.

        Args:
            region (str): Grid region identifier.
            force_refresh (bool): Bypass caching if True.
            save_to_db (bool): Persist generated report to database if True.

        Returns:
            DailyIntelligenceReport: Grounded daily executive report.
        """
        db_context = self._db
        close_session = False
        if db_context is None:
            db_context = SessionLocal()
            close_session = True

        try:
            context: AnalystContext = build_analyst_context(db_context, region=region)
            report: DailyIntelligenceReport = generate_daily_intelligence(context, force_refresh=force_refresh)

            if save_to_db and db_context is not None:
                record_dict = {
                    "insight_type": "daily_intelligence",
                    "region": region,
                    "ai_provider": report.provider_used,
                    "model_version": report.model_version,
                    "summary_text": report.executive_summary,
                    "response_json": report.model_dump(),
                    "context_hash": report.context_hash
                }
                insight_id = AIInsightRepository.save_insight(db_context, record_dict)
                logger.info(f"Daily intelligence report saved with DB ID: {insight_id}")

            return report
        finally:
            if close_session and db_context is not None:
                db_context.close()

    def ask_question(
        self,
        question: str,
        region: str = "Grid_Alpha",
        force_refresh: bool = False,
        save_to_db: bool = True
    ) -> AnalystResponseSchema:
        """Answers energy/weather user question using grounded system context.

        Args:
            question (str): User query string.
            region (str): Grid region identifier.
            force_refresh (bool): Bypass caching if True.
            save_to_db (bool): Persist Q&A exchange to database if True.

        Returns:
            AnalystResponseSchema: Grounded Q&A response schema.
        """
        db_context = self._db
        close_session = False
        if db_context is None:
            db_context = SessionLocal()
            close_session = True

        try:
            context: AnalystContext = build_analyst_context(db_context, region=region)
            response: AnalystResponseSchema = ask_energy_analyst(question, context, force_refresh=force_refresh)

            if save_to_db and db_context is not None:
                record_dict = {
                    "insight_type": "user_qa",
                    "region": region,
                    "ai_provider": response.provider_used,
                    "model_version": response.model_version,
                    "summary_text": f"Q: {question} | A: {response.summary}",
                    "response_json": response.model_dump(),
                    "context_hash": response.context_hash
                }
                insight_id = AIInsightRepository.save_insight(db_context, record_dict)
                logger.info(f"User Q&A insight saved with DB ID: {insight_id}")

            return response
        finally:
            if close_session and db_context is not None:
                db_context.close()

    def get_latest_daily_report(self, region: str = "Grid_Alpha") -> Optional[Dict[str, Any]]:
        """Retrieves most recent persisted daily intelligence report from database."""
        db_context = self._db
        close_session = False
        if db_context is None:
            db_context = SessionLocal()
            close_session = True

        try:
            insight = AIInsightRepository.get_latest_insight(db_context, region=region, insight_type="daily_intelligence")
            if insight:
                import json
                return {
                    "id": insight.id,
                    "created_at": insight.created_at.isoformat() if insight.created_at else None,
                    "ai_provider": insight.ai_provider,
                    "model_version": insight.model_version,
                    "summary_text": insight.summary_text,
                    "data": json.loads(insight.response_json) if insight.response_json else {}
                }
            return None
        finally:
            if close_session and db_context is not None:
                db_context.close()
