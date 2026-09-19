# Data Quality, Cleaning Rules & Feature Engineering Specification

## 1. Data Quality Engine Methodology

The platform implements a transparent, weighted Data Quality Scoring model. Every DataFrame evaluated by `DataQualityEngine` produces four sub-scores ($0.0 \dots 100.0\%$) and an overall composite score.

### Quality Score Mathematical Formula
$$\text{Quality Score} = 100 \times \left(0.35 \times S_{\text{comp}} + 0.30 \times S_{\text{val}} + 0.20 \times S_{\text{uniq}} + 0.15 \times S_{\text{cont}}\right)$$

Where:
- **Completeness ($S_{\text{comp}}$)**: Percentage of non-missing data cells across all attributes ($100 - \% \text{ missing}$).
- **Validity ($S_{\text{val}}$)**: Percentage of values adhering to physical & domain bound limits.
- **Uniqueness ($S_{\text{uniq}}$)**: Percentage of distinct records based on primary logical keys ($100 - \% \text{ duplicates}$).
- **Continuity ($S_{\text{cont}}$)**: Percentage of expected time-series intervals present without sequence gaps ($100 - \% \text{ gaps}$).

---

## 2. Column-by-Column Missing Value Imputation Strategy

| Column | Data Type | Imputation Strategy | Technical Rationale |
| :--- | :--- | :--- | :--- |
| `temperature_c` | Float | Linear Time Interpolation ($<3h$) / Rolling Median | Temperature changes smoothly across hourly windows; linear interpolation preserves diurnal thermal inertia. |
| `humidity_pct` | Float | Linear Time Interpolation ($<3h$) / Rolling Median | Bounded $[0, 100\%]$ relative humidity; short gaps are linearly continuous. |
| `pressure_hpa` | Float | Linear Time Interpolation | Atmospheric barometric pressure fluctuates slowly over synoptic scales. |
| `wind_speed_ms` | Float | Linear Time Interpolation ($<3h$) / Rolling Median | Non-negative anemometer measurements. |
| `precipitation_mm` | Float | **Fill with `0.0`** | **Event-based sparsity**: Interpolating precipitation would invent false rain events during dry spells. |
| `weather_condition` | String | Categorical Mode / Forward Fill | Meteorological conditions persist over multi-hour synoptic blocks. |
| `demand_mw` | Float | Time Linear / Diurnal Hourly Median | Grid power load follows strong 24-hour diurnal consumer cycles. |

---

## 3. Duplicate Prevention & Key Strategy

Duplicate records are detected using composite logical keys:
- **Weather Telemetry**: `location + timestamp + source`
- **Energy Load Telemetry**: `region + timestamp + source`

Database level uniqueness is enforced via SQL `UniqueConstraint` on ORM models with `ON CONFLICT` skip/update repository semantics.

---

## 4. Outlier Detection & Classification Policy

Outliers are evaluated using rolling Z-scores ($\pm 3.0\sigma$) and Interquartile Range ($Q1 - 1.5\times IQR, Q3 + 1.5\times IQR$).

> [!IMPORTANT]
> **Outlier Policy**: Outliers are **NEVER deleted blindly**. An unusual value may represent a real grid event (e.g. heatwave demand surge). Outliers are classified into three categories:

1. **`VALID_EXTREME`**: Extreme values within physical bounds (e.g. 42°C heatwave or peak industrial grid load). Retained for model training.
2. **`SUSPICIOUS`**: Borderline statistical deviations ($3.0 < |Z| \le 4.5$). Flagged for inspection.
3. **`INVALID`**: Physically impossible readings (e.g. $-100^\circ\text{C}$ temperature or negative demand). Imputed or dropped.

---

## 5. Timestamp Strategy & Gap Detection

- **Timezone Standard**: ISO-8601 UTC (`datetime.now(timezone.utc)` / `DateTime(timezone=True)`).
- **Gap Detection Algorithm**: Inferred median sampling step ($\Delta t$). Intervals exceeding $1.5 \times \Delta t$ are flagged as sequence gaps in `QualityReport`.

---

## 6. Categorical Normalization Rules

Raw weather strings are mapped to standard title-case categories:
- `"clear sky"`, `"CLEAR"`, `"sunny"` $\rightarrow$ `"Clear"`
- `"scattered clouds"`, `"partly cloudy"` $\rightarrow$ `"Partly cloudy"`
- `"cloudy"`, `"overcast"` $\rightarrow$ `"Overcast"`
- `"drizzle"`, `"light rain"` $\rightarrow$ `"Slight rain"`

---

## 7. Machine Learning Feature Suitability Matrix

| Feature Name | Type | Leakage Risk | Downstream ML Suitability |
| :--- | :--- | :--- | :--- |
| `hour_sin`, `hour_cos` | Cyclical Float | **Zero (Known prior)** | Energy Forecasting, Rain Prediction |
| `month_sin`, `month_cos` | Cyclical Float | **Zero (Known prior)** | Energy Forecasting, Seasonal Anomaly |
| `season` | Categorical Int | **Zero (Known prior)** | Seasonal Load Baseline |
| `demand_lag_1h` | Float | **Zero (Shifted $t-1$)** | Short-Term Demand Forecasting |
| `demand_lag_24h` | Float | **Zero (Shifted $t-24$)** | Day-Ahead Demand Forecasting |
| `demand_rolling_mean_6h` | Float | **Zero (Closed left window)** | Grid Load Trend Baseline |
| `temperature_c` | Float | **Zero** | Weather-Energy Impact & Rain Classifier |
