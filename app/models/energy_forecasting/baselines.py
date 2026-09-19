"""Baseline Forecasters for Benchmark Comparison.

Implements non-ML time-series baselines:
1. Naive Forecaster: Predicts last observed demand value.
2. Seasonal Naive Forecaster: Predicts demand from equivalent previous seasonal period (24 hours or 168 hours ago).
"""

import numpy as np
import pandas as pd
from typing import Optional


class NaiveForecaster:
    """Predicts demand as equal to the most recently observed historical value."""

    def __init__(self):
        self.last_value = 2800.0

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "NaiveForecaster":
        if "demand_mw_lag_1h" in X.columns:
            self.last_value = float(X["demand_mw_lag_1h"].iloc[-1])
        elif "demand_mw" in X.columns:
            self.last_value = float(X["demand_mw"].iloc[-1])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "demand_mw_lag_1h" in X.columns:
            return X["demand_mw_lag_1h"].values
        elif "demand_mw" in X.columns:
            return X["demand_mw"].values
        return np.full(len(X), self.last_value)


class SeasonalNaiveForecaster:
    """Predicts demand as equal to the demand from the same seasonal period (24 hours ago)."""

    def __init__(self, season_lag: int = 24):
        self.season_lag = season_lag
        self.default_value = 2800.0

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "SeasonalNaiveForecaster":
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        lag_col = f"demand_mw_lag_{self.season_lag}h"
        if lag_col in X.columns:
            return X[lag_col].values
        elif "demand_mw_lag_24h" in X.columns:
            return X["demand_mw_lag_24h"].values
        elif "demand_mw_lag_1h" in X.columns:
            return X["demand_mw_lag_1h"].values
        return np.full(len(X), self.default_value)
