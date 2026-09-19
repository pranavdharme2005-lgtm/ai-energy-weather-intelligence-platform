"""
Anomaly Detection Page (Stage 13).

Consumes Anomaly API via API Client with fallback error boundaries.
Renders anomaly timeline scatter plots, multi-variable filters, and severity breakdown.
Displays: Observed value, Expected value, Deviation, Severity, Reason, Detection method.
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

from app.frontend.utils.formatting import format_timestamp


def render():
    st.markdown("## ⚠️ Anomaly Detection & Grid Incident Center")
    st.caption("Stage 6 Automated statistical anomaly detection for energy consumption spikes, dips, and weather extremes")

    region = st.session_state.get("current_region", "Region-North")

    # Run detection check via API
    det_res = None
    try:
        det_res = api_client.detect_anomalies(region=region)
    except Exception as e:
        st.caption(f"Anomaly engine note: {e}")

    recent_anomalies = []
    try:
        recent_anomalies = api_client.get_recent_anomalies(limit=100)
    except Exception as e:
        st.warning(f"Anomaly retrieval notice: {e}")

    if not recent_anomalies:
        st.info("✅ No anomaly records detected in current database dataset.")
        return

    records = []
    for a in recent_anomalies:
        records.append({
            "id": a.get("id"),
            "timestamp": format_timestamp(a.get("timestamp")),
            "variable_name": a.get("variable_name") or a.get("metric_name") or "demand_mw",
            "severity": str(a.get("severity", "MEDIUM")).upper(),
            "observed_value": float(a.get("observed_value") or a.get("actual_value") or 0.0),
            "expected_value": float(a.get("expected_value") or 0.0),
            "deviation": float(a.get("deviation") or 0.0),
            "anomaly_score": float(a.get("anomaly_score") or a.get("z_score") or 0.0),
            "detection_method": a.get("detection_method") or "Z-Score / Isolation Forest",
            "reason": a.get("reason") or a.get("description") or "Spike detected"
        })
    df_anom = pd.DataFrame(records)

    # Interactive Filters
    st.subheader("🔍 Filter & Search Anomalies")
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        severities = ["ALL"] + sorted(list(df_anom["severity"].unique()))
        sel_sev = st.selectbox("Filter by Severity", severities, index=0)

    with col_f2:
        variables = ["ALL"] + sorted(list(df_anom["variable_name"].unique()))
        sel_var = st.selectbox("Filter by Metric/Variable", variables, index=0)

    with col_f3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Re-run Anomaly Engine", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Apply Filters
    filtered_df = df_anom.copy()
    if sel_sev != "ALL":
        filtered_df = filtered_df[filtered_df["severity"] == sel_sev]
    if sel_var != "ALL":
        filtered_df = filtered_df[filtered_df["variable_name"] == sel_var]

    # Summary KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Anomalies", len(filtered_df))
    col2.metric("Critical Incidents", len(filtered_df[filtered_df["severity"] == "CRITICAL"]))
    col3.metric("High Incidents", len(filtered_df[filtered_df["severity"] == "HIGH"]))
    avg_score = filtered_df["anomaly_score"].mean() if not filtered_df.empty else 0.0
    col4.metric("Avg Anomaly Score", f"{avg_score:.2f}")

    st.markdown("---")

    # Anomaly Timeline Chart
    st.subheader("📈 Interactive Anomaly Timeline")
    if not filtered_df.empty:
        fig = px.scatter(
            filtered_df,
            x="timestamp",
            y="observed_value",
            color="severity",
            size="anomaly_score",
            hover_data=["variable_name", "expected_value", "deviation", "reason", "detection_method"],
            color_discrete_map={
                "CRITICAL": "#EF4444",
                "HIGH": "#F97316",
                "MEDIUM": "#F59E0B",
                "LOW": "#3B82F6",
                "INFO": "#9CA3AF"
            },
            title="Anomaly Incidents Distribution",
            template="plotly_dark"
        )
        fig.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.6)",
            yaxis_title="Observed Value"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed Table
        st.subheader("📋 Incident Feed Table")
        st.dataframe(
            filtered_df[[
                "timestamp", "severity", "variable_name", "observed_value",
                "expected_value", "deviation", "anomaly_score", "detection_method", "reason"
            ]].sort_values("timestamp", ascending=False),
            use_container_width=True
        )
    else:
        st.info("No anomalies match the selected filters.")
