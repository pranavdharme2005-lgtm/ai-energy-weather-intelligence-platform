"""Reusable Anomaly Visualization Generators for UI & Analytics."""

from typing import List, Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.models.base import AnomalyResult, EnergyForecastResult

SEVERITY_COLORS = {
    "NORMAL": "#2ca02c",
    "LOW": "#1f77b4",
    "MEDIUM": "#ff7f0e",
    "HIGH": "#d62728",
    "CRITICAL": "#9467bd"
}


def plot_demand_anomalies(df: pd.DataFrame, anomalies: List[AnomalyResult], save_path: Optional[str] = None) -> plt.Figure:
    """Generates time-series line plot of demand with overlaid detected anomaly points."""
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=100)

    if not df.empty and "timestamp" in df.columns and "demand_mw" in df.columns:
        ax.plot(df["timestamp"], df["demand_mw"], label="Observed Load (MW)", color="#1f77b4", alpha=0.75, linewidth=1.5)

    if anomalies:
        anom_dfs = []
        for a in anomalies:
            if a.variable == "demand_mw":
                anom_dfs.append({
                    "timestamp": a.timestamp,
                    "demand_mw": a.actual_value,
                    "severity": a.severity
                })

        if anom_dfs:
            a_df = pd.DataFrame(anom_dfs)
            for sev, color in SEVERITY_COLORS.items():
                sub = a_df[a_df["severity"] == sev]
                if not sub.empty:
                    ax.scatter(sub["timestamp"], sub["demand_mw"], label=f"Anomaly: {sev}", color=color, s=50, zorder=5)

    ax.set_title("Grid Load Demand with Detected Anomalies Overlaid", fontsize=12, fontweight="bold")
    ax.set_xlabel("Timestamp (UTC)")
    ax.set_ylabel("Demand (MW)")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig


def plot_forecast_breaches(
    actual_df: pd.DataFrame, forecast_results: List[EnergyForecastResult], anomalies: List[AnomalyResult], save_path: Optional[str] = None
) -> plt.Figure:
    """Generates Forecast vs Actual plot highlighting prediction interval breach anomalies."""
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=100)

    if forecast_results:
        f_df = pd.DataFrame([f.model_dump() for f in forecast_results])
        ax.plot(f_df["forecast_target_time"], f_df["forecasted_demand_mw"], label="Forecasted Load (MW)", color="#ff7f0e", linestyle="--", linewidth=2.0)

        if "confidence_lower_mw" in f_df.columns and "confidence_upper_mw" in f_df.columns:
            ax.fill_between(f_df["forecast_target_time"], f_df["confidence_lower_mw"], f_df["confidence_upper_mw"], color="#ff7f0e", alpha=0.18, label="95% Forecast Bounds")

    if not actual_df.empty:
        ax.plot(actual_df["timestamp"], actual_df["demand_mw"], label="Actual Demand (MW)", color="#1f77b4", linewidth=1.5)

    # Highlight forecast breach anomalies
    breaches = [a for a in anomalies if a.anomaly_type == "forecast_deviation"]
    if breaches:
        b_df = pd.DataFrame([b.model_dump() for b in breaches])
        ax.scatter(b_df["timestamp"], b_df["actual_value"], color="#d62728", s=65, label="Forecast Breach", zorder=6, marker="X")

    ax.set_title("Forecast vs Actual Load: Interval Breach Detection", fontsize=12, fontweight="bold")
    ax.set_xlabel("Timestamp (UTC)")
    ax.set_ylabel("Demand (MW)")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig


def plot_severity_distribution(summary: Dict[str, Any], save_path: Optional[str] = None) -> plt.Figure:
    """Generates bar chart of detected anomaly counts by severity level."""
    fig, ax = plt.subplots(figsize=(7, 4), dpi=100)

    sev_counts = summary.get("severity_breakdown", {})
    categories = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    counts = [sev_counts.get(c, 0) for c in categories]
    colors = [SEVERITY_COLORS.get(c, "#333333") for c in categories]

    ax.bar(categories, counts, color=colors)
    ax.set_title("Detected Anomalies by Severity Level", fontsize=12, fontweight="bold")
    ax.set_xlabel("Severity Level")
    ax.set_ylabel("Count")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig
