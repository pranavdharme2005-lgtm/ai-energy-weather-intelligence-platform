import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.frontend.api import EnergyIntelligenceAPIClient, api_client

__all__ = ["EnergyIntelligenceAPIClient", "api_client"]

