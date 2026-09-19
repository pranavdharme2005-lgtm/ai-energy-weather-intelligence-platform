"""Rain Prediction Model Interface and Inference Service."""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib

from app.models.base import BaseMLModel, RainPredictionResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

SAVED_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "saved_models"
MODEL_FILE = SAVED_MODELS_DIR / "rain_predictor_v1.joblib"
META_FILE = SAVED_MODELS_DIR / "rain_predictor_v1_meta.json"


class RainPredictor(BaseMLModel):
    """Production classification model and inference service for rain prediction."""

    def __init__(self, model_version: str = "v1.0.0"):
        super().__init__(model_version=model_version)
        self.model = None
        self.feature_names = None
        self.threshold = 0.50
        self.metadata = {}
        self.load_model()

    def load_model(self, file_path: str = None) -> None:
        """Loads serialized model artifact and metadata if available."""
        target_file = Path(file_path) if file_path else MODEL_FILE

        if target_file.exists():
            try:
                artifact = joblib.load(target_file)
                self.model = artifact.get("model")
                self.feature_names = artifact.get("feature_names")
                self.threshold = artifact.get("threshold", 0.50)
                self.model_version = artifact.get("model_version", "v1.0.0")
                self.is_trained = True

                if META_FILE.exists():
                    with open(META_FILE, "r") as f:
                        self.metadata = json.load(f)

                logger.info(f"Successfully loaded RainPredictor model from {target_file} (Threshold: {self.threshold}).")
            except Exception as e:
                logger.warning(f"Could not load RainPredictor artifact from {target_file}: {e}. Operating in fallback baseline mode.")
                self.is_trained = False
        else:
            logger.info(f"RainPredictor model artifact not found at {target_file}. Operating in fallback baseline mode.")
            self.is_trained = False

    def save_model(self, file_path: str) -> None:
        """Serializes current model state."""
        if self.model:
            joblib.dump({
                "model": self.model,
                "feature_names": self.feature_names,
                "threshold": self.threshold,
                "model_version": self.model_version
            }, file_path)
            logger.info(f"Saved RainPredictor artifact to {file_path}")

    def fit(self, X: pd.DataFrame, y: pd.Series = None) -> "RainPredictor":
        """Fits model via rain pipeline orchestrator."""
        from app.models.rain_pipeline import RainModelTrainer
        self.model, self.metadata = RainModelTrainer.train_and_evaluate(X)
        self.is_trained = True
        return self

    def predict(self, X: pd.DataFrame) -> RainPredictionResult:
        """Runs single-step prediction inference for rain probability."""
        results = self.predict_batch(X)
        if results:
            return results[-1]

        now = datetime.now(timezone.utc)
        return RainPredictionResult(
            timestamp=now,
            prediction_target_time=now + timedelta(hours=3),
            rain_predicted=False,
            probability=0.10,
            model_version=f"{self.model_version}-fallback"
        )

    def predict_batch(self, X: pd.DataFrame) -> List[RainPredictionResult]:
        """Runs batch prediction inference returning list of RainPredictionResult."""
        if X.empty:
            return []

        now = datetime.now(timezone.utc)
        results = []

        # If trained ML model is loaded, use feature matrix and predict_proba
        if self.is_trained and self.model is not None and self.feature_names is not None:
            from app.models.rain_pipeline import extract_rain_features
            feat_X, _ = extract_rain_features(X)

            # Re-align features
            for col in self.feature_names:
                if col not in feat_X.columns:
                    feat_X[col] = 0.0
            feat_X = feat_X[self.feature_names]

            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(feat_X)[:, 1]
            else:
                probs = self.model.predict(feat_X)

            for i, row in X.iterrows():
                ts = row["timestamp"] if "timestamp" in row and isinstance(row["timestamp"], datetime) else now
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                prob = float(probs[i]) if i < len(probs) else 0.10
                rain_flag = bool(prob >= self.threshold)

                results.append(RainPredictionResult(
                    timestamp=ts,
                    prediction_target_time=ts + timedelta(hours=3),
                    rain_predicted=rain_flag,
                    probability=round(float(prob), 4),
                    model_version=self.model_version
                ))
            return results

        # Fallback baseline heuristic calculation if no trained model exists yet
        for i, row in X.iterrows():
            ts = row["timestamp"] if "timestamp" in row and isinstance(row["timestamp"], datetime) else now
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            humidity = float(row.get("humidity_pct", 50.0))
            cloud_cover = float(row.get("cloud_cover_pct", 20.0))
            prob = min(max(((humidity - 40.0) / 60.0 + (cloud_cover / 200.0)) / 1.5, 0.05), 0.95)
            rain_flag = prob >= self.threshold

            results.append(RainPredictionResult(
                timestamp=ts,
                prediction_target_time=ts + timedelta(hours=3),
                rain_predicted=rain_flag,
                probability=round(float(prob), 4),
                model_version=f"{self.model_version}-fallback"
            ))

        return results
