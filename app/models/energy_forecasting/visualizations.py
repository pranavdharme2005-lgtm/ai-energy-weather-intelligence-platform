"""Reusable Forecasting Visualization Generators for UI & Analytics."""

from typing import Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_actual_vs_forecast(actual_df: pd.DataFrame, forecast_df: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
    """Generates time-series line comparison plot of actual vs predicted demand."""
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=100)

    if not actual_df.empty:
        ax.plot(actual_df["timestamp"], actual_df["demand_mw"], label="Actual Load (MW)", color="#1f77b4", linewidth=2.0)
    if not forecast_df.empty:
        ax.plot(forecast_df["forecast_target_time"], forecast_df["forecasted_demand_mw"], label="Forecasted Load (MW)", color="#ff7f0e", linestyle="--", linewidth=2.0)

    ax.set_title("Grid Energy Demand: Actual vs Forecast Horizon", fontsize=12, fontweight="bold")
    ax.set_xlabel("Timestamp (UTC)")
    ax.set_ylabel("Power Load (MW)")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig


def plot_forecast_horizon(forecast_df: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
    """Generates 24-hour forecast trajectory with 95% confidence interval shaded band."""
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=100)

    if not forecast_df.empty:
        timestamps = forecast_df["forecast_target_time"]
        preds = forecast_df["forecasted_demand_mw"]
        ax.plot(timestamps, preds, label="Predicted Demand (MW)", color="#0055ff", marker="o", linewidth=2.0)

        if "confidence_lower_mw" in forecast_df.columns and "confidence_upper_mw" in forecast_df.columns:
            lower = forecast_df["confidence_lower_mw"]
            upper = forecast_df["confidence_upper_mw"]
            ax.fill_between(timestamps, lower, upper, color="#0055ff", alpha=0.18, label="95% Prediction Interval")

    ax.set_title("24-Hour Grid Demand Forecast & Uncertainty Interval", fontsize=12, fontweight="bold")
    ax.set_xlabel("Target Forecast Time")
    ax.set_ylabel("Demand (MW)")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig


def plot_model_comparison(candidate_evals: Dict[str, Dict[str, float]], save_path: Optional[str] = None) -> plt.Figure:
    """Generates bar chart comparing MAE, RMSE, and sMAPE across candidate models."""
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=100)

    models = list(candidate_evals.keys())
    maes = [candidate_evals[m].get("mae", 0.0) for m in models]
    rmses = [candidate_evals[m].get("rmse", 0.0) for m in models]

    x = np.arange(len(models))
    width = 0.35

    ax.bar(x - width / 2, maes, width, label="MAE (MW)", color="#2ca02c")
    ax.bar(x + width / 2, rmses, width, label="RMSE (MW)", color="#d62728")

    ax.set_title("Energy Forecaster Candidate Model Benchmark Comparison", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace("_", " ").title() for m in models], rotation=15)
    ax.set_ylabel("Error (MW)")
    ax.legend()
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig


def plot_feature_importance(importance_dict: Dict[str, float], top_n: int = 10, save_path: Optional[str] = None) -> plt.Figure:
    """Generates horizontal bar chart of top predictor feature importances."""
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)

    sorted_feats = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
    features = [f[0] for f in reversed(sorted_feats)]
    scores = [f[1] for f in reversed(sorted_feats)]

    ax.barh(features, scores, color="#9467bd")
    ax.set_title(f"Top {top_n} Predictor Feature Importance Ranking", fontsize=12, fontweight="bold")
    ax.set_xlabel("Relative Importance Score")
    ax.grid(True, axis="x", linestyle=":", alpha=0.6)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path)
    return fig
