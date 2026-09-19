"""FastAPI Backend API Schemas Package."""

from app.backend.api.schemas.common import (
    APIErrorResponse,
    HealthResponse,
    DatabaseHealthResponse,
    ServicesHealthResponse,
    PaginatedResponse
)
from app.backend.api.schemas.weather import WeatherDataDTO, WeatherSummaryDTO
from app.backend.api.schemas.energy import EnergyDataDTO, EnergySummaryDTO
from app.backend.api.schemas.forecast import ForecastPointDTO, ForecastResponseDTO, ForecastSummaryDTO
from app.backend.api.schemas.rain import RainPredictionDTO, RainHistoryItemDTO
from app.backend.api.schemas.anomaly import AnomalyDTO, AnomalySummaryDTO
from app.backend.api.schemas.alert import AlertDTO, AcknowledgeAlertRequest, ResolveAlertRequest, AlertSummaryDTO
from app.backend.api.schemas.simulator import SimulationRequest, SimulationResultDTO
from app.backend.api.schemas.ai import AIQueryRequest, AIResponseDTO
from app.backend.api.schemas.analytics import WeatherImpactDTO, PeakDemandDTO
from app.backend.api.schemas.data_quality import DataQualityAuditDTO
