"""Reusable Matplotlib visualization utilities for weather impact analytics."""

from typing import Dict, Any, List
import matplotlib
matplotlib.use("Agg")  # Non-interactive background renderer
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Modern theme styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
PRIMARY_COLOR = "#1f77b4"
SECONDARY_COLOR = "#ff7f0e"
ACCENT_COLOR = "#2ca02c"
DARK_TEXT = "#222222"


def plot_temperature_vs_demand(df: pd.DataFrame) -> plt.Figure:
    """1. Temperature vs Energy Demand Scatter & Trend curve."""
    fig, ax = plt.subplots(figsize=(8, 5))
    if df.empty or "temperature_c" not in df.columns or "demand_mw" not in df.columns:
        ax.text(0.5, 0.5, "Insufficient Data for Temperature vs Demand", ha="center", va="center")
        return fig

    clean_df = df.dropna(subset=["temperature_c", "demand_mw"])
    ax.scatter(clean_df["temperature_c"], clean_df["demand_mw"], alpha=0.5, color=PRIMARY_COLOR, edgecolors="none", label="Observations")

    # Quadratic polynomial trendline
    if len(clean_df) >= 10:
        x_vals = np.linspace(clean_df["temperature_c"].min(), clean_df["temperature_c"].max(), 100)
        p = np.polyfit(clean_df["temperature_c"], clean_df["demand_mw"], 2)
        y_vals = np.polyval(p, x_vals)
        ax.plot(x_vals, y_vals, color="red", linewidth=2, label="Polynomial Trend")

    ax.set_title("Temperature vs Energy Demand", fontsize=12, fontweight="bold")
    ax.set_xlabel("Temperature (deg C)", fontsize=10)
    ax.set_ylabel("Energy Demand (MW)", fontsize=10)
    ax.legend(loc="upper left")
    plt.tight_layout()
    return fig


def plot_temperature_bins(temp_bins_dict: Dict[str, Any]) -> plt.Figure:
    """2. Temperature Bins vs Average Demand bar chart."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = temp_bins_dict.get("temperature_bins", {})
    if not bins:
        ax.text(0.5, 0.5, "No Temperature Bins Available", ha="center", va="center")
        return fig

    labels = list(bins.keys())
    means = [bins[k]["mean_demand_mw"] for k in labels]
    counts = [bins[k]["observation_count"] for k in labels]

    bars = ax.bar(labels, means, color="#3498db", edgecolor="black", alpha=0.85)

    for bar, count in zip(bars, counts):
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.01), f"{yval:.1f}\n(n={count})", ha="center", va="bottom", fontsize=8)

    ax.set_title("Average Energy Demand by Temperature Bin", fontsize=12, fontweight="bold")
    ax.set_xlabel("Temperature Bin", fontsize=10)
    ax.set_ylabel("Mean Demand (MW)", fontsize=10)
    plt.tight_layout()
    return fig


def plot_weather_condition_demand(cond_dict: Dict[str, Any]) -> plt.Figure:
    """3. Weather Condition vs Energy Demand comparison chart."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    conditions = cond_dict.get("conditions", {})
    if not conditions:
        ax.text(0.5, 0.5, "No Weather Condition Data Available", ha="center", va="center")
        return fig

    names = list(conditions.keys())
    means = [conditions[k]["mean_demand_mw"] for k in names]

    bars = ax.bar(names, means, color="#9b59b6", edgecolor="black", alpha=0.85)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.01), f"{yval:.1f} MW", ha="center", va="bottom", fontsize=8)

    ax.set_title("Mean Energy Demand across Weather Conditions", fontsize=12, fontweight="bold")
    ax.set_xlabel("Weather Condition", fontsize=10)
    ax.set_ylabel("Mean Demand (MW)", fontsize=10)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    return fig


def plot_rain_vs_no_rain(rain_dict: Dict[str, Any]) -> plt.Figure:
    """4. Rain vs No-Rain Demand Comparison bar chart."""
    fig, ax = plt.subplots(figsize=(6, 4))
    rain_p = rain_dict.get("rain_periods", {})
    no_rain_p = rain_dict.get("no_rain_periods", {})

    labels = ["No Rain", "Rain"]
    means = [no_rain_p.get("mean_demand_mw", 0.0), rain_p.get("mean_demand_mw", 0.0)]
    counts = [no_rain_p.get("observation_count", 0), rain_p.get("observation_count", 0)]

    colors = ["#2ecc71", "#34495e"]
    bars = ax.bar(labels, means, color=colors, edgecolor="black", width=0.5, alpha=0.85)

    for bar, count in zip(bars, counts):
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 5, f"{yval:.1f} MW\n(n={count})", ha="center", va="bottom", fontsize=9)

    ax.set_title("Energy Demand: Rain vs. No Rain", fontsize=12, fontweight="bold")
    ax.set_ylabel("Mean Demand (MW)", fontsize=10)
    plt.tight_layout()
    return fig


