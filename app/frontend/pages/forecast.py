"""
Energy Demand Forecasting Page (Stage 13).

Consumes Forecast API & Energy API via API Client with fallback error boundaries.
Renders Plotly interactive Actual vs Forecast chart, confidence bounds,
interactive time window controls, and model uncertainty metrics.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[3])
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.frontend.api_client import api_client

from app.frontend.utils.formatting import format_mw


def render():
    st.markdown("## 🔮 Energy Demand Forecasting Engine")
    st.caption("Stage 5 Machine Learning forecasting model with 95% confidence intervals and time slider analysis")

    region = st.session_state.get("current_region", "Region-North")

    # Time range selection & controls
    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        hist_hours = st.slider("Historical Window Display (Hours)", min_value=12, max_value=72, value=24, step=6)
    with col_ctrl2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Generate Fresh 24h Forecast", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    energy_hist = []
    try:
        energy_hist = api_client.get_energy_history(region=region, limit=hist_hours * 2)
    except Exception as e:
        st.warning(f"Historical energy notice: {e}")

    forecast_res = None
    try:
        forecast_res = api_client.get_forecast(region=region, horizon_hours=24)
    except Exception as e:
        st.warning(f"Forecast service notice: {e}")

    forecast_points = forecast_res.get("forecasts", []) if forecast_res else []

    if not energy_hist and not forecast_points:
        st.warning("Data unavailable: No historical readings or forecast outputs found.")
        return

    df_hist = pd.DataFrame(energy_hist) if energy_hist else pd.DataFrame()
    if not df_hist.empty and "timestamp" in df_hist.columns:
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
        df_hist = df_hist.sort_values("timestamp")

    df_fc = pd.DataFrame(forecast_points) if forecast_points else pd.DataFrame()
    if not df_fc.empty and "timestamp" in df_fc.columns:
        df_fc["timestamp"] = pd.to_datetime(df_fc["timestamp"])

    # Forecast Uncertainty & Metrics Card
    st.subheader("📊 Forecast Metrics & Uncertainty Card")
    col1, col2, col3, col4 = st.columns(4)

    next_val = df_fc["forecasted_demand_mw"].iloc[0] if (not df_fc.empty and "forecasted_demand_mw" in df_fc.columns) else None
    lower_val = df_fc["confidence_lower_mw"].iloc[0] if (not df_fc.empty and "confidence_lower_mw" in df_fc.columns) else None
    upper_val = df_fc["confidence_upper_mw"].iloc[0] if (not df_fc.empty and "confidence_upper_mw" in df_fc.columns) else None

    uncertainty_level = "Moderate"
    model_name = forecast_res.get("model_version", "Stage 5 Ridge/LGBM") if forecast_res else "N/A"

    col1.metric("Next-Hour Forecast", format_mw(next_val))
    col2.metric("Lower 95% Bound", format_mw(lower_val))
    col3.metric("Upper 95% Bound", format_mw(upper_val))
    col4.metric("Uncertainty Level", uncertainty_level)

    if lower_val is not None and upper_val is not None:
        st.info(f"💡 **Forecast Range:** {format_mw(lower_val, decimals=0)} – {format_mw(upper_val, decimals=0)} | **Active Model:** `{model_name}`")
    else:
        st.info("Forecast uncertainty details: Standard point forecast displayed.")

    st.markdown("---")

    # Interactive Plotly Actual vs Forecast Visualization with Time Slider
    st.subheader("📈 Interactive Load Trajectory: Historical → Forecast Transition")

    fig = go.Figure()

    if not df_hist.empty and "demand_mw" in df_hist.columns:
        fig.add_trace(go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["demand_mw"],
            mode="lines+markers",
            name="Historical Actual Demand (MW)",
            line=dict(color="#38BDF8", width=2.5)
        ))

    if not df_fc.empty and "forecasted_demand_mw" in df_fc.columns:
        fig.add_trace(go.Scatter(
            x=df_fc["timestamp"],
            y=df_fc["forecasted_demand_mw"],
            mode="lines+markers",
            name="Forecast Demand (MW)",
            line=dict(color="#F59E0B", width=3, dash="dash")
        ))

        if "confidence_lower_mw" in df_fc.columns and "confidence_upper_mw" in df_fc.columns:
            fig.add_trace(go.Scatter(
                x=df_fc["timestamp"].tolist() + df_fc["timestamp"].tolist()[::-1],
                y=df_fc["confidence_upper_mw"].tolist() + df_fc["confidence_lower_mw"].tolist()[::-1],
                fill='toself',
                fillcolor='rgba(245, 158, 11, 0.18)',
                line=dict(color='rgba(255,255,255,0)'),
                hoverinfo="skip",
                showlegend=True,
                name="95% Confidence Interval"
            ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.6)",
        height=460,
        xaxis=dict(
            title="Timestamp",
            rangeslider=dict(visible=True),
            type="date"
        ),
        yaxis=dict(title=dict(text="Energy Load (MW)", font=dict(color="#38BDF8"))),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabular Forecast Point View
    if not df_fc.empty:
        with st.expander("📋 Detailed 24-Hour Multi-Step Forecast Table"):
            st.dataframe(df_fc, use_container_width=True)
