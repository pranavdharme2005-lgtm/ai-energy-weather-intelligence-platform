"""
Streamlit Frontend Main Application Entry Point for Stage 13 Energy Control Room.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add project root directory to index 0 of python path for modular import resolution
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


from app.config.settings import settings
from app.frontend.api_client import api_client
from app.frontend.components.styles import inject_custom_css
from app.frontend.components.theme_manager import get_dynamic_theme, generate_theme_css
from app.frontend.components.sound_manager import render_sound_controls

# Import page view handlers
from app.frontend.pages import (
    overview,
    live_energy,
    forecast,
    rain_prediction,
    anomaly_center,
    smart_alerts,
    simulator,
    ai_analyst,
    weather_impact,
    data_quality,
    settings_page
)

# Page Layout Configuration
st.set_page_config(
    page_title=f"{settings.APP_NAME} — Energy Control Room",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom base styling
inject_custom_css()

# Global State Initialization
if "current_region" not in st.session_state:
    st.session_state.current_region = settings.DEFAULT_REGION

if "current_location" not in st.session_state:
    st.session_state.current_location = settings.DEFAULT_LOCATION

# Fetch API Health Status
api_health = api_client.get_health()
api_online = api_health.get("status") in ("healthy", "ONLINE")

# Fetch current weather via API Client to apply dynamic weather-reactive theme
weather_cond = "Clear"
timestamp_str = datetime.now().isoformat()

curr_weather = api_client.get_current_weather(location=st.session_state.current_location)
if curr_weather:
    weather_cond = curr_weather.get("weather_condition", "Clear") or "Clear"
    timestamp_str = str(curr_weather.get("timestamp", datetime.now().isoformat()))

# Apply Dynamic Weather-Reactive Theme
theme = get_dynamic_theme(weather_condition=weather_cond, timestamp=timestamp_str)
st.markdown(generate_theme_css(theme), unsafe_allow_html=True)

# Sidebar Header & Brand
st.sidebar.title("⚡ Energy Control Room")
st.sidebar.caption("Real-Time Energy Intelligence Platform v1.0.0")

# API & Theme Status Badges
status_color = "#10B981" if api_online else "#F59E0B"
status_text = "API ONLINE" if api_online else "LOCAL FALLBACK"
st.sidebar.markdown(
    f"<span class='status-pill'>{theme['status_badge']}</span> "
    f"<span class='status-pill' style='background:rgba(16,185,129,0.1); color:{status_color}; border:1px solid {status_color};'>● {status_text}</span>",
    unsafe_allow_html=True
)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

from app.config.settings import settings, SUPPORTED_LOCATIONS

# Global Location & Region Selectors
curr_loc = st.session_state.get("current_location", settings.DEFAULT_LOCATION)
loc_index = SUPPORTED_LOCATIONS.index(curr_loc) if curr_loc in SUPPORTED_LOCATIONS else 0

selected_location = st.sidebar.selectbox(
    "📍 Monitored Location / City",
    SUPPORTED_LOCATIONS,
    index=loc_index
)
st.session_state.current_location = selected_location

selected_region = st.sidebar.selectbox(
    "⚡ Monitored Region",
    ["Region-North", "Region-South", "Region-East", "Region-West"],
    index=0
)
st.session_state.current_region = selected_region

# Navigation Menu across 11 core sections
page_choice = st.sidebar.radio(
    "Application Navigation",
    [
        "1. Control Room",
        "2. Weather Intelligence",
        "3. Energy Forecast",
        "4. Rain Prediction",
        "5. Anomalies",
        "6. Alerts",
        "7. What-If Simulator",
        "8. AI Energy Analyst",
        "9. Weather Impact Analytics",
        "10. Data Quality",
        "11. About / System Info"
    ],
    index=0
)

# Refresh Controls & Time Indicator
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Data Refresh")
col_ref1, col_ref2 = st.sidebar.columns([1, 1])
with col_ref1:
    if st.button("Manual Refresh", use_container_width=True):
        st.cache_data.clear()
        st.session_state.last_refresh = datetime.now().strftime("%H:%M:%S")
        st.rerun()

auto_refresh = st.sidebar.toggle("Auto-Refresh", value=False)
if auto_refresh:
    refresh_interval = st.sidebar.slider("Interval (sec)", min_value=10, max_value=300, value=60, step=10)
    st.sidebar.caption(f"Refreshing automatically every {refresh_interval}s")

last_ref = st.session_state.get("last_refresh", datetime.now().strftime("%H:%M:%S"))
st.sidebar.caption(f"Last updated: {last_ref}")

# Sound Alerts Control Manager
render_sound_controls()

# Main Header Banner across all pages
st.markdown(
    f"""
    <div class="control-room-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin:0; color:#FFFFFF;">{settings.APP_NAME}</h2>
                <p style="margin:2px 0 0 0; color:#94A3B8; font-size:0.9rem;">
                    Location: <b>{st.session_state.current_location}</b> | Region: <b>{st.session_state.current_region}</b> | Status: <span style="color:{status_color};">● {status_text}</span> | Mode: <b>{theme['name']}</b>
                </p>
            </div>
            <div style="text-align: right; color:#94A3B8; font-size:0.85rem;">
                <div><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                <div><b>Data Freshness:</b> Real-time Ingestion</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Prominent Top Control Bar for Location Selection
col_hdr_left, col_hdr_right = st.columns([3, 1])
with col_hdr_left:
    st.markdown(f"### 📍 Active Monitored Location: **{st.session_state.current_location}**")
with col_hdr_right:
    curr_l = st.session_state.get("current_location", settings.DEFAULT_LOCATION)
    idx_l = SUPPORTED_LOCATIONS.index(curr_l) if curr_l in SUPPORTED_LOCATIONS else 0
    top_city = st.selectbox(
        "📍 Change City / Location",
        SUPPORTED_LOCATIONS,
        index=idx_l,
        key="top_location_selectbox"
    )
    if top_city != st.session_state.current_location:
        st.session_state.current_location = top_city
        st.rerun()

st.markdown("---")

# Page Routing Engine
if page_choice == "1. Control Room":
    overview.render()
elif page_choice == "2. Weather Intelligence":
    live_energy.render()
elif page_choice == "3. Energy Forecast":
    forecast.render()
elif page_choice == "4. Rain Prediction":
    rain_prediction.render()
elif page_choice == "5. Anomalies":
    anomaly_center.render()
elif page_choice == "6. Alerts":
    smart_alerts.render()
elif page_choice == "7. What-If Simulator":
    simulator.render()
elif page_choice == "8. AI Energy Analyst":
    ai_analyst.render()
elif page_choice == "9. Weather Impact Analytics":
    weather_impact.render()
elif page_choice == "10. Data Quality":
    data_quality.render()
elif page_choice == "11. About / System Info":
    settings_page.render()

# Sidebar Footer
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 AI Energy Intelligence & Weather Analytics")
