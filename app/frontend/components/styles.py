"""Modern Custom CSS Injection for Energy Control Center UI."""

import streamlit as st


def inject_custom_css():
    """Injects high-end modern dark energy control center CSS styling into Streamlit."""
    custom_css = """
    <style>
    /* Dark Energy Control Center Theme Styling */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    .stSidebar {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* Executive Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
        margin-bottom: 15px;
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
        margin-bottom: 4px;
    }
    .metric-delta {
        font-size: 0.85rem;
        font-weight: 600;
    }
    .delta-positive { color: #34d399; }
    .delta-negative { color: #f87171; }
    .delta-neutral { color: #38bdf8; }

    /* Custom Header Banner */
    .control-center-banner {
        background: linear-gradient(90deg, #1e1b4b 0%, #311b92 50%, #0f172a 100%);
        border: 1px solid #4338ca;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
    }
    .banner-title {
        font-size: 1.75rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.025em;
        margin: 0;
    }
    .banner-subtitle {
        font-size: 0.95rem;
        color: #c7d2fe;
        margin-top: 6px;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
