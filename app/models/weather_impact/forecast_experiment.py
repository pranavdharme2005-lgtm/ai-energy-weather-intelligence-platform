"""Weather + Energy Forecasting Connection evaluation experiment submodule."""

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _calculate_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Symmetric Mean Absolute Percentage Error (sMAPE)."""
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    # Avoid zero division
    mask = denominator != 0
    if not np.any(mask):
        return 0.0
    smape = np.mean(np.abs(y_true[mask] - y_pred[mask]) / denominator[mask]) * 100.0
    return float(smape)


def evaluate_weather_forecasting_value(
    df: pd.DataFrame, test_ratio: float = 0.2
) -> Dict[str, Any]:
    """Compares forecasting performance between Baseline (Model A), Weather-Enhanced (Model B), and Weather+RainProb (Model C).

    Args:
        df: Cleaned analytical dataset containing demand, timestamp, and weather variables.
        test_ratio: Fraction of historical data reserved for chronological testing.

    Returns:
        Dict containing model evaluation metrics, MAE/RMSE comparisons, and weather feature importances.
    """
    if df.empty or "demand_mw" not in df.columns:
        return {"sufficient_data": False, "error": "Insufficient or missing demand data"}

    df_proc = df.copy()

    # Ensure chronological order
    if "timestamp" in df_proc.columns:
        df_proc["timestamp"] = pd.to_datetime(df_proc["timestamp"])
        df_proc = df_proc.sort_values("timestamp").reset_index(drop=True)

    # 1. Engineer Base Calendar & Demand Lags
    if "hour" not in df_proc.columns and "timestamp" in df_proc.columns:
        df_proc["hour"] = df_proc["timestamp"].dt.hour
        df_proc["dayofweek"] = df_proc["timestamp"].dt.dayofweek
        df_proc["is_weekend"] = df_proc["dayofweek"].isin([5, 6]).astype(int)

    # Base Demand Lags (past-only)
    df_proc["demand_lag_24h"] = df_proc["demand_mw"].shift(24)
    df_proc["demand_lag_48h"] = df_proc["demand_mw"].shift(48)
    df_proc["demand_roll_mean_24h"] = df_proc["demand_mw"].shift(1).rolling(24).mean()

    # Temperature degree days if available
    if "temperature_c" in df_proc.columns:
        if "cdd" not in df_proc.columns:
            df_proc["cdd"] = np.maximum(df_proc["temperature_c"] - 18.3, 0.0)
        if "hdd" not in df_proc.columns:
            df_proc["hdd"] = np.maximum(18.3 - df_proc["temperature_c"], 0.0)

    # Define Feature Sets
    baseline_features = [col for col in ["hour", "dayofweek", "is_weekend", "demand_lag_24h", "demand_lag_48h", "demand_roll_mean_24h"] if col in df_proc.columns]

    weather_candidate_features = [
        "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms",
        "cloud_cover_pct", "precipitation_mm", "cdd", "hdd"
    ]
    weather_features = [col for col in weather_candidate_features if col in df_proc.columns]

    rain_prob_features = [col for col in ["probability", "rain_predicted"] if col in df_proc.columns]

    if not baseline_features:
        return {"sufficient_data": False, "error": "Could not construct baseline features"}

    # Drop NaNs created by lagging
    all_needed_cols = ["demand_mw"] + list(set(baseline_features + weather_features + rain_prob_features))
    df_clean = df_proc.dropna(subset=all_needed_cols).reset_index(drop=True)

    if len(df_clean) < 50:
        logger.warning(f"Dataset too small ({len(df_clean)} samples) for forecasting evaluation experiment.")
        return {"sufficient_data": False, "error": f"Insufficient sample size ({len(df_clean)})"}

    # Chronological Split
    split_idx = int(len(df_clean) * (1.0 - test_ratio))
    train_df = df_clean.iloc[:split_idx]
    test_df = df_clean.iloc[split_idx:]

    y_train = train_df["demand_mw"].values
    y_test = test_df["demand_mw"].values

    results = {}
    weather_feature_importances = {}

    # --- Model A: Baseline (Demand + Calendar) ---
    X_train_A = train_df[baseline_features]
    X_test_A = test_df[baseline_features]

    model_A = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=10, n_jobs=-1)
    model_A.fit(X_train_A, y_train)
    pred_A = model_A.predict(X_test_A)

    mae_A = mean_absolute_error(y_test, pred_A)
    rmse_A = root_mean_squared_error(y_test, pred_A)
    smape_A = _calculate_smape(y_test, pred_A)

    results["model_A_baseline"] = {
        "description": "Historical demand lags + calendar time features",
        "features": baseline_features,
        "mae_mw": round(float(mae_A), 2),
        "rmse_mw": round(float(rmse_A), 2),
        "smape_pct": round(float(smape_A), 2),
    }

    # --- Model B: Baseline + Weather Features ---
    features_B = baseline_features + weather_features
    X_train_B = train_df[features_B]
    X_test_B = test_df[features_B]

    model_B = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=10, n_jobs=-1)
    model_B.fit(X_train_B, y_train)
    pred_B = model_B.predict(X_test_B)

    mae_B = mean_absolute_error(y_test, pred_B)
    rmse_B = root_mean_squared_error(y_test, pred_B)
    smape_B = _calculate_smape(y_test, pred_B)

    results["model_B_weather_enhanced"] = {
        "description": "Baseline features + physical weather features",
        "features": features_B,
        "mae_mw": round(float(mae_B), 2),
        "rmse_mw": round(float(rmse_B), 2),
        "smape_pct": round(float(smape_B), 2),
    }

    # Extract Weather Feature Importance from Model B
    importances_B = model_B.feature_importances_
    for feat, imp in zip(features_B, importances_B):
        if feat in weather_features:
            weather_feature_importances[feat] = round(float(imp), 4)

    # --- Model C: Baseline + Weather + Rain Probability (if available) ---
    if rain_prob_features:
        features_C = features_B + rain_prob_features
        X_train_C = train_df[features_C]
        X_test_C = test_df[features_C]

        model_C = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=10, n_jobs=-1)
        model_C.fit(X_train_C, y_train)
        pred_C = model_C.predict(X_test_C)

        mae_C = mean_absolute_error(y_test, pred_C)
        rmse_C = root_mean_squared_error(y_test, pred_C)
        smape_C = _calculate_smape(y_test, pred_C)

        results["model_C_weather_and_rain_prob"] = {
            "description": "Baseline + Weather features + Stage 4 Rain Prediction Probability",
            "features": features_C,
            "mae_mw": round(float(mae_C), 2),
            "rmse_mw": round(float(rmse_C), 2),
            "smape_pct": round(float(smape_C), 2),
        }

        # Include Rain Prob feature importance
        for feat, imp in zip(features_C, model_C.feature_importances_):
            if feat in rain_prob_features:
                weather_feature_importances[feat] = round(float(imp), 4)

    # Calculate Value & Improvement %
    mae_improvement_mw = mae_A - mae_B
    mae_improvement_pct = (mae_improvement_mw / mae_A * 100.0) if mae_A > 0 else 0.0

    rmse_improvement_mw = rmse_A - rmse_B
    rmse_improvement_pct = (rmse_improvement_mw / rmse_A * 100.0) if rmse_A > 0 else 0.0

    # Sort weather feature importances descending
    sorted_importances = dict(sorted(weather_feature_importances.items(), key=lambda x: x[1], reverse=True))

    return {
        "models": results,
        "mae_improvement_mw": round(float(mae_improvement_mw), 2),
        "mae_improvement_pct": round(float(mae_improvement_pct), 2),
        "rmse_improvement_mw": round(float(rmse_improvement_mw), 2),
        "rmse_improvement_pct": round(float(rmse_improvement_pct), 2),
        "top_weather_features": sorted_importances,
        "train_sample_count": len(train_df),
        "test_sample_count": len(test_df),
        "sufficient_data": True,
        "conclusion": (
            f"Adding weather features reduced forecasting MAE by {round(mae_improvement_pct, 1)}% "
            f"({round(mae_A, 2)} MW -> {round(mae_B, 2)} MW). "
            if mae_improvement_pct > 0
            else "Weather features yielded neutral/marginal MAE changes under current sample conditions."
        ),
    }
