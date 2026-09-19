"""
Smart Alert Center Page (Stage 13).

Consumes Alerts API via API Client with fallback error boundaries.
Renders active/resolved alert cards with visual severity badges, alert counters,
deduplication fingerprints, interactive status buttons, and web audio alerts.
"""

import streamlit as st
import pandas as pd

from app.frontend.api_client import api_client
from app.frontend.components.sound_manager import trigger_alert_sound
from app.frontend.utils.formatting import format_timestamp, format_status_badge


def render():
    st.markdown("## 🚨 Smart Alert Center & Incident Operations")
    st.caption("Stage 10 Rule-based multi-tier alert engine with fingerprint deduplication and state tracking")

    all_alerts = []
    try:
        all_alerts = api_client.get_alerts(limit=50)
    except Exception as e:
        st.warning(f"Alert service notice: {e}")

    active_alerts = [a for a in all_alerts if str(a.get("status", "")).upper() in ["ACTIVE", "ACKNOWLEDGED"]] if all_alerts else []

    # Alert Counters & Severity Breakdown
    total_active = len(active_alerts)
    crit_count = sum(1 for a in active_alerts if str(a.get("severity", "")).upper() == "CRITICAL")
    high_count = sum(1 for a in active_alerts if str(a.get("severity", "")).upper() == "HIGH")
    med_count = sum(1 for a in active_alerts if str(a.get("severity", "")).upper() in ["MEDIUM", "LOW"])
    resolved_count = sum(1 for a in all_alerts if str(a.get("status", "")).upper() == "RESOLVED")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Active Alerts", total_active)
    col2.metric("Critical", crit_count)
    col3.metric("High", high_count)
    col4.metric("Medium/Low", med_count)
    col5.metric("Resolved", resolved_count)

    st.markdown("---")

    # Tabs for Active vs All Alerts
    tab_active, tab_all = st.tabs(["🔴 Active Alerts Feed", "📜 Incident History Log"])

    with tab_active:
        if not active_alerts:
            st.success("✅ Operational status clear. No active un-resolved alerts.")
        else:
            for alert in active_alerts:
                sev = str(alert.get("severity", "INFO")).upper()
                alert_id = str(alert.get("id"))

                # Trigger sound if HIGH or CRITICAL
                trigger_alert_sound(sev, alert_id)

                # Dynamic border colors based on visual hierarchy
                border_color = "#EF4444" if sev == "CRITICAL" else "#F97316" if sev == "HIGH" else "#F59E0B" if sev == "MEDIUM" else "#3B82F6"
                bg_color = "rgba(239, 68, 68, 0.1)" if sev in ["CRITICAL", "HIGH"] else "rgba(30, 41, 59, 0.8)"

                timestamp_fmt = format_timestamp(alert.get("timestamp"))

                st.markdown(f"""
                <div style="background:{bg_color}; border-left: 6px solid {border_color}; border-radius:8px; padding:16px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="background:{border_color}; color:#FFFFFF; padding:2px 8px; border-radius:4px; font-weight:700; font-size:0.8rem;">
                                {sev}
                            </span>
                            <span style="margin-left:10px; font-size:1.1rem; font-weight:700; color:#F8FAFC;">
                                {alert.get('title') or alert.get('alert_type') or 'System Alert'}
                            </span>
                        </div>
                        <div style="color:#94A3B8; font-size:0.85rem;">
                            ⏱️ {timestamp_fmt}
                        </div>
                    </div>
                    <div style="margin-top:10px; color:#E2E8F0; font-size:0.95rem;">
                        <b>Category:</b> {alert.get('category', 'GENERAL')} | <b>Status:</b> {format_status_badge(alert.get('status', 'ACTIVE'))}
                    </div>
                    <div style="margin-top:4px; color:#CBD5E1; font-size:0.9rem;">
                        <b>Message:</b> {alert.get('message') or alert.get('reason') or 'No detail provided.'}
                    </div>
                    <div style="margin-top:6px; color:#64748B; font-size:0.75rem;">
                        ID: #{alert_id} | Status: {alert.get('status', 'ACTIVE')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Interactive State Transition Buttons via API Client
                col_btn1, col_btn2, _ = st.columns([1, 1, 4])
                with col_btn1:
                    if st.button(f"Acknowledge #{alert_id}", key=f"ack_{alert_id}"):
                        api_client.acknowledge_alert(int(alert_id))
                        st.rerun()
                with col_btn2:
                    if st.button(f"Resolve #{alert_id}", key=f"res_{alert_id}"):
                        api_client.resolve_alert(int(alert_id))
                        st.rerun()

    with tab_all:
        if not all_alerts:
            st.info("No alert history found.")
        else:
            df_all = pd.DataFrame(all_alerts)
            st.dataframe(df_all, use_container_width=True)
