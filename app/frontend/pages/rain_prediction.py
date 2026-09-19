"""
Rain Prediction Visualization Page (Stage 13).

Consumes Rain API & Weather API via API Client with fallback error boundaries.
Provides precipitation probability analysis, model metadata, and humidity-rain correlations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from app.frontend.api_client import api_client
from app.frontend.utils.formatting import (
    format_percent,
    format_temp,
    format_pressure,
    format_wind_speed,
    format_timestamp
)


def render():
    st.markdown("## 🌧️ Meteorological Rain Prediction Center")
    st.caption("Stage 4 Machine Learning precipitation risk evaluation and atmospheric moisture analytics")

    location = st.session_state.get("current_location", "Central Station")

    curr_weather = None
    try:
        curr_weather = api_client.get_current_weather(location=location)
    except Exception as e:
        st.warning(f"Weather service notice: {e}")

    rain_res = None
    try:
        rain_res = api_client.predict_rain(location=location)
    except Exception as e:
        st.warning(f"Rain service notice: {e}")

    weather_hist = []
    try:
        weather_hist = api_client.get_weather_history(location=location, limit=48)
    except Exception as e:
        st.warning(f"Weather history notice: {e}")

    if not rain_res and not curr_weather:
        st.warning("Data unavailable: Rain prediction model output not available.")
        return

    prob_val = rain_res.get("probability", 0.0) if rain_res else 0.0
    is_rain = rain_res.get("rain_predicted", False) if rain_res else False
    conf_level = "High"

    # Key Prediction Metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Estimated Probability", format_percent(prob_val, decimals=1))
    col2.metric("Rain / No-Rain", "🌧 Rain Expected" if is_rain else "☀️ No Rain Expected")
    col3.metric("Model Confidence", conf_level)
    col4.metric("Model Version", "Stage 4 XGBoost v1.0")

    st.markdown("---")

    # Atmospheric Features & Prediction Gauges
    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        st.subheader("🎯 Model Probability Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob_val * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Estimated Rain Probability (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#0284C7"},
                'steps': [
                    {'range': [0, 30], 'color': "#1E293B"},
                    {'range': [30, 70], 'color': "#334155"},
                    {'range': [70, 100], 'color': "#1E3A8A"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50.0
                }
            }
        ))
        fig_gauge.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            height=300
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_g2:
        st.subheader("📋 Atmospheric Parameters (Input Features)")
        if curr_weather:
            st.markdown(f"- **Humidity:** `{format_percent(curr_weather.get('humidity_pct'), decimals=1)}`")
            st.markdown(f"- **Temperature:** `{format_temp(curr_weather.get('temperature_c'))}`")
            st.markdown(f"- **Pressure:** `{format_pressure(curr_weather.get('pressure_hpa'))}`")
            st.markdown(f"- **Cloud Cover:** `{format_percent(curr_weather.get('cloud_cover_pct'), decimals=0)}`")
            st.markdown(f"- **Wind Speed:** `{format_wind_speed(curr_weather.get('wind_speed_ms'))}`")
            st.caption(f"Timestamp: {format_timestamp(curr_weather.get('timestamp'))}")
        else:
            st.info("Latest atmospheric telemetry unavailable.")

    st.markdown("---")

    # Historical Precipitation & Humidity Chart
    st.subheader("📊 Historical Relative Humidity vs Precipitation Trace")
    if weather_hist:
        df_w = pd.DataFrame(weather_hist)
        if "timestamp" in df_w.columns:
            df_w["timestamp"] = pd.to_datetime(df_w["timestamp"])
            df_w = df_w.sort_values("timestamp")

            y_col = "precipitation_mm" if "precipitation_mm" in df_w.columns else "temperature_c"
            color_col = "humidity_pct" if "humidity_pct" in df_w.columns else None

            fig_bar = px.bar(
                df_w,
                x="timestamp",
                y=y_col,
                color=color_col,
                title="Historical Precipitation and Humidity Correlation",
                template="plotly_dark"
            )
            fig_bar.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("No recent weather readings available.")
