"""Rain Prediction REST API Client wrapper."""

from typing import Dict, Any, Optional
import pandas as pd
from app.frontend.api.client import BaseAPIClient
from app.config.settings import settings
from app.database.session import SessionLocal
from app.database.repository import WeatherRepository
from app.models.rain_predictor import RainPredictor


class RainAPIClient:
    """API Client for Rain Prediction endpoints with fallback to local model."""

    def __init__(self, base_client: BaseAPIClient):
        self.client = base_client

    def predict_rain(self, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries /rain/current or /rain/predict endpoint."""
        loc = location or settings.DEFAULT_LOCATION
        res = self.client.get("/rain/current", params={"location": loc})
        if res:
            return res

        res_predict = self.client.get("/rain/predict", params={"location": loc})
        if res_predict:
            return res_predict

        # Fallback to local RainPredictor model
        db = SessionLocal()
        try:
            records = WeatherRepository.get_latest(db, location=loc, limit=1)
            if records:
                latest_w = records[0]
                w_df = pd.DataFrame([{
                    "timestamp": latest_w.timestamp,
                    "temperature_c": latest_w.temperature_c,
                    "humidity_pct": latest_w.humidity_pct,
                    "pressure_hpa": latest_w.pressure_hpa,
                    "wind_speed_ms": latest_w.wind_speed_ms,
                    "cloud_cover_pct": latest_w.cloud_cover_pct,
                    "precipitation_mm": latest_w.precipitation_mm
                }])
                predictor = RainPredictor()
                result = predictor.predict(w_df)
                return {
                    "prediction": "Rain Likely" if result.rain_predicted else "No Rain Expected",
                    "probability": round(result.probability, 4),
                    "rain_predicted": result.rain_predicted,
                    "confidence_level": "High",
                    "timestamp": latest_w.timestamp.isoformat() if hasattr(latest_w.timestamp, 'isoformat') else str(latest_w.timestamp),
                    "model_version": result.model_version
                }
        except Exception:
            pass
        finally:
            db.close()
        return None

    def get_feature_importance(self) -> Optional[Dict[str, Any]]:
        """Queries /rain/feature-importance endpoint."""
        return self.client.get("/rain/feature-importance")
