"""Multivariate Anomaly Detection using Unsupervised Isolation Forest."""

from typing import List, Dict, Any
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

from app.models.base import AnomalyResult
from app.models.anomaly_detection.scoring import calculate_anomaly_score, classify_severity
from app.utils.logger import get_logger

logger = get_logger(__name__)

MULTIVARIATE_FEATURES = [
    "demand_mw", "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms", "precipitation_mm"
]


def detect_multivariate_anomalies(
    df: pd.DataFrame, region: str = "Grid_Alpha", contamination: float = 0.05
) -> List[AnomalyResult]:
    """Detects unusual joint feature combinations using Isolation Forest.
    
    Args:
        df: Combined weather and energy load dataframe.
        region: Regional grid identifier.
        contamination: Proportion of expected outliers.
        
    Returns:
        List[AnomalyResult]: Multivariate anomaly results.
    """
    anomalies = []
    if df.empty or len(df) < 20:
        return anomalies

    # Select available multivariate features
    avail_cols = [c for c in MULTIVARIATE_FEATURES if c in df.columns]
    if len(avail_cols) < 2 or "demand_mw" not in avail_cols:
        return anomalies

    res_df = df.copy()
    X = res_df[avail_cols].fillna(res_df[avail_cols].median()).fillna(0.0)

    # Fit Isolation Forest
    iso_model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    preds = iso_model.fit_predict(X)
    scores_raw = iso_model.score_samples(X)  # Negative values; lower = more anomalous

    # Normalize raw decision scores to [0.0, 1.0]
    # score_samples ranges from ~ -0.8 (most anomalous) to ~ -0.3 (normal)
    min_s, max_s = scores_raw.min(), scores_raw.max()
    score_span = (max_s - min_s) if (max_s - min_s) > 1e-6 else 1.0
    norm_scores = (max_s - scores_raw) / score_span

    for idx, (p, norm_s) in enumerate(zip(preds, norm_scores)):
        if p == -1 and norm_s > 0.55:  # Anomaly flag by Isolation Forest
            severity = classify_severity(float(norm_s))
            if severity == "NORMAL":
                continue

            row = res_df.iloc[idx]
            ts = row["timestamp"] if "timestamp" in row else datetime.now(timezone.utc)
            if not isinstance(ts, datetime):
                ts = pd.to_datetime(ts).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            actual_demand = float(row.get("demand_mw", 0.0))
            expected_demand = float(res_df["demand_mw"].median())
            dev = float(actual_demand - expected_demand)

            reason = (
                f"Multivariate Isolation Forest identified an anomalous joint feature pattern "
                f"across energy load ({round(actual_demand, 1)} MW) and meteorological state (score: {round(norm_s, 2)})."
            )

            anomalies.append(
                AnomalyResult(
                    timestamp=ts,
                    region=region,
                    metric_name="multivariate_grid_state",
                    variable="demand_mw",
                    actual_value=round(actual_demand, 2),
                    expected_value=round(expected_demand, 2),
                    deviation=round(dev, 2),
                    anomaly_score=round(float(norm_s), 2),
                    severity=severity,
                    anomaly_type="multivariate_isolation",
                    description=reason,
                    detection_method="isolation_forest",
                    model_version="v1.0.0"
                )
            )

    logger.info(f"Multivariate Isolation Forest found {len(anomalies)} multivariate anomalies.")
    return anomalies
