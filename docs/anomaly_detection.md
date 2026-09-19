# Energy & Weather Anomaly Detection Architecture & Technical Documentation

Production anomaly detection documentation for the **Energy & Weather Anomaly Detection Module** of the *AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform*.

---

## 1. Problem Definition & Core Objective

The Anomaly Detection Module identifies and classifies unexpected operational behavior across grid demand telemetries, weather observations, forecast residual errors, and joint multivariate feature spaces.

Key objectives:
- Identify abnormal load spikes, sudden dips, and grid structural breaks.
- Detect prediction interval breaches where actual grid demand strays from Stage 5 ML forecasts.
- Flag extreme meteorological occurrences (heatwaves, pressure drops, intense precipitation).
- Detect subtle non-linear multivariate relationship shifts using unsupervised learning (`IsolationForest`).
- Differentiate between **data-quality defects** vs. **legitimate real-world physical anomalies**.

---

## 2. Distinction: Data Quality Defects vs Real-World Anomalies

| Category | Description | Processing Stage | Example |
| :--- | :--- | :--- | :--- |
| **Data Quality Issue** | Ingested data corruption, missing fields, duplicate timestamps, or physically impossible values. | **Stage 3 Quality Engine** | `demand_mw = -500.0`, missing timestamp row, or `temperature = -120°C`. |
| **Real-World Anomaly** | Valid physical observation representing an unusual operational deviation or extreme environmental event. | **Stage 6 Anomaly Module** | Peak summer load at 3:00 AM (unusual load spike), heatwave $T = 39.5^\circ\text{C}$, or actual demand breaching upper forecast interval bounds. |

---

## 3. Four-Dimensional Anomaly Detection Architecture

### 1. Energy Demand Anomaly Detector (`demand_zscore` / `demand_iqr`)
- **Hourly Seasonal Baseline**: Evaluates demand observations against their specific hourly window $t \pmod{24}$ across historical days rather than a global fixed threshold.
- **Robust Z-score**:
  $$z = \frac{|y_{\text{actual}} - \text{Median}_{h}|}{\sigma_{\text{robust}}}, \quad \text{where } \sigma_{\text{robust}} = \max\left(25.0, \frac{\text{IQR}_{h}}{1.349}\right)$$
- **IQR Outlier Bounds**: $y_{\text{actual}} < Q1_h - 1.5 \cdot \text{IQR}_h$ or $y_{\text{actual}} > Q3_h + 1.5 \cdot \text{IQR}_h$.

### 2. Forecast-Based Anomaly Detector (`forecast_deviation`)
- Utilizes **Stage 5 ML Energy Forecaster** outputs and 95% confidence intervals (`confidence_lower_mw`, `confidence_upper_mw`).
- Flagged if actual demand $y_{\text{actual}}$ breaches confidence bounds:
  $$y_{\text{actual}} > \text{Upper Bound} \quad \text{or} \quad y_{\text{actual}} < \text{Lower Bound}$$

### 3. Weather Measurement Anomaly Detector (`weather_extreme`)
- Evaluates meteorological observations (`temperature_c`, `humidity_pct`, `pressure_hpa`, `wind_speed_ms`, `precipitation_mm`) against historical z-score distributions.
- Prevents flagging normal seasonal variations while capturing genuine weather extremes.

### 4. Multivariate Anomaly Detector (`multivariate_isolation`)
- Applies unsupervised `IsolationForest` (Scikit-Learn, 100 trees) on the joint feature matrix $\mathbf{X} = [\text{demand}, T, \text{humidity}, P, \text{wind}, \text{precip}]$.
- Identifies unusual joint feature relationships (e.g. normal temperature and normal humidity, but combined load is highly anomalous).

---

## 4. Anomaly Scoring & Severity Classification

All anomalies receive a normalized score in $[0.0, 1.0]$:
$$\text{Score} = \min\left(1.0, \frac{|z|}{5.0}\right)$$

