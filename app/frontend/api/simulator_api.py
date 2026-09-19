"""What-If Scenario Simulator REST API Client wrapper."""

from typing import Dict, Any, Optional
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.services.simulator import WhatIfSimulatorService
from app.database.session import SessionLocal


class SimulatorAPIClient:
    """API Client for What-If Scenario Simulator endpoints with fallback to service."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def run_simulation(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Posts to /simulator/run endpoint."""
        res = self.client.post("/simulator/run", json_data=request_data)
        if res:
            return res

        # Fallback to local simulator service
        db = SessionLocal()
        try:
            overrides = request_data.get("scenario_overrides", {})
            region = request_data.get("region", settings.DEFAULT_REGION)
            horizon_hours = request_data.get("horizon_hours", 24)
            sim_res = WhatIfSimulatorService.run_scenario(
                db=db,
                scenario_overrides=overrides,
                region=region,
                horizon_hours=horizon_hours
            )
            return sim_res
        except Exception:
            return None
        finally:
            db.close()
