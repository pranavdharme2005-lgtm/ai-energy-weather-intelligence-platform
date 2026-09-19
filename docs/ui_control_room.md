# Stage 11 — Advanced Dynamic UI / Energy Control Room Documentation

## 1. Overview
The Stage 11 **Energy Control Room** provides an operational-grade, real-time analytics interface for grid operators and energy analysts. It consumes services and model outputs from Stages 2 through 10 directly from SQLite database repositories without duplicating ML or business logic.

---

## 2. Dynamic Weather-Reactive Theme Engine
The application automatically shifts visual presentation based on live meteorological telemetry and time of day via `app.frontend.components.theme_manager.get_dynamic_theme()`.

| Theme State | Trigger Condition | Background Accent | Header Gradient |
| :--- | :--- | :--- | :--- |
| **NIGHT** | Evening / Night hours (19:00 - 06:00) | `#0B0F19` | Dark Midnight |
| **STORM** | Heavy rain, thunderstorm, extreme weather | `#0F172A` | Deep Indigo Accent |
| **RAIN** | Light/moderate rain, drizzle, shower | `#0E1A2B` | Ocean Blue Accent |
| **CLOUDY** | Clouds, overcast, mist, fog | `#111827` | Slate Grey Accent |
| **CLEAR** | Sun, clear sky (default daytime) | `#0F172A` | Cyan Accent |

---

## 3. Application Navigation Structure
The Streamlit frontend sidebar implements 10 specialized sections:

1. **Control Room**: Executive dashboard featuring top 6 KPI cards, 24h Plotly actual vs forecast load trend, and Stage 9 daily intelligence briefing.
2. **Weather Intelligence**: Real-time ambient temperature, humidity, pressure, wind speed, cloud cover, precipitation, and Stage 4 XGBoost rain prediction metrics.
3. **Energy Forecast**: Stage 5 multi-step load forecasting with Plotly date range slider, 95% confidence intervals, and model uncertainty card.
4. **Rain Prediction**: Stage 4 ML rain risk evaluation with probability gauge, atmospheric feature breakdown, and precipitation-humidity correlation trace.
5. **Anomalies**: Stage 6 incident monitoring with severity filters (CRITICAL, HIGH, MEDIUM, LOW), anomaly scores, and incident scatter timeline.
6. **Alerts**: Stage 10 rule-based alert center with deduplication counters, severity badges, interactive `Acknowledge` and `Resolve` buttons, and web audio alert tones.
7. **What-If Simulator**: Stage 8 stress-testing interface with preset templates (Heatwave, Severe Storm, Cold Snap), training range boundary checks, and baseline vs scenario comparison charts.
8. **AI Energy Analyst**: Stage 9 natural language query copilot with structured findings, quantitative evidence, operational risk warnings, and deterministic fallback.
9. **Data Quality**: Stage 3 pipeline health score, null entry audit, duplicate record tracker, and schema validation.
10. **About / System Information**: Platform specification, pipeline architecture matrix (Stages 1-11), database/model health checks, and non-sensitive environment configuration.

---

## 4. Audio Alert Synthesizer
Audio alerts for `HIGH` and `CRITICAL` incidents are managed by `app.frontend.components.sound_manager.py`:
- Defaults to **OFF** to respect browser autoplay security policies.
- Utilizes Web Audio API oscillators to generate alert tones without external audio file dependencies.
- Session-state fingerprint deduplication prevents repetitive alert sounds for the same incident ID.

---

## 5. Verification & Testing
Stage 11 integration was validated with 88 automated pytest unit tests covering:
- Dynamic theme calculations across all 5 meteorological states.
- Web audio synthesizer triggering and deduplication logic.
- Headless rendering of all 10 frontend Control Room pages without exceptions.
