"""Energy Demand Forecasting Package."""

from app.models.energy_forecasting.features import extract_forecasting_features, create_forecasting_target
from app.models.energy_forecasting.baselines import NaiveForecaster, SeasonalNaiveForecaster
from app.models.energy_forecasting.train import EnergyModelTrainer, evaluate_forecaster
from app.models.energy_forecasting.backtesting import ExpandingWindowCV
from app.models.energy_forecasting.peak_analysis import analyze_peak_demand

__all__ = [
    "extract_forecasting_features",
    "create_forecasting_target",
    "NaiveForecaster",
    "SeasonalNaiveForecaster",
    "EnergyModelTrainer",
    "evaluate_forecaster",
    "ExpandingWindowCV",
    "analyze_peak_demand",
]
