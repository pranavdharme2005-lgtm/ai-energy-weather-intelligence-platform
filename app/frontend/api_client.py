"""
Frontend REST API Client for Stage 13 Control Room UI.

Communicates with FastAPI backend (/api/v1/) over HTTP REST API.
Re-exports unified EnergyIntelligenceAPIClient facade and api_client instance.
"""

from app.frontend.api import EnergyIntelligenceAPIClient, api_client

__all__ = ["EnergyIntelligenceAPIClient", "api_client"]
