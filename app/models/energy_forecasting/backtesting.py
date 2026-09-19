"""Time-Series Expanding Window Cross-Validation & Backtesting Engine.

Evaluates forecasting performance over rolling historical time origins without look-ahead shuffle.
"""

from typing import Dict, Any, List, Tuple, Type
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from app.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Symmetric Mean Absolute Percentage Error (sMAPE).
    
    sMAPE = (100% / n) * sum( 2 * |y_pred - y_true| / (|y_true| + |y_pred| + eps) )
    """
    denominator = np.abs(y_true) + np.abs(y_pred) + 1e-8
    numerator = 2.0 * np.abs(y_pred - y_true)
    smape = np.mean(numerator / denominator) * 100.0
    return round(float(smape), 2)


class ExpandingWindowCV:
    """Expanding-window cross-validation for time-series regression forecasters."""

    def __init__(self, initial_train_ratio: float = 0.50, n_splits: int = 4, horizon_hours: int = 24):
        self.initial_train_ratio = initial_train_ratio
        self.n_splits = n_splits
        self.horizon_hours = horizon_hours

    def evaluate(self, model_factory, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Runs expanding window backtest over X and y.
        
        Args:
            model_factory: Instantiator or template model with fit() and predict() methods.
            X: Feature matrix.
            y: Target demand series.
            
        Returns:
            Dict[str, Any]: Aggregated backtest metrics (MAE, RMSE, sMAPE).
        """
        n = len(X)
        if n < 50:
            logger.warning("Dataset too small for multi-fold backtesting.")
            return {"mae": 0.0, "rmse": 0.0, "smape": 0.0, "folds": 0}

        min_train_end = int(n * self.initial_train_ratio)
        remaining = n - min_train_end
        step_size = max(1, remaining // self.n_splits)

        maes, rmses, smapes = [], [], []

        for fold in range(self.n_splits):
            train_end = min_train_end + fold * step_size
            val_end = min(train_end + self.horizon_hours, n)

            if train_end >= n or val_end <= train_end:
                break

            X_tr, y_tr = X.iloc[:train_end], y.iloc[:train_end]
            X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]

            # Clone or instantiate model
            m = model_factory()
            m.fit(X_tr, y_tr)
            preds = m.predict(X_val)

            mae = float(mean_absolute_error(y_val, preds))
            rmse = float(root_mean_squared_error(y_val, preds))
            smape = calculate_smape(y_val.values, preds)

            maes.append(mae)
            rmses.append(rmse)
            smapes.append(smape)

        return {
            "mae": round(float(np.mean(maes)), 2) if maes else 0.0,
            "rmse": round(float(np.mean(rmses)), 2) if rmses else 0.0,
            "smape": round(float(np.mean(smapes)), 2) if smapes else 0.0,
            "folds": len(maes)
        }
