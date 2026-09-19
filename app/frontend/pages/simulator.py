"""
What-If Scenario Simulator Page (Stage 13).

Consumes Simulator API via API Client with fallback error boundaries.
Simulates energy demand under hypothetical weather shocks with preset templates,
training range boundary validation, and baseline vs scenario Plotly comparison.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[3])
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go

from app.frontend.api_client import api_client

from app.frontend.utils.formatting import format_mw, format_percent


def render():
    st.markdown("## 🎛️ What-If Energy Scenario Simulator")
    st.caption("Stage 8 Stress-testing energy demand curves against weather perturbations using Stage 5 models")

    region = st.session_state.get("current_region", "Region-North")

    # Preset Scenario Selector
    st.subheader("📋 Scenario Preset Templates")
    preset = st.selectbox(
        "Select Scenario Preset or Custom Inputs",
        [
            "Custom Inputs",
            "Extreme Heatwave (+5.0°C Temperature Spike)",
            "Severe Rainstorm & Humidity (+15% Humidity, +10mm Rain)",
            "Winter Cold Snap (-6.0°C Temperature Drop)",
            "High Wind Advisory (+8.0 m/s Wind Speed)"
        ]
    )

    # Default values based on preset selection
    temp_delta = 0.0
    hum_delta = 0.0
    precip_delta = 0.0
    wind_delta = 0.0

    if preset == "Extreme Heatwave (+5.0°C Temperature Spike)":
        temp_delta = 5.0
        hum_delta = -10.0
    elif preset == "Severe Rainstorm & Humidity (+15% Humidity, +10mm Rain)":
        temp_delta = -2.0
        hum_delta = 15.0
        precip_delta = 10.0
    elif preset == "Winter Cold Snap (-6.0°C Temperature Drop)":
        temp_delta = -6.0
        hum_delta = 5.0
    elif preset == "High Wind Advisory (+8.0 m/s Wind Speed)":
        wind_delta = 8.0

    col_input, col_results = st.columns([1, 1])

    with col_input:
        st.subheader("⚙️ Perturbation Controls")

        temp_val = st.slider("Temperature Change (°C)", min_value=-15.0, max_value=15.0, value=float(temp_delta), step=0.5)
        hum_val = st.slider("Humidity Change (%)", min_value=-40.0, max_value=40.0, value=float(hum_delta), step=1.0)
        precip_val = st.number_input("Precipitation Delta (mm)", min_value=0.0, max_value=50.0, value=float(precip_delta), step=1.0)
        wind_val = st.slider("Wind Speed Delta (m/s)", min_value=-10.0, max_value=20.0, value=float(wind_delta), step=0.5)

        # Define scenario overrides
        overrides = {}
        if temp_val != 0.0:
            overrides["temperature_c_delta"] = temp_val
        if hum_val != 0.0:
            overrides["humidity_pct_delta"] = hum_val
        if precip_val > 0.0:
            overrides["precipitation_mm_delta"] = precip_val
        if wind_val != 0.0:
            overrides["wind_speed_m_s_delta"] = wind_val

        st.button("🚀 Run Scenario Simulation", use_container_width=True)

    # Execute simulation via API Client
    request_data = {
        "scenario_overrides": overrides,
        "region": region,
        "horizon_hours": 24
    }

    sim_output = None
    try:
        sim_output = api_client.run_simulation(request_data)
    except Exception as e:
        st.warning(f"Simulator notice: {e}")

    with col_results:
        st.subheader("📊 Scenario Results & Metrics")
        if not sim_output:
            st.warning("Simulation result unavailable for specified parameters.")
            return

        base_mw = float(sim_output.get("baseline_demand_mw") or sim_output.get("baseline_forecast_mw") or 0.0)
        scen_mw = float(sim_output.get("scenario_demand_mw") or sim_output.get("scenario_forecast_mw") or 0.0)
        abs_diff = float(sim_output.get("absolute_change_mw") or sim_output.get("absolute_difference_mw") or (scen_mw - base_mw))
        pct_diff = float(sim_output.get("percentage_change") or sim_output.get("percentage_difference_pct") or 0.0)

        warnings = sim_output.get("training_range_warnings", [])
        if not warnings and sim_output.get("out_of_range_warning"):
            warnings = [str(sim_output.get("out_of_range_warning"))]

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Baseline Demand", format_mw(base_mw, decimals=0))
        col_r2.metric("Scenario Demand", format_mw(scen_mw, decimals=0))
        col_r3.metric("Net Change", f"{abs_diff:+,.0f} MW", delta=f"{pct_diff:+.2f}%")

        # Training Range Warning Display
        if warnings:
            for w in warnings:
                st.warning(f"⚠️ **Training Range Warning:** {w}")
        else:
            st.success("✅ Scenario parameters are within historical model training boundaries.")

        # Baseline vs Scenario Chart
        fig_bar = go.Figure(data=[
            go.Bar(name='Baseline Forecast', x=['Energy Demand'], y=[base_mw], marker_color='#38BDF8'),
            go.Bar(name='Scenario Forecast', x=['Energy Demand'], y=[scen_mw], marker_color='#F59E0B' if pct_diff >= 0 else '#10B981')
        ])
        fig_bar.update_layout(
            barmode='group',
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.6)",
            height=320,
            yaxis_title="Load (MW)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
