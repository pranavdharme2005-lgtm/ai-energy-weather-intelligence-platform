# Stage 10 — Smart Alert Center

## Overview

The **Smart Alert Center** is the centralized operational monitoring and alerting module of the **AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform**. It evaluates real-time outputs across Stages 2–9—including energy demand readings, load forecasts, statistical anomalies, rain probabilities, extreme meteorological events, and data quality metrics—against explicit, documented rule conditions to trigger actionable alerts.

---

## Technical Architecture

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           System Context Data                          │
  │   (Real-Time Demand, Stage 4 Rain, Stage 5 Forecasts, Stage 6 Anomalies, │
  │    Stage 7 Weather Impact, Stage 8 What-If, Stage 3 Data Quality)     │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                        Smart Alert Rule Engine                         │
  │   (EnergySpike, EnergyDrop, ForecastDev, RainEvent, ExtremeWeather,    │
  │    DataQuality, ModelConfidence Rule Evaluators)                       │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 Deduplication & Cooldown Engine                        │
  │   - MD5 Fingerprinting: alert_type:region:source_event                 │
  │   - Cooldown Window: ALERT_COOLDOWN_MINUTES                            │
  │   - Dynamic Severity Escalation (MEDIUM -> HIGH allowed in cooldown)   │
  │   - Occurrence Count Accumulation                                      │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴────────────────────────────────────┐
  │                                                                        │
  ▼                                                                        ▼
┌───────────────────────────────┐                       ┌──────────────────┐
│ Alert ORM Table & Repository  │                       │  Optional Stage 9│
│ (ACTIVE/ACKNOWLEDGED/RESOLVED)│                       │  AI Explainer    │
└──────────────┬────────────────┘                       └────────┬─────────┘
               │                                                 │
               ▼                                                 ▼
