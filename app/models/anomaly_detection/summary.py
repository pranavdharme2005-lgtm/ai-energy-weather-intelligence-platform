"""Anomaly Summary & Statistics Generator."""

from typing import List, Dict, Any
from app.models.base import AnomalyResult


def calculate_anomaly_summary(anomalies: List[AnomalyResult]) -> Dict[str, Any]:
    """Computes summary statistics over a sequence of detected anomaly results.
    
    Args:
        anomalies: List of AnomalyResult objects.
        
    Returns:
        Dict[str, Any]: Comprehensive summary metrics.
    """
    if not anomalies:
        return {
            "total_anomalies": 0,
            "high_severity_count": 0,
            "critical_severity_count": 0,
            "severity_breakdown": {"NORMAL": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
            "type_breakdown": {},
            "variable_breakdown": {},
            "most_frequent_category": "None"
        }

    severities = {"NORMAL": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    types = {}
    variables = {}

    for a in anomalies:
        sev = a.severity
        severities[sev] = severities.get(sev, 0) + 1

        a_type = a.anomaly_type
        types[a_type] = types.get(a_type, 0) + 1

        var = a.variable
        variables[var] = variables.get(var, 0) + 1

    most_freq_cat = max(types.items(), key=lambda x: x[1])[0] if types else "None"

    return {
        "total_anomalies": len(anomalies),
        "high_severity_count": severities.get("HIGH", 0),
        "critical_severity_count": severities.get("CRITICAL", 0),
        "severity_breakdown": severities,
        "type_breakdown": types,
        "variable_breakdown": variables,
        "most_frequent_category": most_freq_cat
    }
