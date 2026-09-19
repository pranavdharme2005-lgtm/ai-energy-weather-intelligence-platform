"""Abstract Provider Interfaces for Weather and Energy Data Ingestion."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional


class WeatherProvider(ABC):
    """Abstract Base Class for meteorological data providers."""

    @abstractmethod
    def fetch_current_weather(
        self, location: str, latitude: float, longitude: float
    ) -> List[Dict[str, Any]]:
        """Fetch current weather telemetry records normalized to internal schema."""
        pass

    @abstractmethod
    def fetch_historical_weather(
        self, location: str, latitude: float, longitude: float, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch historical weather telemetry records normalized to internal schema."""
        pass


class EnergyProvider(ABC):
    """Abstract Base Class for power grid load providers."""

    @abstractmethod
    def fetch_energy_demand(
        self, region: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch regional grid energy load telemetries normalized to internal schema."""
        pass
