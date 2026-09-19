"""
Control Room — Main Command Center Dashboard View (Stage 13).

Consumes data via API Client with fallback error boundaries.
Displays: Current Demand, Forecast Demand, Demand Change, Temperature,
Humidity, Rain Probability, Active Alerts, Anomalies, Data Quality, and Today's Intelligence.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[3])
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from app.frontend.api_client import api_client

from app.frontend.utils.formatting import (
    format_mw,
    format_temp,
    format_percent,
    format_timestamp
)


def render():
    st.markdown("## 🕹️ Energy Control Room — Command Center")

    region = st.session_state.get("current_region", "Region-North")
    location = st.session_state.get("current_location", "Central Station")

    # Safe API Fetches with Error Boundaries
    curr_weather = None
    try:
        curr_weather = api_client.get_current_weather(location=location)
    except Exception as e:
        st.caption(f"Weather service note: {e}")

    curr_energy = None
    try:
        curr_energy = api_client.get_current_energy(region=region)
    except Exception as e:
        st.caption(f"Energy service note: {e}")

    forecast_res = None
    try:
        forecast_res = api_client.get_forecast(region=region, horizon_hours=24)
    except Exception as e:
        st.caption(f"Forecast service note: {e}")

    rain_res = None
    try:
        rain_res = api_client.predict_rain(location=location)
    except Exception as e:
        st.caption(f"Rain service note: {e}")

    active_alerts = []
    try:
        active_alerts = api_client.get_active_alerts()
    except Exception as e:
        st.caption(f"Alert service note: {e}")

    ai_briefing = None
    try:
        ai_briefing = api_client.ask_ai_analyst("Generate executive daily energy briefing", region=region)
    except Exception as e:
        st.caption(f"AI Analyst note: {e}")

    # Extract metrics safely
    curr_demand = curr_energy.get("demand_mw") if curr_energy else None
    curr_demand_time = format_timestamp(curr_energy.get("timestamp")) if curr_energy else "N/A"

    forecast_val = None
    forecast_points = forecast_res.get("forecasts", []) if forecast_res else []
    if forecast_points:
        forecast_val = forecast_points[0].get("forecasted_demand_mw")

    demand_change_pct = None
    if curr_demand is not None and forecast_val is not None and forecast_val > 0:
        demand_change_pct = ((curr_demand - forecast_val) / forecast_val) * 100.0

    rain_prob = rain_res.get("probability", 0.0) if rain_res else 0.0
    curr_temp = curr_weather.get("temperature_c") if curr_weather else None
    weather_cond = curr_weather.get("weather_condition", "Unknown") if curr_weather else "Unknown"

    alert_count = len(active_alerts)
    crit_count = sum(1 for a in active_alerts if str(a.get("severity", "")).upper() in ["CRITICAL", "HIGH"])

    # Top 6 KPI Cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Current Demand</div>
            <div class="kpi-value">{format_mw(curr_demand, decimals=0)}</div>
            <div class="kpi-unit">{region}</div>
            <div class="kpi-subtext">Time: {curr_demand_time}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Forecast Demand</div>
            <div class="kpi-value">{format_mw(forecast_val, decimals=0)}</div>
            <div class="kpi-unit">Stage 5 Model</div>
            <div class="kpi-subtext">Next Hour Horizon</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        change_str = f"{demand_change_pct:+.1f}%" if demand_change_pct is not None else "N/A"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Demand Variance</div>
            <div class="kpi-value">{change_str}</div>
            <div class="kpi-unit">vs Forecast</div>
            <div class="kpi-subtext">Actual Delta</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Rain Probability</div>
            <div class="kpi-value">{format_percent(rain_prob, decimals=1)}</div>
            <div class="kpi-unit">Stage 4 ML</div>
            <div class="kpi-subtext">Location: {location}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Temperature</div>
            <div class="kpi-value">{format_temp(curr_temp)}</div>
            <div class="kpi-unit">Ambient</div>
            <div class="kpi-subtext">{weather_cond}</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Active Alerts</div>
            <div class="kpi-value">{alert_count}</div>
            <div class="kpi-unit">Stage 10 Rules</div>
            <div class="kpi-subtext">⚠️ {crit_count} High/Critical</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Today's Intelligence Executive Briefing (Stage 9 AI Energy Analyst Output)
    st.subheader("💡 Today's Intelligence — Executive Summary")
    if ai_briefing and isinstance(ai_briefing, dict):
        summary_text = ai_briefing.get("answer") or ai_briefing.get("executive_summary") or "No briefing available."
        grid_status = ai_briefing.get("grid_status", "STABLE")
        weather_assess = ai_briefing.get("weather_assessment", "NORMAL")

        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            st.markdown(f"**Executive Briefing:** {summary_text}")
            st.markdown(f"**Grid Condition:** `{grid_status}` | **Weather Assessment:** `{weather_assess}`")
        with col_b2:
            findings = ai_briefing.get("key_findings", [])
            if findings:
                st.markdown("**Key Operational Insights:**")
                for kf in findings[:3]:
                    st.markdown(f"- {kf}")
    else:
        st.info("Today's intelligence briefing temporarily unavailable.")

    st.markdown("---")

    # 24h Actual vs Forecast Demand Chart
    st.subheader("📈 24-Hour Energy Load & Forecast Trend")

    energy_hist = api_client.get_energy_history(region=region, limit=48)
    if not energy_hist:
        try:
            from app.database.session import SessionLocal
            from app.database.repository import EnergyRepository
            with SessionLocal() as db:
                recs = EnergyRepository.get_latest(db, region=region, limit=48)
                energy_hist = [
                    {"timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp), "demand_mw": r.demand_mw}
                    for r in recs
                ]
        except Exception:
            energy_hist = []

    if energy_hist:
        df_hist = pd.DataFrame(energy_hist)
        if "timestamp" in df_hist.columns and "demand_mw" in df_hist.columns:
            df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
            df_hist = df_hist.sort_values("timestamp")

            fig = go.Figure()

            # Historical Actual Demand line
            fig.add_trace(go.Scatter(
                x=df_hist["timestamp"],
                y=df_hist["demand_mw"],
                mode="lines+markers",
                name="Actual Demand (MW)",
                line=dict(color="#38BDF8", width=2.5)
            ))

            # Add forecast trace if available
            if forecast_points:
                df_fc = pd.DataFrame(forecast_points)
                df_fc["timestamp"] = pd.to_datetime(df_fc["timestamp"])

                fig.add_trace(go.Scatter(
                    x=df_fc["timestamp"],
                    y=df_fc["forecasted_demand_mw"],
                    mode="lines",
                    name="Forecast Demand (MW)",
                    line=dict(color="#F59E0B", width=2.5, dash="dash")
                ))

                if "confidence_lower_mw" in df_fc.columns and "confidence_upper_mw" in df_fc.columns:
                    fig.add_trace(go.Scatter(
                        x=df_fc["timestamp"].tolist() + df_fc["timestamp"].tolist()[::-1],
                        y=df_fc["confidence_upper_mw"].tolist() + df_fc["confidence_lower_mw"].tolist()[::-1],
                        fill='toself',
                        fillcolor='rgba(245, 158, 11, 0.15)',
                        line=dict(color='rgba(255,255,255,0)'),
                        hoverinfo="skip",
                        showlegend=True,
                        name="95% Confidence Interval"
                    ))

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.6)",
                height=420,
                margin=dict(l=20, r=20, t=30, b=20),
                yaxis=dict(title=dict(text="Energy Demand (MW)", font=dict(color="#38BDF8"))),
                xaxis=dict(title="Timestamp"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ Telemetry pipeline actively seeding historical energy load readings.")

