# Stage 8 — What-If Energy Scenario Simulator Documentation

## 1. Purpose

The **What-If Energy Scenario Simulator** enables grid operators, energy analysts, and power planners to simulate hypothetical meteorological conditions (e.g. extreme heatwaves, sudden cold snaps, heavy rainstorms, humid summer surges) and observe model-based energy demand shifts against baseline forecasts.

Key principles of the simulator:
- **Zero Model Retraining**: Uses the serialized Stage 5 machine-learning forecaster (`saved_models/energy_forecaster_v1.joblib`) for zero-latency inference without retraining.
- **Controlled Prediction Comparison**: Modifies only supplied weather features while keeping all other inputs (demand lags, rolling statistics, calendar encodings) identical to the baseline.
- **Multi-Horizon Trajectory**: Generates 24-hour sequence of baseline vs. scenario forecasts ($MW$), absolute differences ($\Delta MW$), and percentage changes ($\Delta \%$).
- **Historical Range Check**: Benchmarks scenario inputs against historical training feature distributions to flag out-of-distribution scenarios.
- **Non-Causal Labeling**: Explicitly frames results as **"Model-Based Scenario Estimates"** and **"Model Sensitivity Analysis"**. Avoids asserting causal proof.

---

## 2. Architecture & Data Flow

```
+---------------------------------------------------------------------------------+
|                         WHAT-IF SIMULATION DATA FLOW                            |
+---------------------------------------------------------------------------------+
| 1. Historical Dataset ---> Baseline Input Features (X_base)                     |
| 2. User Scenario Overrides ---> Input Validator & Sanitizer                     |
| 3. Sanitized Overrides ---> Range Checker (Flags Out-of-Distribution Inputs)    |
| 4. X_base + Overrides ---> Scenario Input Features (X_scen)                     |
| 5. X_base & X_scen ---> Stage 5 ML Forecaster (Joblib Artifact)                 |
| 6. Predictions ---> Trajectory Comparison + 95% Confidence Intervals            |
| 7. Results ---> Deterministic Explanation Generator + DB Storage + Charts       |
+---------------------------------------------------------------------------------+
```

---

## 3. Baseline Scenario Generation

The baseline scenario represents the current expected grid load forecast based on actual recent data:

- **Data Source**: Recent time-aligned historical observations (`load_merged_dataset` or SQLite/PostgreSQL `energy_data` / `weather_data` tables).
- **Feature Extraction**: Historical demand lags ($t-1h, t-2h, \dots, t-168h$), past-only rolling means/stds, calendar encodings (`hour_sin`, `day_sin`, `is_weekend`), and observed weather variables.
- **Inference Pipeline**: Executed through Stage 5 `EnergyForecaster` (`predict_horizon()`), yielding 24 hourly baseline points ($MW_{\text{base}}$).

---

## 4. Supported Scenario Variables & Input Validation

The simulator supports modifying only those weather features that are accepted by the Stage 5 forecasting pipeline:

| Variable | Unit | Type | Valid Physical Bounds | Description |
| :--- | :--- | :--- | :--- | :--- |
| `temperature_c` | $^\circ\text{C}$ | Float | $[-30.0, +55.0]^\circ\text{C}$ | Ambient air temperature. |
| `humidity_pct` | $\%$ | Float | $[0.0, 100.0]\%$ | Relative humidity. |
| `pressure_hpa` | $hPa$ | Float | $[850.0, 1080.0]\,hPa$ | Atmospheric barometric pressure. |
| `wind_speed_ms` | $m/s$ | Float | $[0.0, 75.0]\,m/s$ | Wind velocity. |
| `cloud_cover_pct` | $\%$ | Float | $[0.0, 100.0]\%$ | Sky cover percentage. |
| `precipitation_mm` | $mm$ | Float | $[0.0, 200.0]\,mm$ | Rainfall depth. |
| `rain_probability` | Scale | Float | $[0.0, 1.0]$ | Stage 4 ML rain prediction probability (auto-scaled if entered as $0-100\%$). |

### Validation Engine (`validate_scenario_inputs()`)
- Checks data types (coerces numeric values, rejects invalid text).
- Enforces physical bounds (e.g. temperature above $55^\circ\text{C}$ or below $-30^\circ\text{C}$ is rejected with a clear error message).
- Filters out unsupported variables gracefully with warning messages.

---

## 5. Controlled Scenario Forecast Calculation

To isolate the model's response to scenario changes:

1. **Unchanged Input Preservation**: Unmodified weather features, historical demand lags ($t-1h \dots t-168h$), rolling statistics, and calendar encodings remain **100% identical** to baseline inputs.
2. **Dual-Model Inference**: Both baseline and scenario feature matrices are evaluated through the **exact same serialized model artifact**.
3. **Delta Calculations**:
   - **Absolute Difference ($MW$)**: $\Delta MW_h = MW_{\text{scenario}, h} - MW_{\text{baseline}, h}$
   - **Percentage Change ($\%$)**: $\Delta \%_h = \frac{\Delta MW_h}{MW_{\text{baseline}, h}} \times 100\%$