### Severity Mapping Table:
| Score Range | Z-Score Equivalent | Severity Level | Operational Action |
| :--- | :--- | :--- | :--- |
| $< 0.30$ | $< 2.0$ | `NORMAL` | Standard grid operation. |
| $0.30 - 0.49$ | $2.0 - 2.8$ | `LOW` | Informational logging. |
| $0.50 - 0.69$ | $2.8 - 3.5$ | `MEDIUM` | Monitor regional substation load. |
| $0.70 - 0.87$ | $3.5 - 4.5$ | `HIGH` | Dispatch secondary reserve capacity. |
| $\ge 0.88$ | $\ge 4.5$ | `CRITICAL` | Trigger emergency demand response / grid alert. |

---

## 5. Database Schema (`anomalies` Table)

| Column | SQL Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY` | Auto-incrementing primary key. |
| `timestamp` | `TIMESTAMP WITH TIMEZONE` | Observation timestamp (UTC). |
| `region` | `VARCHAR(100)` | Regional grid identifier (`Grid_Alpha`). |
| `variable` | `VARCHAR(100)` | Target metric (`demand_mw`, `temperature_c`, etc.). |
| `actual_value` | `FLOAT` | Observed numerical measurement. |
| `expected_value` | `FLOAT` | Expected baseline/forecast value. |
| `deviation` | `FLOAT` | Difference ($y_{\text{actual}} - y_{\text{expected}}$). |
| `anomaly_score` | `FLOAT` | Normalized score in $[0.0, 1.0]$. |
| `severity` | `VARCHAR(20)` | `NORMAL`, `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`. |
| `anomaly_type` | `VARCHAR(50)` | `demand_zscore`, `forecast_deviation`, `weather_extreme`, `multivariate_isolation`. |
| `description` | `VARCHAR(500)` | Human-interpretable explanatory reason. |
| `detection_method` | `VARCHAR(100)` | Detection algorithm used. |
| `model_version` | `VARCHAR(50)` | Model version tag (`v1.0.0`). |

---

## 6. Standardized JSON Output Schema

```json
{
  "timestamp": "2026-09-19T10:00:00+00:00",
  "region": "Grid_Alpha",
  "variable": "demand_mw",
  "actual_value": 3520.5,
  "expected_value": 2950.0,
  "deviation": 570.5,
  "anomaly_score": 0.85,
  "severity": "HIGH",
  "anomaly_type": "forecast_deviation",
  "description": "Actual demand (3520.5 MW) breached Stage 5 forecast upper bound (3180.0 MW) by 340.5 MW relative to predicted expectation (2950.0 MW).",
  "detection_method": "forecast_residual_interval_breach",
  "model_version": "v1.0.0"
}
```

---

## 7. Technical Interview Q&A Section

### Question: "How does your system detect an abnormal energy event?"

> **Answer**:
> 1. **Multi-Layered Detection Strategy**: The platform employs a four-tiered approach combining statistical hourly seasonal z-scores, IQR bounds, forecast residual interval breaches, and unsupervised `IsolationForest` multivariate learning.
> 2. **Seasonal Time-Context Awareness**: Rather than applying a single static threshold, demand is evaluated against a robust median and IQR calculated for that specific hour of the day ($t \pmod{24}$). This prevents normal afternoon peak loads from being incorrectly flagged, while catching unusual off-peak midnight demand spikes.
> 3. **Forecast Residual Integration**: Actual real-time telemetries are continuously benchmarked against Stage 5 machine-learning load forecasts. If actual demand breaches the model's 95% confidence bounds ($\pm 1.96 \sigma_{\text{residuals}}$), a `forecast_deviation` anomaly is triggered with a human-interpretable explanation.
> 4. **Standardized Severity & Scoring**: Deviations are mapped into a normalized $[0, 1]$ score and categorized into `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` severity levels to drive downstream automated grid alerts.
