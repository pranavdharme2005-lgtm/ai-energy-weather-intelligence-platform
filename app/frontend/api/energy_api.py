"""Energy Demand REST API Client wrapper."""

from typing import Dict, Any, List, Optional
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.database.session import SessionLocal
from app.database.repository import EnergyRepository


class EnergyAPIClient:
    """API Client for Energy Demand endpoints with fallback to repository."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def get_current_energy(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /energy/current endpoint."""
        reg = region or settings.DEFAULT_REGION
        res = self.client.get("/energy/current", params={"region": reg})
        if res:
            return res

        db = SessionLocal()
        try:
            records = EnergyRepository.get_latest(db, region=reg, limit=1)
            if records:
                r = records[0]
                return {
                    "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                    "region": r.region,
                    "demand_mw": r.demand_mw,
                    "unit": r.unit or "MW",
                    "is_peak": getattr(r, "is_peak", False),
                    "source": r.source or "Local DB"
                }
        except Exception:
            pass
        finally:
            db.close()
        return None

    def get_energy_history(self, region: Optional[str] = None, limit: int = 48) -> List[Dict[str, Any]]:
        """Queries /energy/history endpoint."""
        reg = region or settings.DEFAULT_REGION
        res = self.client.get("/energy/history", params={"region": reg, "limit": limit})
        if res and isinstance(res, list):
            return res

        db = SessionLocal()
        try:
            records = EnergyRepository.get_latest(db, region=reg, limit=limit)
            return [
                {
                    "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                    "region": r.region,
                    "demand_mw": r.demand_mw,
                    "unit": r.unit or "MW",
                    "is_peak": getattr(r, "is_peak", False),
                    "source": r.source or "Local DB"
                } for r in records
            ]
        except Exception:
            return []
        finally:
            db.close()

    def get_peak_demand(self, region: Optional[str] = None, threshold_mw: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Queries /energy/peak-demand endpoint with local repository fallback."""
        reg = region or settings.DEFAULT_REGION
        params = {"region": reg}
        if threshold_mw:
            params["threshold_mw"] = threshold_mw
        res = self.client.get("/energy/peak-demand", params=params)
        if res:
            return res

        db = SessionLocal()
        try:
            recs = EnergyRepository.get_latest(db, region=reg, limit=48)
            if recs:
                demands = [r.demand_mw for r in recs]
                peak_val = max(demands)
                t_limit = threshold_mw or settings.ENERGY_SPIKE_THRESHOLD_MW
                peak_rec = next((r for r in recs if r.demand_mw == peak_val), recs[0])
                return {
                    "region": reg,
                    "peak_demand_mw": peak_val,
                    "threshold_mw": t_limit,
                    "threshold_exceeded": peak_val >= t_limit,
                    "peak_timestamp": peak_rec.timestamp.isoformat() if hasattr(peak_rec.timestamp, 'isoformat') else str(peak_rec.timestamp),
                    "sample_count": len(recs)
                }
        except Exception:
            pass
        finally:
            db.close()
        return None