┌───────────────────────────────┐                       ┌──────────────────┐
│ NotificationProvider Interface│                       │   UI Card View   │
│ (ConsoleNotificationProvider) │                       │   Data Structure │
└───────────────────────────────┘                       └──────────────────┘
```

---

## Core Operational Principles

### 1. Anomaly != Alert
A statistical anomaly (e.g. a minor 1.5 $\sigma$ z-score fluctuation) does **not** automatically trigger an alert. Alerts are produced only when explicit, documented operational thresholds (magnitude, persistence, baseline deviation, forecast headroom risk) are breached.

### 2. Zero LLM Alert Decision Guarantee
Alert evaluation, severity classification (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and state transitions (`ACTIVE` → `ACKNOWLEDGED` → `RESOLVED`) are 100% rule-based and deterministic. The Stage 9 AI Analyst is invoked *only* to append optional human-readable explanations *after* a deterministic alert is created.

---

## Alert Categories & Threshold Rules

| Alert Category | Trigger Condition | Default Severity | Source Module |
| :--- | :--- | :--- | :--- |
| **`ENERGY_DEMAND_SPIKE`** | Demand $\ge 3500.0\text{ MW}$ or $> 30\%$ above rolling mean | `HIGH` ($\ge 4000\text{ MW}$ $\rightarrow$ `CRITICAL`) | Stage 2 Ingestion |
| **`ENERGY_DEMAND_DROP`** | Demand $\le 1500.0\text{ MW}$ or $< 35\%$ of rolling mean | `MEDIUM` ($\le 1000\text{ MW}$ $\rightarrow$ `HIGH`) | Stage 2 Ingestion |
| **`PREDICTED_PEAK`** | 24h forecasted peak $\ge 3400.0\text{ MW}$ | `MEDIUM` ($\ge 3800\text{ MW}$ $\rightarrow$ `HIGH`) | Stage 5 Forecasting |
| **`FORECAST_DEVIATION`** | Residual $> 15\%$ or demand outside $95\%$ confidence bounds | `MEDIUM` ($> 25\%$ $\rightarrow$ `HIGH`) | Stage 5 Forecasting |
| **`RAIN_EVENT`** | Rain probability $\ge 60.0\%$ | `LOW` ($\ge 80.0\%$ $\rightarrow$ `MEDIUM`) | Stage 4 Rain Model |
| **`EXTREME_WEATHER`** | Temp $\ge 35.0^\circ\text{C}$, $\le 0.0^\circ\text{C}$, or Storm condition | `MEDIUM` ($\ge 40.0^\circ\text{C}$ / Storm $\rightarrow$ `HIGH`) | Stage 2 Weather |
| **`DATA_QUALITY`** | Quality score $< 90.0\%$ or timestamp gaps $> 0$ | `LOW` ($< 80.0\%$ $\rightarrow$ `MEDIUM`) | Stage 3 Quality |
| **`MODEL_CONFIDENCE`** | Out-of-range historical feature warning or interval width $> 800\text{ MW}$ | `LOW` (Both $\rightarrow$ `MEDIUM`) | Stage 5 & 8 Models |

---

## Alert Lifecycle, Cooldown & Escalation

### 1. Fingerprinting & Deduplication
Every alert receives a deterministic MD5 fingerprint ID:
$$\text{alert\_id} = \text{MD5}(\text{alert\_type} : \text{region} : \text{source\_event\_bucket})$$
If an active or acknowledged alert with the same `alert_id` exists in the database:
- `occurrence_count` is incremented.
- `last_seen_at` timestamp is updated.

### 2. Cooldown Window
If an active alert was evaluated within `ALERT_COOLDOWN_MINUTES` (default 30 min):
- Duplicate notification dispatches are suppressed to prevent alert spam.

### 3. Severity Escalation
If a repeated event has a higher severity than the active record (e.g. `MEDIUM` $\rightarrow$ `HIGH`), cooldown notification suppression is bypassed, and the active alert severity and message are updated immediately.

### 4. Automatic Resolution
When metric parameters return to normal operating boundaries (e.g. demand drops below 3300 MW after a spike alert), `SmartAlertEngine.evaluate_resolutions()` automatically transitions the alert status from `ACTIVE` to `RESOLVED` and sets the `resolved_at` timestamp.

---

## Database Schema (`alerts` Table)

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id VARCHAR(100) NOT NULL INDEX,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL INDEX,
    region VARCHAR(100) NOT NULL DEFAULT 'Grid_Alpha',
    title VARCHAR(150) NOT NULL,
    message VARCHAR(500) NOT NULL,
    reason VARCHAR(500),
    observed_value FLOAT,
    expected_value FLOAT,
    deviation FLOAT,
    source VARCHAR(100) DEFAULT 'rule_engine',
    detection_method VARCHAR(100) DEFAULT 'threshold_rule',
    model_version VARCHAR(50) DEFAULT 'v1.0.0',
    occurrence_count INTEGER DEFAULT 1,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP
);
```

---

## Execution Guide

### 1. Run CLI Runner
```bash
py run.py alerts
```

### 2. Run Automated Test Suite
```bash
py run.py test
```

---

## Senior Engineering Interview Q&A

### Q1: How does your Smart Alert Center avoid alert spam in production?
> **Answer**: We employ a 4-tier anti-spam architecture:
> 1. **Anomaly vs Alert Distinction**: Statistical anomalies are filtered so only operational threshold breaches produce alerts.
> 2. **MD5 Fingerprinting**: Related events collapse into a single composite `alert_id`.
> 3. **Occurrence Accumulation & Cooldown**: Repeated events within `ALERT_COOLDOWN_MINUTES` increment `occurrence_count` without re-notifying operators.
> 4. **Automatic Resolution**: Alerts automatically transition to `RESOLVED` when parameters normalize, preventing stale alerts from cluttering operator views.

### Q2: Why is the LLM not responsible for triggering alerts or setting severity?
> **Answer**: Operational safety requires deterministic, repeatable, and auditable logic. LLMs carry non-deterministic temperature risk and potential hallucination. In our design, rule evaluators code-enforce severity (`INFO` through `CRITICAL`), and the AI Analyst is used strictly for optional human explanations after deterministic triggering.
