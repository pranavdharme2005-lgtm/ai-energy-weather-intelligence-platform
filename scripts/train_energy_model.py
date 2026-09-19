"""CLI Training Script for Energy Demand Forecasting Machine Learning Module."""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import settings
from app.data.providers.open_energy import OpenEnergyProvider
from app.data.providers.open_meteo import OpenMeteoWeatherProvider
from app.models.energy_forecasting.train import EnergyModelTrainer
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_training_energy_dataset(region: str = "Grid_Alpha", days: int = 60) -> pd.DataFrame:
    """Fetches or generates 60 days of hourly energy load and weather time series for training."""
    logger.info(f"Generating training dataset for region={region} over past {days} days...")
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=24 * days, freq="1h", tz="UTC")
    n = len(timestamps)

    hours = timestamps.hour
    dow = timestamps.dayofweek

    # Dual-peak load curve with weekly cycle variation
    base_load = 2800.0 + 650.0 * np.sin((hours - 4) * np.pi / 12) + 320.0 * np.cos((hours - 14) * np.pi / 6)
    weekend_reduction = np.where(dow >= 5, 250.0, 0.0)
    temps = 18.0 + 7.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 2.0, n)
    temp_impact = (temps - 20.0) ** 2 * 3.5  # Heating/cooling degree load impact

    demands = np.round(base_load - weekend_reduction + temp_impact + np.random.normal(0, 45, n), 2)
    humids = np.clip(np.round(65.0 - 20.0 * np.sin((hours - 8) * np.pi / 12) + np.random.normal(0, 5.0, n), 2), 15.0, 100.0)
    pressures = np.round(1013.25 + np.random.normal(0, 6.0, n), 2)
    winds = np.round(np.abs(4.0 + np.random.normal(0, 2.0, n)), 2)
    clouds = np.clip(np.round(45.0 + np.random.normal(0, 30.0, n), 2), 0.0, 100.0)
    precips = np.where(np.random.rand(n) < 0.15, np.random.exponential(2.5, n), 0.0)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "region": region,
        "demand_mw": demands,
        "temperature_c": temps,
        "humidity_pct": humids,
        "pressure_hpa": pressures,
        "wind_speed_ms": winds,
        "cloud_cover_pct": clouds,
        "precipitation_mm": precips,
        "rain_probability": np.clip(precips * 0.3, 0.0, 1.0)
    })

    return df


def main():
    parser = argparse.ArgumentParser(description="Train Energy Demand Forecaster ML Model")
    parser.add_argument("--region", type=str, default="Grid_Alpha")
    parser.add_argument("--days", type=int, default=60, help="Training history window in days")
    parser.add_argument("--horizon", type=int, default=24, help="Forecast horizon in hours")
    parser.add_argument(
        "--model",
        type=str,
        default="random_forest",
        choices=["naive_baseline", "seasonal_naive", "ridge_regression", "random_forest", "hist_gradient_boosting"],
        help="Target regression forecasting algorithm"
    )

    args = parser.parse_args()

    df_train = generate_training_energy_dataset(region=args.region, days=args.days)
    logger.info(f"Loaded {len(df_train)} hourly energy observation records for ML training.")

    model, meta = EnergyModelTrainer.train_and_evaluate(df_train, horizon_hours=args.horizon, model_type=args.model)

    print("\n" + "=" * 70)
    print("STAGE 5: ENERGY DEMAND FORECASTING ML MODEL BENCHMARK & EVALUATION")
    print("=" * 70)
    print(f"Selected Candidate Algorithm : {meta['model_name'].upper()}")
    print(f"Model Artifact Version       : {meta['model_version']}")
    print(f"Detected Data Frequency      : {meta['data_frequency']}")
    print(f"Forecast Horizon             : {meta['forecast_horizon']}")
    print(f"95% Prediction Interval Band : +/- {meta['margin_95']} MW")
    print(f"Train Records                : {meta['train_records']} | Test Records: {meta['test_records']}")

    print("\nCandidate Models Benchmark Evaluation:")
    print(f"{'Model Name':<24} | {'Val MAE':<9} | {'Val RMSE':<9} | {'Val sMAPE':<10} | {'Test MAE':<9} | {'Test RMSE':<9}")
    print("-" * 82)

    for m_name, ev in meta["candidate_evaluations"].items():
        val_m = ev["val"]
        test_m = ev["test"]
        print(
            f"{m_name:<24} | {val_m['mae']:<9.2f} | {val_m['rmse']:<9.2f} | "
            f"{val_m['smape']:<10.2f}% | {test_m['mae']:<9.2f} | {test_m['rmse']:<9.2f}"
        )

    print("\nExpanding Window Cross-Validation Backtest Metrics:")
    bt = meta["backtest_results"]
    print(f"  • Backtest Folds Evaluated: {bt.get('folds', 0)}")
    print(f"  • Mean Backtest MAE      : {bt.get('mae', 0.0)} MW")
    print(f"  • Mean Backtest RMSE     : {bt.get('rmse', 0.0)} MW")
    print(f"  • Mean Backtest sMAPE    : {bt.get('smape', 0.0)} %")

    if meta.get("feature_importance"):
        print("\nTop Predictor Feature Importance Ranking:")
        for feat, imp in list(meta["feature_importance"].items())[:10]:
            print(f"  • {feat:28s}: {imp:.4f} ({imp * 100:.1f}%)")

    print("\n" + "=" * 70)
    logger.info("Energy Demand Forecaster Training Job finished successfully.")


if __name__ == "__main__":
    main()
