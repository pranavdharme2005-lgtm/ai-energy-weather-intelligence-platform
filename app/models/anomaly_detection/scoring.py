"""Standardized Anomaly Scoring & Severity Mapping Engine."""

from typing import Optional
import numpy as np


def calculate_anomaly_score(z_score: float, max_z: float = 5.0) -> float:
    """Normalizes absolute statistical z-score or deviation into [0.0, 1.0] anomaly score.
    
    Formula: score = clip( abs(z_score) / max_z, 0.0, 1.0 )
    """
    if np.isnan(z_score) or np.isinf(z_score):
        return 0.0
    return round(float(np.clip(abs(z_score) / max_z, 0.0, 1.0)), 2)


def classify_severity(score: float, z_score: Optional[float] = None) -> str:
    """Classifies anomaly severity level into NORMAL, LOW, MEDIUM, HIGH, or CRITICAL.
    
    Args:
        score: Normalized anomaly score in [0.0, 1.0].
        z_score: Absolute z-score (optional).
        
    Returns:
        str: Severity classification.
    """
    eff_score = score
    if z_score is not None:
        eff_score = max(score, calculate_anomaly_score(z_score))

    if eff_score >= 0.88:
        return "CRITICAL"
    elif eff_score >= 0.70:
        return "HIGH"
    elif eff_score >= 0.50:
        return "MEDIUM"
    elif eff_score >= 0.30:
        return "LOW"
    else:
        return "NORMAL"
