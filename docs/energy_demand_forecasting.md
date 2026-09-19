# Energy Demand Forecasting Architecture & ML Technical Documentation

Production machine learning documentation for the **Energy Demand Forecasting Module** of the *AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform*.

---

## 1. Problem Definition & Core Objective

The Energy Demand Forecasting Module provides short-term, multi-step grid load forecasting to predict regional power consumption ($\text{MW}$) over a **24-hour horizon** ($t+1h \dots t+24h$).

Key goals:
- Predict upcoming load profiles for grid balancing and peak dispatch planning.
- Quantify forecast uncertainty via **95% prediction intervals** (`confidence_lower_mw`, `confidence_upper_mw`).
- Extract peak load metrics (peak timestamp, peak MW, peak-to-average ratio) for downstream alerting engines.
- Ensure strict **zero look-ahead data leakage**.

---

## 2. Dataset & Detected Data Frequency

- **Data Source**: Regional Grid Consumption Records (`PJM_OpenData_Historical` / Open Energy Provider) merged with Open-Meteo Meteorological Observations.
- **Detected Data Frequency**: **Hourly (`1h`)**.
- **Primary Forecast Horizon**: **24 Hours (`24h`)**.

---

## 3. Predictor Feature Engineering & Zero Leakage Shield

Features are constructed with strict backward-looking shields to prevent future target information leakage into the model matrix $\mathbf{X}_t$:

```
                             Prediction Origin (t)
Historical Load (t-168h..t) |-------------> | [Forecast Horizon: t+1h .. t+24h]
Historical Weather (t-168h..t)               | Target: Demand at t+24h
Rain Probability P(Rain)                     |
```

### Feature Categories:
1. **Historical Demand Lags**:
   - `demand_mw_lag_1h`, `demand_mw_lag_2h`, `demand_mw_lag_3h`, `demand_mw_lag_6h`, `demand_mw_lag_12h`, `demand_mw_lag_24h`, `demand_mw_lag_48h`, `demand_mw_lag_168h` (1 week lag).
2. **Past-Only Rolling Statistics**:
   - Computed using `.shift(1)` to shield the current observation $t$:
     - `demand_mw_rolling_mean_6h`, `demand_mw_rolling_std_6h`
     - `demand_mw_rolling_mean_24h`, `demand_mw_rolling_std_24h`, `demand_mw_rolling_min_24h`, `demand_mw_rolling_max_24h`
     - `demand_mw_rolling_mean_168h` (7-day moving average).
3. **Temporal & Cyclical Encodings**:
   - `hour_sin = sin(2*pi*hour/24)`, `hour_cos = cos(2*pi*hour/24)`
   - `day_sin = sin(2*pi*dow/7)`, `day_cos = cos(2*pi*dow/7)`
   - `month_sin`, `month_cos`, `is_weekend`, `season`
4. **Meteorological Features**:
   - `temperature_c`, `humidity_pct`, `pressure_hpa`, `wind_speed_ms`, `cloud_cover_pct`, `precipitation_mm`.
5. **Rain Predictor Probability**:
   - `rain_probability` ($P(\text{Rain}) \in [0, 1]$) output from the Stage 4 ML Rain Prediction Module.

### Why Cyclical Encodings Are Essential:
In a standard integer representation, hour `23` and hour `0` have a numerical difference of `23`, even though they are only `1` hour apart in continuous time. Cyclical trigonometric encodings mapping $h \mapsto (\sin\frac{2\pi h}{24}, \cos\frac{2\pi h}{24})$ project timestamps onto a continuous unit circle in $\mathbb{R}^2$, allowing tree-based and linear models to preserve the continuous temporal distance between 23:00 and 00:00.

---

## 4. Train / Validation / Test Chronological Splitting

To evaluate time-series generalization without look-ahead shuffle:
- **Train Set (70%)**: First 70% of chronological observations.
- **Validation Set (15%)**: Middle 15% of historical observations (used for hyperparameter selection and residual interval estimation).
- **Test Set (15%)**: Final 15% of unseen future historical observations.

---

## 5. Candidate Benchmark & Model Evaluation Results

