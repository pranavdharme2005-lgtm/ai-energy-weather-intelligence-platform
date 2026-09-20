"""
Unified REST API Client package facade for Stage 13 Control Room UI.
"""

from typing import Dict, Any, List, Optional
from app.frontend.api.client import BaseAPIClient
from app.frontend.api.weather_api import WeatherAPIClient
from app.frontend.api.energy_api import EnergyAPIClient
from app.frontend.api.forecast_api import ForecastAPIClient
from app.frontend.api.rain_api import RainAPIClient
from app.frontend.api.anomalies_api import AnomaliesAPIClient
from app.frontend.api.alerts_api import AlertsAPIClient
from app.frontend.api.simulator_api import SimulatorAPIClient
from app.frontend.api.ai_api import AIAnalystAPIClient
from app.frontend.api.analytics_api import AnalyticsAPIClient
from app.frontend.api.data_quality_api import DataQualityAPIClient


class EnergyIntelligenceAPIClient:
    """Unified API Client facade composing domain wrappers."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_client = BaseAPIClient(base_url=base_url)
        self.weather = WeatherAPIClient(self.base_client)
        self.energy = EnergyAPIClient(self.base_client)
        self.forecast = ForecastAPIClient(self.base_client)
        self.rain = RainAPIClient(self.base_client)
        self.anomalies = AnomaliesAPIClient(self.base_client)
        self.alerts = AlertsAPIClient(self.base_client)
        self.simulator = SimulatorAPIClient(self.base_client)
        self.ai = AIAnalystAPIClient(self.base_client)
        self.analytics = AnalyticsAPIClient(self.base_client)
        self.data_quality = DataQualityAPIClient(self.base_client)

    def get_health(self) -> Dict[str, Any]:
        """Health check delegate."""
        return self.base_client.check_health()

    # Delegate methods for convenient direct top-level access
    def get_current_weather(self, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.weather.get_current_weather(location=location)

    def get_weather_history(self, location: Optional[str] = None, limit: int = 48) -> List[Dict[str, Any]]:
        return self.weather.get_weather_history(location=location, limit=limit)

    def get_weather_summary(self, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.weather.get_weather_summary(location=location)

    def get_current_energy(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.energy.get_current_energy(region=region)

    def get_energy_history(self, region: Optional[str] = None, limit: int = 48) -> List[Dict[str, Any]]:
        return self.energy.get_energy_history(region=region, limit=limit)

    def get_peak_demand(self, region: Optional[str] = None, threshold_mw: Optional[float] = None) -> Optional[Dict[str, Any]]:
        return self.energy.get_peak_demand(region=region, threshold_mw=threshold_mw)

    def get_forecast(self, region: Optional[str] = None, horizon_hours: int = 24) -> Optional[Dict[str, Any]]:
        return self.forecast.get_forecast(region=region, horizon_hours=horizon_hours)

    def get_latest_forecast(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.forecast.get_forecast(region=region, horizon_hours=24)

    def get_forecast_accuracy(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.forecast.get_forecast_accuracy(region=region)

    def predict_rain(self, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.rain.predict_rain(location=location)

    def get_rain_feature_importance(self) -> Optional[Dict[str, Any]]:
        return self.rain.get_feature_importance()

    def detect_anomalies(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.anomalies.detect_anomalies(region=region)

    def get_recent_anomalies(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.anomalies.get_recent_anomalies(limit=limit)

    def get_alerts(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return self.alerts.get_alerts(status=status, limit=limit)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return self.alerts.get_alerts(status="ACTIVE")

    def get_alert_summary(self) -> Optional[Dict[str, Any]]:
        return self.alerts.get_alert_summary()

    def acknowledge_alert(self, alert_id: int) -> bool:
        return self.alerts.acknowledge_alert(alert_id)

    def resolve_alert(self, alert_id: int) -> bool:
        return self.alerts.resolve_alert(alert_id)

    def run_simulation(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.simulator.run_simulation(request_data)

    def ask_ai_analyst(self, question: str, region: Optional[str] = None, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.ai.ask_ai_analyst(question=question, region=region, location=location)

    def get_correlations(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.analytics.get_correlations(region=region)

    def get_analytics_summary(self, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.analytics.get_analytics_summary(region=region)

    def get_data_quality_metrics(self) -> Optional[Dict[str, Any]]:
        return self.data_quality.get_metrics()

    def get_data_quality_quarantine(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.data_quality.get_quarantine(limit=limit)


api_client = EnergyIntelligenceAPIClient()

__all__ = [
    "EnergyIntelligenceAPIClient",
    "BaseAPIClient",
    "WeatherAPIClient",
    "EnergyAPIClient",
    "ForecastAPIClient",
    "RainAPIClient",
    "AnomaliesAPIClient",
    "AlertsAPIClient",
    "SimulatorAPIClient",
    "AIAnalystAPIClient",
    "AnalyticsAPIClient",
    "DataQualityAPIClient",
    "api_client",
]
