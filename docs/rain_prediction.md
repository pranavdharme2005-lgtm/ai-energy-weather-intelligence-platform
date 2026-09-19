# Rain Prediction Machine Learning Module Specification

## 1. Problem Definition & Objective

Precipitation events significantly impact both electrical grid loads (cooling/heating demand variations) and renewable energy generation (solar panel cloud shading). The objective of the Rain Prediction Machine Learning Module is to construct an explainable, time-aware binary classification model estimating short-term rain probability ($P(\text{Rain}) \in [0.0, 1.0]$) for the upcoming 3-hour window ($t+3h$).

---

## 2. Target Definition & Justification

$$\text{Target}_{\text{Rain Next 3h}} = \begin{cases} 1 & \text{if } \max_{i \in [1, 3]} (\text{precipitation}_{t+i}) \ge 0.1 \text{ mm} \\ 0 & \text{otherwise} \end{cases}$$

- **Threshold Justification**: $0.1\text{ mm}$ is the standard international meteorological threshold defined by the World Meteorological Organization (WMO) to distinguish measurable liquid precipitation from unmeasurable trace atmospheric moisture.

---

## 3. Predictor Features & Target Leakage Prevention

To ensure real-world operational validity and prevent target leakage, **all predictor features are strictly backward-looking or deterministic known priors**.

| Feature Name | Feature Type | Time Horizon | Leakage Shielding |
| :--- | :--- | :--- | :--- |
| `temperature_c` | Continuous Float | Observation Time $t$ | Current ambient temperature |
| `humidity_pct` | Continuous Float | Observation Time $t$ | Current relative humidity |
| `pressure_hpa` | Continuous Float | Observation Time $t$ | Current barometric surface pressure |
| `wind_speed_ms` | Continuous Float | Observation Time $t$ | Current surface wind speed |
| `cloud_cover_pct` | Bounded Float $[0, 100]$ | Observation Time $t$ | Current cloud density ratio |
| `precipitation_mm_lag_1h` | Continuous Float | Past Observation $t-1h$ | **Shifted $t-1h$ (Prevents future leak)** |
| `hour_sin`, `hour_cos` | Cyclical Float | Prior Calendar | Deterministic diurnal cycle |
| `month_sin`, `month_cos` | Cyclical Float | Prior Calendar | Deterministic seasonal cycle |
| `season` | Categorical Int | Prior Calendar | Season mapping ($1\dots4$) |

> [!WARNING]
> **Strict Leakage Rule**: Future precipitation values ($t+1h \dots t+3h$) are used **EXCLUSIVELY** to construct the supervised target vector $\mathbf{y}$ during training and are **NEVER** present in feature matrix $\mathbf{X}$.

---

## 4. Chronological Split Strategy

Because meteorological observation telemetries represent correlated time-series sequences:
- **Random K-Fold Cross-Validation is STRICTLY PROHIBITED** (to eliminate look-ahead data contamination).
- **Chronological Time-Aware Split**:
  - **Training Set (70%)**: Earliest chronological timeline.
  - **Validation Set (15%)**: Intermediate chronological sequence (used for threshold tuning $\tau$).
  - **Test Set (15%)**: Most recent chronological timeline (held-out final evaluation).

---

## 5. Candidate Models & Performance Metrics

Evaluating candidate classification algorithms against baseline heuristics:

| Model Candidate | Algorithm | Class Imbalance Strategy | Primary Strengths |
| :--- | :--- | :--- | :--- |
| **Baseline 1** | Majority Class Classifier | None | Benchmark lower bound ($F_1 = 0.0$) |
| **Baseline 2** | Logistic Regression | `class_weight='balanced'` | Linear baseline, fast inference |
| **Candidate 1 (Selected)** | **Random Forest Classifier** | `class_weight='balanced'` | Non-linear tree ensemble, handles feature interactions, interpretable Gini importances |
| **Candidate 2** | HistGradientBoosting | `class_weight='balanced'` | Gradient boosted trees |

### Metric Definitions
- **Accuracy**: Overall proportion of correct classifications $\frac{TP+TN}{TP+TN+FP+FN}$.
- **Precision**: Proportion of predicted rain alerts that were actual rain events $\frac{TP}{TP+FP}$.
- **Recall**: Proportion of actual rain events correctly detected by the model $\frac{TP}{TP+FN}$.
- **$F_1$-Score**: Harmonic mean of Precision and Recall $\frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$.
- **ROC-AUC**: Area under the Receiver Operating Characteristic curve ($P(\text{Rain})$ ranking quality).

---

## 6. Decision Threshold Optimization ($\tau$)

Rather than defaulting blindly to $\tau = 0.50$, the optimal decision threshold $\tau^*$ is searched across $[0.10, 0.90]$ on validation set probabilities to maximize $F_1$-score:

$$\tau^* = \arg\max_{\tau \in [0.1, 0.9]} F_1\left(\mathbf{y}_{\text{val}}, \mathbb{I}(\mathbf{P}_{\text{val}} \ge \tau)\right)$$

*Operational Note:* In grid analytics, a lower threshold ($\tau \approx 0.35 \dots 0.40$) is preferred when the cost of an unpredicted rain event (unanticipated PV generation drop) exceeds the cost of a false alarm.

---

## 7. Feature Importance Ranking

1. **Relative Humidity (`humidity_pct`)**: Strongest single predictor of near-term saturation.
2. **Cloud Cover (`cloud_cover_pct`)**: Direct indicator of atmospheric condensation density.
3. **Barometric Pressure (`pressure_hpa`)**: Falling pressure indicates approaching cyclonic weather fronts.
4. **Historical Precipitation Lag (`precipitation_mm_lag_1h`)**: Persistence indicator.
5. **Ambient Temperature (`temperature_c`)**: Thermal dew point proximity.

---

## 8. Model Artifact Serialization & Metadata

Model artifacts are serialized for reproducible deployment:
- **Model Binary**: `saved_models/rain_predictor_v1.joblib`
- **Metadata JSON**: `saved_models/rain_predictor_v1_meta.json`

### Sample Prediction Inference Output (`RainPredictionResult`):
```json
{
  "timestamp": "2026-09-19T14:00:00Z",
  "prediction_target_time": "2026-09-19T17:00:00Z",
  "rain_predicted": true,
  "probability": 0.7842,
  "model_version": "v1.0.0"
}
```

---

## 9. Honest Operational Limitations

- **Micro-Climate Variability**: Regional topography (coastal/mountainous terrain) can introduce local precipitation micro-climates not captured by single-station surface telemetry.
- **Extreme Unseen Events**: Models trained during dry seasons require periodic retraining (Concept Drift mitigation) prior to monsoon transitions.
- **Probabilistic Nature**: Probability $P(\text{Rain}) = 0.78$ represents calibrated model confidence, not a deterministic guarantee.