Models were benchmarked against naive non-ML baselines:

| Model Algorithm | Val MAE (MW) | Val RMSE (MW) | Val sMAPE (%) | Test MAE (MW) | Test RMSE (MW) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `naive_baseline` | 213.12 | 263.11 | 7.85% | 194.90 | 245.01 |
| `seasonal_naive` | 167.32 | 205.94 | 6.23% | 174.34 | 216.70 |
| `ridge_regression` | 84.28 | 111.46 | 3.04% | 80.54 | 101.60 |
| **`random_forest` (Selected)** | **74.25** | **100.21** | **2.71%** | **69.77** | **93.51** |
| `hist_gradient_boosting` | 77.20 | 103.40 | 2.76% | 73.08 | 98.86 |

- **Selected Model**: `RandomForestRegressor` (100 trees, max depth 10, random_state 42).
- **Serialized Model Location**: `saved_models/energy_forecaster_v1.joblib` and `saved_models/energy_forecaster_v1_meta.json`.

---

## 6. Expanding Window Cross-Validation Backtest

To verify stability over rolling historical origins:
- **Folds Evaluated**: 3 expanding folds.
- **Mean Backtest MAE**: 77.71 MW
- **Mean Backtest RMSE**: 106.31 MW
- **Mean Backtest sMAPE**: 2.77%

---

## 7. Feature Importance Ranking

1. `demand_mw_lag_24h`: 67.3%
2. `hour_cos`: 10.4%
3. `demand_mw_rolling_std_6h`: 5.7%
4. `demand_mw_lag_48h`: 4.3%
5. `hour_sin`: 2.7%
6. `demand_mw_lag_1h`: 2.0%
7. `day_sin`: 1.8%
8. `demand_mw_lag_168h`: 0.8%

---

## 8. Forecast Uncertainty Quantification

Prediction bounds are calculated using validation set residual standard error $\sigma_{\text{residuals}}$:
$$\text{Margin}_{95} = 1.96 \cdot \sigma_{\text{residuals}} \approx \pm 99.5\,\text{MW}$$

$$\text{Lower Bound} = \max(0, \hat{y} - \text{Margin}_{95}), \quad \text{Upper Bound} = \hat{y} + \text{Margin}_{95}$$

---

## 9. Example Standardized Forecast Output

```json
{
  "region": "Grid_Alpha",
  "forecast_horizon": "24h",
  "predictions_count": 24,
  "peak_analysis": {
    "peak_demand_mw": 3412.5,
    "peak_timestamp": "2026-09-19T18:00:00+00:00",
    "min_demand_mw": 2480.1,
    "avg_demand_mw": 2895.4,
    "peak_to_avg_ratio": 1.18,
    "peak_severity": "ELEVATED"
  },
  "forecasts": [
    {
      "timestamp": "2026-09-19T15:00:00+00:00",
      "forecast_target_time": "2026-09-19T16:00:00+00:00",
      "region": "Grid_Alpha",
      "forecasted_demand_mw": 3120.45,
      "confidence_lower_mw": 3020.95,
      "confidence_upper_mw": 3219.95,
      "forecast_horizon": "24h",
      "model_version": "v1.0.0"
    }
  ]
}
```

---

## 10. Technical Interview Q&A Section

### Question: "Why is this ML forecasting approach better than simply predicting the average demand?"

> **Answer**:
> 1. **Captures Diurnal & Weekly Seasonality**: Energy demand follows non-linear dual-peak daily curves (morning & evening peaks) and weekly work vs. weekend variations. A simple mean forecast flattens these peaks, leading to severe under-prediction during peak demand hours (causing potential grid overload risks) and over-prediction during low demand night hours.
> 2. **Integrates Meteorological Non-Linearities**: Temperature swings directly drive heating and cooling degree loads. The ML model incorporates non-linear weather interactions alongside historical 24h/168h load lags.
> 3. **Quantitative Superiority**: In empirical benchmarks, Random Forest reduced the Mean Absolute Error from **213.12 MW** (Naive) and **167.32 MW** (Seasonal Naive) down to **74.25 MW** (a **65% error reduction** over naive baselines).
