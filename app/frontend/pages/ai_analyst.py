"""
AI Energy Analyst Interactive Panel (Stage 13).

Consumes AI API via API Client with fallback error boundaries.
Provides natural language grid intelligence querying with grounded evidence,
structured key findings, operational risk warnings, and deterministic fallback.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[3])
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from app.frontend.api_client import api_client



def render():
    st.markdown("## 🤖 AI Energy Analyst — Natural Language Intelligence Copilot")
    st.caption("Stage 9 AI Analyst providing grounded grid insights, operational root causes, and weather impact explanations")

    region = st.session_state.get("current_region", "Region-North")

    # Executive Daily Intelligence Briefing Section
    st.subheader("💡 Today's Intelligence Executive Briefing")
    briefing = None
    try:
        briefing = api_client.ask_ai_analyst("Generate executive daily intelligence briefing", region=region)
    except Exception as e:
        st.caption(f"AI Analyst notice: {e}")

    if briefing and isinstance(briefing, dict):
        summary_text = briefing.get("answer") or briefing.get("summary") or briefing.get("executive_summary") or "No briefing available."
        grid_status = briefing.get("grid_status", "NORMAL")
        weather_assess = briefing.get("weather_assessment", "STABLE")

        st.markdown(f"**Executive Briefing:** {summary_text}")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown(f"**Grid Status:** `{grid_status}`")
            st.markdown(f"**Weather Assessment:** `{weather_assess}`")
        with col_b2:
            findings = briefing.get("key_findings", [])
            if findings:
                st.markdown("**Key Findings:**")
                for kf in findings:
                    st.markdown(f"- {kf}")
    else:
        st.info("Daily intelligence briefing unavailable.")

    st.markdown("---")

    # Interactive Q&A Interface
    st.subheader("💬 Ask the AI Energy Analyst")

    # Sample prompt shortcuts
    st.caption("Quick Questions:")
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    sample_q = ""
    with col_q1:
        if st.button("What is causing today's demand increase?", use_container_width=True):
            sample_q = "What is causing today's demand increase?"
    with col_q2:
        if st.button("Is rain likely to affect demand?", use_container_width=True):
            sample_q = "Is rain likely to affect demand?"
    with col_q3:
        if st.button("Are there any unusual energy patterns?", use_container_width=True):
            sample_q = "Are there any unusual energy patterns?"
    with col_q4:
        if st.button("What happens if temp increases by 3°C?", use_container_width=True):
            sample_q = "What happens if temperature increases by 3°C?"

    # Text input field
    user_query = st.text_input("User Question Input", value=sample_q, placeholder="e.g. Is the current energy demand spike caused by high temperature?")

    if st.button("Ask Analyst", type="primary") or (user_query and user_query != st.session_state.get("last_query", "")):
        st.session_state.last_query = user_query
        if user_query.strip():
            with st.spinner("Analyzing real-time grid telemetries, weather forecasts, and anomaly records..."):
                analyst_resp = None
                try:
                    analyst_resp = api_client.ask_ai_analyst(user_query.strip(), region=region)
                except Exception as e:
                    st.error(f"Error querying AI Analyst: {e}")

            if analyst_resp and isinstance(analyst_resp, dict):
                st.markdown("### 📝 Analyst Response")

                answer_text = analyst_resp.get("answer") or analyst_resp.get("summary") or "No response available."
                st.markdown(f"**Summary:** {answer_text}")

                # Key Findings
                kf_list = analyst_resp.get("key_findings", [])
                if kf_list:
                    st.markdown("**🔍 Key Findings:**")
                    for kf in kf_list:
                        st.markdown(f"- {kf}")

                # Quantitative Evidence
                evidence = analyst_resp.get("evidence", {})
                if evidence:
                    st.markdown("**📊 Quantitative Evidence:**")
                    for k, v in evidence.items():
                        st.markdown(f"- **{k}:** `{v}`")

                # Warnings
                warnings = analyst_resp.get("warnings", [])
                if warnings:
                    st.markdown("**⚠️ Operational Risk & Warnings:**")
                    for w in warnings:
                        st.warning(w)

                # Limitations & Provider Info
                provider = analyst_resp.get("provider", "Stage 9 Deterministic Rule Engine")
                limitations = analyst_resp.get("limitations", "Response based on current database state.")
                st.caption(f"Provider: `{provider}` | Limitations: {limitations}")
            else:
                st.warning("AI Analyst response currently unavailable.")
        else:
            st.info("Please enter a question to query the AI Energy Analyst.")