> [!NOTE]
> Near-zero or zero baseline demand values are handled safely ($\Delta \% = 0.0\%$) to prevent division-by-zero crashes.

---

## 6. One-Variable Model Sensitivity Analysis

The simulator provides single-variable parameter sweeps (`run_one_variable_sensitivity()`):

- **Mechanism**: Sweeps a single selected feature (e.g., `temperature_c` from $10^\circ\text{C}$ to $40^\circ\text{C}$ in 10 steps) while keeping all other model inputs constant.
- **Output**: Generates a 10-point sensitivity curve mapping input value vs. predicted grid load ($MW$).
- **Disclaimers**: Explicitly labeled:
  > *"Model Sensitivity Analysis. Demonstrates how model predictions vary with input changes; does NOT prove physical causation."*

---

## 7. Historical Training-Range Validation

To prevent users from over-interpreting extreme or impossible scenarios, the module benchmarks input values against historical training feature distributions:

- **Status Classifications**:
  - `WITHIN_TRAINING_RANGE`: Value lies between historical minimum and maximum.
  - `NEAR_HISTORICAL_BOUNDARY`: Value lies outside 5th – 95th percentile bounds.
  - `OUTSIDE_TRAINING_RANGE`: Value exceeds historical absolute minimum or maximum.

- **Warning Propagation**: If any feature is outside training bounds, `out_of_range_warning` is set to `True` with the warning message:
  > *"Scenario input is outside historical training feature range. Model forecast uncertainty may be higher for extreme inputs."*

---

## 8. Uncertainty & Prediction Interval Propagation

- **Uncertainty Propagation**: Stage 5 residual 95% confidence intervals ($\pm 1.96 \cdot \sigma_{\text{residuals}}$) are propagated for both baseline and scenario trajectories:
  - $\text{Lower Bound} = \max(0.0, MW_{\text{scenario}} - \text{Margin}_{95})$
  - $\text{Upper Bound} = MW_{\text{scenario}} + \text{Margin}_{95}$
- **Flag**: `uncertainty_available = True`.

---

## 9. Preset Scenario Templates

Derived from project dataset quantiles:

1. **Hot Heatwave Day**: Temperature $= 35.0^\circ\text{C}$, Humidity $= 65\%$, Rain Prob $= 0.10$.
2. **Cold Snap Day**: Temperature $= 2.0^\circ\text{C}$, Humidity $= 80\%$, Rain Prob $= 0.25$.
3. **Heavy Rainstorm**: Temperature $= 18.0^\circ\text{C}$, Humidity $= 90\%$, Precip $= 12.5\text{ mm}$, Rain Prob $= 0.95$.
4. **High Humidity Summer**: Temperature $= 30.0^\circ\text{C}$, Humidity $= 88\%$, Precip $= 2.0\text{ mm}$, Rain Prob $= 0.45$.

---

## 10. Database Schema (`scenario_runs`)

Executed scenario runs are persisted in PostgreSQL / SQLite:

- Table: `scenario_runs`
- Columns: `id`, `scenario_id`, `region`, `baseline_demand_mw`, `scenario_demand_mw`, `absolute_change_mw`, `percentage_change`, `baseline_inputs_json`, `scenario_inputs_json`, `out_of_range_warning`, `model_version`, `created_at`.

---

## 11. Visualizations

The module generates 6 Matplotlib figures in `docs/images/stage8/`:
1. `01_baseline_vs_scenario_trajectory.png`: 24h demand curve comparison line chart.
2. `02_forecast_difference.png`: Hourly demand delta bar chart ($\Delta MW$).
3. `03_one_variable_sensitivity.png`: Parameter sweep curve.
4. `04_scenario_input_comparison.png`: Baseline vs scenario input feature comparison.
5. `05_prediction_interval_comparison.png`: 95% residual confidence bounds shaded chart.
6. `06_training_range_warning.png`: Range status check indicator chart.

---

## 12. Interview-Friendly Q&A

### Question:
*"How does your What-If Simulator work?"*

### Professional Response:

> "Our What-If Energy Scenario Simulator provides a controlled environment for testing how hypothetical weather changes impact predicted grid energy demand.
> 
> The core design principle is **zero model retraining** and **controlled comparison**. We reuse the exact serialized Random Forest Regressor trained in Stage 5.
> 
> When an analyst modifies input variables—such as raising temperature from $28^\circ\text{C}$ to $35^\circ\text{C}$—the simulator creates a controlled scenario feature matrix. It updates only the specified weather variables while holding all historical demand lags, rolling statistics, and calendar features 100% identical to the baseline.
> 
> Both baseline and scenario feature matrices are fed through the same inference pipeline to compute a 24-hour hourly trajectory comparison, absolute megawatt shifts, and percentage changes.
> 
> To prevent misleading over-interpretation of extreme scenarios, the simulator benchmarks input values against historical training feature distributions and flags any out-of-distribution inputs with uncertainty warnings. All outputs are explicitly labeled as model-based scenario estimates, avoiding unsubstantiated causal claims."

---

## 13. Verification Results

- All 68 automated unit & integration tests pass cleanly (`py run.py test`).
- CLI runner `py run.py simulate` executed with zero errors and generated all 6 Matplotlib figures.