def plot_humidity_vs_demand(df: pd.DataFrame) -> plt.Figure:
    """5. Humidity vs Energy Demand Scatter plot."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if df.empty or "humidity_pct" not in df.columns or "demand_mw" not in df.columns:
        ax.text(0.5, 0.5, "Insufficient Data for Humidity vs Demand", ha="center", va="center")
        return fig

    clean_df = df.dropna(subset=["humidity_pct", "demand_mw"])
    ax.scatter(clean_df["humidity_pct"], clean_df["demand_mw"], alpha=0.5, color="#e67e22", edgecolors="none")

    # Linear trendline
    if len(clean_df) >= 5:
        p = np.polyfit(clean_df["humidity_pct"], clean_df["demand_mw"], 1)
        x_vals = np.linspace(clean_df["humidity_pct"].min(), clean_df["humidity_pct"].max(), 50)
        ax.plot(x_vals, np.polyval(p, x_vals), color="black", linestyle="--", label="Linear Fit")

    ax.set_title("Humidity (%) vs Energy Demand (MW)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Relative Humidity (%)", fontsize=10)
    ax.set_ylabel("Energy Demand (MW)", fontsize=10)
    ax.legend()
    plt.tight_layout()
    return fig


def plot_weather_correlation_matrix(corr_dict: Dict[str, Any]) -> plt.Figure:
    """6. Weather Correlation Matrix Heatmap."""
    fig, ax = plt.subplots(figsize=(7, 6))
    matrix_dict = corr_dict.get("matrix_pearson", {})
    if not matrix_dict:
        ax.text(0.5, 0.5, "No Correlation Matrix Available", ha="center", va="center")
        return fig

    matrix_df = pd.DataFrame(matrix_dict)
    cax = ax.matshow(matrix_df, cmap="coolwarm", vmin=-1, vmax=1)
    fig.colorbar(cax)

    ticks = np.arange(len(matrix_df.columns))
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels(matrix_df.columns, rotation=45, ha="left", fontsize=9)
    ax.set_yticklabels(matrix_df.columns, fontsize=9)

    for i in range(len(matrix_df.columns)):
        for j in range(len(matrix_df.columns)):
            val = matrix_df.iloc[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="black" if abs(val) < 0.7 else "white", fontsize=8)

    ax.set_title("Weather & Demand Pearson Correlation Matrix", fontsize=12, fontweight="bold", pad=20)
    plt.tight_layout()
    return fig


def plot_weather_feature_importance(importance_dict: Dict[str, float]) -> plt.Figure:
    """7. Weather Feature Importance Horizontal Bar Chart."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if not importance_dict:
        ax.text(0.5, 0.5, "No Weather Feature Importance Data", ha="center", va="center")
        return fig

    features = list(importance_dict.keys())
    scores = [importance_dict[f] for f in features]

    y_pos = np.arange(len(features))
    ax.barh(y_pos, scores, color="#16a085", edgecolor="black", alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(features, fontsize=9)
    ax.invert_yaxis()  # top feature on top

    for i, v in enumerate(scores):
        ax.text(v + 0.002, i, f"{v:.4f}", va="center", fontsize=8)

    ax.set_title("Predictive Importance of Weather Features", fontsize=12, fontweight="bold")
    ax.set_xlabel("Relative Feature Importance Score", fontsize=10)
    plt.tight_layout()
    return fig


def plot_peak_demand_weather_context(peak_context: Dict[str, Any]) -> plt.Figure:
    """8. Peak Demand Weather Context comparison bar chart."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    peak_means = peak_context.get("peak_weather_averages", {})
    non_peak_means = peak_context.get("non_peak_weather_averages", {})

    common_vars = [v for v in peak_means if v in non_peak_means and v in ["temperature_c", "humidity_pct", "wind_speed_ms"]]
    if not common_vars:
        ax.text(0.5, 0.5, "No Peak Weather Averages Available", ha="center", va="center")
        return fig

    x = np.arange(len(common_vars))
    width = 0.35

    peak_vals = [peak_means[v] for v in common_vars]
    non_peak_vals = [non_peak_means[v] for v in common_vars]

    ax.bar(x - width/2, peak_vals, width, label="Peak Periods (>90th %)", color="#e74c3c", edgecolor="black")
    ax.bar(x + width/2, non_peak_vals, width, label="Non-Peak Periods", color="#95a5a6", edgecolor="black")

    ax.set_title("Weather Context: Peak Demand vs. Non-Peak", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(common_vars, fontsize=9)
    ax.legend()
    plt.tight_layout()
    return fig


def plot_forecasting_comparison(forecast_eval: Dict[str, Any]) -> plt.Figure:
    """9. Weather-Enabled vs Non-Weather Forecasting Comparison bar chart."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    models = forecast_eval.get("models", {})
    if not models:
        ax.text(0.5, 0.5, "No Forecasting Comparison Data", ha="center", va="center")
        return fig

    labels = ["Model A\n(Baseline)", "Model B\n(+Weather)"]
    maes = [models.get("model_A_baseline", {}).get("mae_mw", 0.0), models.get("model_B_weather_enhanced", {}).get("mae_mw", 0.0)]
    rmses = [models.get("model_A_baseline", {}).get("rmse_mw", 0.0), models.get("model_B_weather_enhanced", {}).get("rmse_mw", 0.0)]

    if "model_C_weather_and_rain_prob" in models:
        labels.append("Model C\n(+Weather+RainProb)")
        maes.append(models["model_C_weather_and_rain_prob"].get("mae_mw", 0.0))
        rmses.append(models["model_C_weather_and_rain_prob"].get("rmse_mw", 0.0))

    x = np.arange(len(labels))
    width = 0.35

    ax.bar(x - width/2, maes, width, label="MAE (MW)", color="#f39c12", edgecolor="black")
    ax.bar(x + width/2, rmses, width, label="RMSE (MW)", color="#c0392b", edgecolor="black")

    for i in range(len(labels)):
        ax.text(x[i] - width/2, maes[i] + 0.2, f"{maes[i]:.1f}", ha="center", va="bottom", fontsize=8)
        ax.text(x[i] + width/2, rmses[i] + 0.2, f"{rmses[i]:.1f}", ha="center", va="bottom", fontsize=8)

    ax.set_title("Forecasting Error: Baseline vs. Weather-Enhanced Models", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Error (MW)", fontsize=10)
    ax.legend()
    plt.tight_layout()
    return fig
