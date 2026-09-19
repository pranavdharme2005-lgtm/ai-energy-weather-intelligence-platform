"""Rain Prediction Machine Learning Pipeline & Training Engine."""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np
import joblib

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

from app.data.features import add_calendar_features
from app.utils.logger import get_logger

logger = get_logger(__name__)

SAVED_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


def create_rain_target(
    df: pd.DataFrame, horizon_hours: int = 3, threshold_mm: float = 0.1
) -> pd.DataFrame:
    """Creates binary target indicating precipitation within the next horizon_hours window.
    
    Target = 1 if max(precipitation in [t+1, t+horizon]) >= threshold_mm else 0.
    Trailing horizon rows where look-ahead cannot be computed are dropped.
    """
    if df.empty or "precipitation_mm" not in df.columns:
        return df

    res_df = df.copy()
    precip = res_df["precipitation_mm"]

    # Rolling max looking forward (shift -1 leaves NaN at end)
    future_max_precip = precip.iloc[::-1].rolling(window=horizon_hours, min_periods=1).max().iloc[::-1].shift(-1)
    
    target_series = pd.Series(np.nan, index=res_df.index, dtype=float)
    valid_mask = ~future_max_precip.isna()
    target_series[valid_mask] = (future_max_precip[valid_mask] >= threshold_mm).astype(float)

    res_df["target_rain_next_3h"] = target_series

    # Drop trailing rows where future horizon target is unknown
    res_df = res_df.dropna(subset=["target_rain_next_3h"]).reset_index(drop=True)
    res_df["target_rain_next_3h"] = res_df["target_rain_next_3h"].astype(int)

    return res_df


def extract_rain_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Extracts leakage-free predictor feature matrix for rain classification."""
    feat_df = add_calendar_features(df)

    # Historical lag of precipitation (strictly backward looking)
    if "precipitation_mm" in feat_df.columns:
        feat_df["precipitation_mm_lag_1h"] = feat_df["precipitation_mm"].shift(1).fillna(0.0)

    feature_cols = [
        "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms",
        "cloud_cover_pct", "precipitation_mm_lag_1h", "hour_sin", "hour_cos",
        "month_sin", "month_cos", "season"
    ]

    # Ensure all feature columns exist with fallbacks
    for col in feature_cols:
        if col not in feat_df.columns:
            feat_df[col] = 0.0

    X = feat_df[feature_cols].copy()
    # Fill any remaining NaNs with column median
    X = X.fillna(X.median()).fillna(0.0)

    return X, feature_cols


def chronological_split(
    X: pd.DataFrame, y: pd.Series, train_ratio: float = 0.70, val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Splits data chronologically without random shuffling to prevent look-ahead bias."""
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
    X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
    X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

    return X_train, X_val, X_test, y_train, y_val, y_test


def find_optimal_threshold(y_true: pd.Series, y_probs: np.ndarray) -> Tuple[float, float]:
    """Finds decision threshold tau in [0.1, 0.9] maximizing F1 score."""
    best_tau = 0.5
    best_f1 = 0.0

    for tau in np.linspace(0.10, 0.90, 81):
        preds = (y_probs >= tau).astype(int)
        f1 = f1_score(y_true, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_tau = float(tau)

    return round(best_tau, 2), round(best_f1, 4)


def evaluate_classifier(model, X_test: pd.DataFrame, y_test: pd.Series, threshold: float = 0.5) -> Dict[str, Any]:
    """Evaluates classifier model returning accuracy, precision, recall, f1, roc_auc, and confusion matrix."""
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_test)[:, 1]
    else:
        probs = model.predict(X_test)

    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y_test, preds).tolist()

    try:
        roc_auc = float(roc_auc_score(y_test, probs))
    except Exception:
        roc_auc = 0.5

    return {
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "precision": round(float(precision_score(y_test, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, preds, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, preds, zero_division=0)), 4),
        "roc_auc": round(roc_auc, 4),
        "threshold": threshold,
        "confusion_matrix": cm
    }


class RainModelTrainer:
    """Orchestrates candidate model training, evaluation, threshold tuning, and artifact saving."""

    @classmethod
    def train_and_evaluate(cls, df: pd.DataFrame, model_type: str = "random_forest") -> Tuple[Any, Dict[str, Any]]:
        """Trains candidate rain models, selects best artifact, and saves to storage."""
        logger.info("Starting Rain Prediction Model training pipeline...")

        # 1. Target Creation
        df_target = create_rain_target(df, horizon_hours=3, threshold_mm=0.1)
        if df_target.empty or len(df_target) < 10:
            raise ValueError("Insufficient data records for model training.")

        y = df_target["target_rain_next_3h"]
        X, feature_names = extract_rain_features(df_target)

        # 2. Chronological Split
        X_train, X_val, X_test, y_train, y_val, y_test = chronological_split(X, y)
        logger.info(f"Chronological Split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

        # Combine train + val for final fit after model selection
        X_train_val = pd.concat([X_train, X_val])
        y_train_val = pd.concat([y_train, y_val])

        # 3. Model Candidates Setup
        models = {
            "majority_baseline": DummyClassifier(strategy="most_frequent"),
            "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=42),
            "hist_gradient_boosting": HistGradientBoostingClassifier(class_weight="balanced", random_state=42)
        }

        eval_results = {}
        trained_models = {}

        for name, m in models.items():
            m.fit(X_train, y_train)
            trained_models[name] = m

            # Get validation probabilities
            if hasattr(m, "predict_proba"):
                val_probs = m.predict_proba(X_val)[:, 1]
            else:
                val_probs = np.zeros(len(X_val))

            best_tau, val_f1 = find_optimal_threshold(y_val, val_probs)
            metrics = evaluate_classifier(m, X_test, y_test, threshold=best_tau)
            metrics["optimal_threshold"] = best_tau
            eval_results[name] = metrics
            logger.info(f"Model [{name}]: Accuracy={metrics['accuracy']}, F1={metrics['f1']}, ROC-AUC={metrics['roc_auc']}, Tau={best_tau}")

        # 4. Select Target Model
        selected_key = model_type if model_type in trained_models else "random_forest"
        selected_model = trained_models[selected_key]
        selected_metrics = eval_results[selected_key]
        opt_tau = selected_metrics["optimal_threshold"]

        # Final fit on train + val
        selected_model.fit(X_train_val, y_train_val)

        # 5. Extract Feature Importance
        feature_importance = {}
        if hasattr(selected_model, "feature_importances_"):
            importances = selected_model.feature_importances_
            feature_importance = {name: round(float(imp), 4) for name, imp in zip(feature_names, importances)}
            feature_importance = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))

        # 6. Model Artifact Serialization
        model_path = SAVED_MODELS_DIR / "rain_predictor_v1.joblib"
        meta_path = SAVED_MODELS_DIR / "rain_predictor_v1_meta.json"

        joblib.dump({
            "model": selected_model,
            "feature_names": feature_names,
            "threshold": opt_tau,
            "model_version": "v1.0.0"
        }, model_path)

        metadata = {
            "model_name": selected_key,
            "model_version": "v1.0.0",
            "training_date": datetime.now(timezone.utc).isoformat(),
            "train_records": len(X_train_val),
            "test_records": len(X_test),
            "features_used": feature_names,
            "optimal_threshold": opt_tau,
            "metrics": selected_metrics,
            "candidate_evaluations": eval_results,
            "feature_importance": feature_importance
        }

        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved Rain Predictor model artifact to {model_path}")

        return selected_model, metadata
