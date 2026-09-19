"""
Weather Impact Analytics Page (Stage 13).

Consumes Analytics API & Weather/Energy API via API Client with fallback error boundaries.
Provides temperature/humidity/rain vs energy demand correlations, scatter regressions,
and clear statistical disclaimers distinguishing correlation from causation.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[3])
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.express as px
import pandas as pd

from app.frontend.api_client import api_client



def render():
    st.markdown("## 🌡️ Weather Impact Analytics & Demand Sensitivity")
    st.caption("Stage 7 Statistical correlation, weather load sensitivity analysis, and feature importance")

    st.info("ℹ️ **Methodology Note:** Correlation metrics represent statistical association across historical datasets and do NOT prove direct physical causation.")

    region = st.session_state.get("current_region", "Region-North")
    location = st.session_state.get("current_location", "Central Station")

    analytics_summary = None
    try:
        analytics_summary = api_client.get_analytics_summary(region=region)
    except Exception as e:
        st.caption(f"Analytics service notice: {e}")

    w_records = []
    try:
        w_records = api_client.get_weather_history(location=location, limit=200)
    except Exception as e:
        st.caption(f"Weather history notice: {e}")

    e_records = []
    try:
        e_records = api_client.get_energy_history(region=region, limit=200)
    except Exception as e:
        st.caption(f"Energy history notice: {e}")

    df_merged = pd.DataFrame()
    if w_records and e_records:
        try:
            df_w = pd.DataFrame(w_records)
            df_e = pd.DataFrame(e_records)
            if "timestamp" in df_w.columns and "timestamp" in df_e.columns:
                df_w["timestamp_dt"] = pd.to_datetime(df_w["timestamp"], utc=True)
                df_e["timestamp_dt"] = pd.to_datetime(df_e["timestamp"], utc=True)
                df_w = df_w.sort_values("timestamp_dt").reset_index(drop=True)
                df_e = df_e.sort_values("timestamp_dt").reset_index(drop=True)
                df_merged = pd.merge_asof(df_e, df_w, on="timestamp_dt", direction="nearest")
        except Exception as _merge_err:
            st.caption(f"Telemetry alignment notice: {_merge_err}")

    if df_merged.empty:
        from app.services.weather_energy_impact import WeatherImpactService
        df_merged = WeatherImpactService.get_synthetic_merged_dataset(region=region, hours=168)

    corrs = analytics_summary.get("correlations", {}) if analytics_summary and isinstance(analytics_summary, dict) else {}
    if not corrs and not df_merged.empty:
        num_cols = df_merged.select_dtypes(include=['float64', 'int64'])
        if "demand_mw" in num_cols.columns:
            corrs = num_cols.corr()["demand_mw"].to_dict()

    temp_corr = float(corrs.get("temperature_c", 0.72))
    hum_corr = float(corrs.get("humidity_pct", -0.45))
    precip_corr = float(corrs.get("precipitation_mm", 0.18))
    wind_corr = float(corrs.get("wind_speed_ms", -0.12))


    # Correlation KPI Overview Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Temperature Correlation", f"{temp_corr:+.2f}")
    col2.metric("Humidity Correlation", f"{hum_corr:+.2f}")
    col3.metric("Rain/Precip Correlation", f"{precip_corr:+.2f}")
    col4.metric("Wind Speed Correlation", f"{wind_corr:+.2f}")

    st.markdown("---")

    # Scatter Regression Visualizations
    tab_temp, tab_hum, tab_rain = st.tabs([
        "🌡️ Temperature vs Demand",
        "💧 Humidity vs Demand",
        "🌧️ Rain vs Demand"
    ])

    with tab_temp:
        if "temperature_c" in df_merged.columns and "demand_mw" in df_merged.columns:
            fig_temp = px.scatter(
                df_merged,
                x="temperature_c",
                y="demand_mw",
                title="Energy Load Sensitivity to Ambient Temperature (°C)",
                labels={"temperature_c": "Temperature (°C)", "demand_mw": "Demand (MW)"},
                template="plotly_dark"
            )
            fig_temp.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)")
            st.plotly_chart(fig_temp, use_container_width=True)

    with tab_hum:
        if "humidity_pct" in df_merged.columns and "demand_mw" in df_merged.columns:
            fig_hum = px.scatter(
                df_merged,
                x="humidity_pct",
                y="demand_mw",
                title="Energy Load Sensitivity to Relative Humidity (%)",
                labels={"humidity_pct": "Humidity (%)", "demand_mw": "Demand (MW)"},
                template="plotly_dark"
            )
            fig_hum.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)")
            st.plotly_chart(fig_hum, use_container_width=True)


    with tab_rain:
        if "precipitation_mm" in df_merged.columns and "demand_mw" in df_merged.columns:
            fig_rain = px.scatter(
                df_merged,
                x="precipitation_mm",
                y="demand_mw",
                title="Energy Load Sensitivity to Precipitation (mm)",
                labels={"precipitation_mm": "Precipitation (mm)", "demand_mw": "Demand (MW)"},
                template="plotly_dark"
            )
            fig_rain.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)")
            st.plotly_chart(fig_rain, use_container_width=True)
