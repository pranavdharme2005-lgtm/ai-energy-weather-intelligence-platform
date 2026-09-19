"""Energy Demand Forecasting Candidate Training & Serialization Engine."""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np
import joblib

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from app.models.energy_forecasting.features import create_forecasting_target, extract_forecasting_features
from app.models.energy_forecasting.baselines import NaiveForecaster, SeasonalNaiveForecaster
from app.models.energy_forecasting.backtesting import ExpandingWindowCV, calculate_smape
from app.utils.logger import get_logger

logger = get_logger(__name__)

SAVED_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "saved_models"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


def evaluate_forecaster(model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
    """Evaluates forecaster returning MAE, RMSE, and sMAPE metrics."""
    preds = model.predict(X_test)
    y_true = y_test.values

    mae = float(mean_absolute_error(y_true, preds))
    rmse = float(root_mean_squared_error(y_true, preds))
    smape = calculate_smape(y_true, preds)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "smape": smape
    }


class EnergyModelTrainer:
    """Orchestrates model training, baseline comparisons, backtesting, and serialization."""

    @classmethod
    def train_and_evaluate(
        cls, df: pd.DataFrame, horizon_hours: int = 24, model_type: str = "random_forest"
    ) -> Tuple[Any, Dict[str, Any]]:
        """Trains candidate forecasters, selects best model, computes uncertainty bounds, and serializes artifact."""
        logger.info(f"Starting Energy Demand Forecaster training pipeline (horizon={horizon_hours}h)...")

        # 1. Target Creation
        df_target = create_forecasting_target(df, horizon_hours=horizon_hours)
        target_col = f"target_demand_next_{horizon_hours}h"

        if df_target.empty or len(df_target) < 30:
            raise ValueError("Insufficient data records for forecasting model training.")

        y = df_target[target_col]
        X, feature_names = extract_forecasting_features(df_target)

        # 2. Chronological Split (70% Train, 15% Val, 15% Test)
        n = len(X)
        train_end = int(n * 0.70)
        val_end = int(n * 0.85)

        X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
        X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
        X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

        X_train_val = pd.concat([X_train, X_val])
        y_train_val = pd.concat([y_train, y_val])

        # 3. Model Candidates Setup
        models = {
            "naive_baseline": NaiveForecaster(),
            "seasonal_naive": SeasonalNaiveForecaster(season_lag=24),
            "ridge_regression": Ridge(alpha=1.0),
            "random_forest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            "hist_gradient_boosting": HistGradientBoostingRegressor(random_state=42)
        }

        eval_results = {}
        trained_models = {}

        for name, m in models.items():
            m.fit(X_train, y_train)
            trained_models[name] = m

            # Evaluate on Validation & Test set
            val_metrics = evaluate_forecaster(m, X_val, y_val)
            test_metrics = evaluate_forecaster(m, X_test, y_test)

            eval_results[name] = {
                "val": val_metrics,
                "test": test_metrics
            }
            logger.info(f"Model [{name}]: Val MAE={val_metrics['mae']}, Val RMSE={val_metrics['rmse']}, Test MAE={test_metrics['mae']}")

        # 4. Target Model Selection
        selected_key = model_type if model_type in trained_models else "random_forest"
        selected_model = trained_models[selected_key]
        selected_eval = eval_results[selected_key]

        # Refit selected model on Train + Val
        selected_model.fit(X_train_val, y_train_val)

        # Calculate Residual Standard Error for 95% Confidence Interval
        val_preds = selected_model.predict(X_val)
        residuals = y_val.values - val_preds
        residual_std = float(np.std(residuals))
        margin_95 = round(1.96 * residual_std, 2)

        # 5. Expanding Window Cross-Validation Backtest
        cv_backtester = ExpandingWindowCV(initial_train_ratio=0.50, n_splits=3, horizon_hours=horizon_hours)
        backtest_res = cv_backtester.evaluate(
            lambda: RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42), X, y
        )

        # 6. Extract Feature Importance
        feature_importance = {}
        if hasattr(selected_model, "feature_importances_"):
            importances = selected_model.feature_importances_
            feature_importance = {name: round(float(imp), 4) for name, imp in zip(feature_names, importances)}
            feature_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))

        # 7. Serialize Model Artifacts
        model_path = SAVED_MODELS_DIR / "energy_forecaster_v1.joblib"
        meta_path = SAVED_MODELS_DIR / "energy_forecaster_v1_meta.json"

        joblib.dump({
            "model": selected_model,
            "feature_names": feature_names,
            "horizon_hours": horizon_hours,
            "margin_95": margin_95,
            "model_version": "v1.0.0"
        }, model_path)

        metadata = {
            "model_name": selected_key,
            "model_version": "v1.0.0",
            "training_date": datetime.now(timezone.utc).isoformat(),
            "data_frequency": "hourly (1h)",
            "forecast_horizon": f"{horizon_hours}h",
            "train_records": len(X_train_val),
            "test_records": len(X_test),
            "features_used": feature_names,
            "margin_95": margin_95,
            "selected_eval": selected_eval,
            "candidate_evaluations": eval_results,
            "backtest_results": backtest_res,
            "feature_importance": feature_importance
        }

        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved Energy Forecaster model artifact to {model_path}")
        return selected_model, metadata
