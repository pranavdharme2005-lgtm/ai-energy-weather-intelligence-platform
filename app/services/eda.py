"""Exploratory Data Analysis (EDA) & Statistical Insight Engine."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ColumnStats(BaseModel):
    """Descriptive statistics breakdown for a single metric."""
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float


class CorrelationResult(BaseModel):
    """Pearson and Spearman rank correlation analysis."""
    feature: str
    pearson_corr: float
    spearman_corr: float
    sample_size: int
    disclaimer: str = "Correlation indicates statistical co-movement, not physical causation."


class LoadPeriodPeakInfo(BaseModel):
    """Peak and minimum load period insights."""
    peak_demand_mw: float
    peak_timestamp: Optional[str]
    peak_temperature_c: Optional[float]
    min_demand_mw: float
    min_timestamp: Optional[str]
    min_temperature_c: Optional[float]
    peak_hour_of_day: int
    min_hour_of_day: int


class EDASummary(BaseModel):
    """Consolidated EDA Report and Statistical Insights."""
    dataset_records: int
    demand_stats: Optional[ColumnStats] = None
    temperature_stats: Optional[ColumnStats] = None
    correlations: List[CorrelationResult] = Field(default_factory=list)
    load_periods: Optional[LoadPeriodPeakInfo] = None
    hourly_average_demand: Dict[int, float] = Field(default_factory=dict)
    daily_average_demand: Dict[int, float] = Field(default_factory=dict)
    insights_narrative: List[str] = Field(default_factory=list)


class EDAEngine:
    """Statistical evaluation engine calculating dataset metrics, correlations, and insights."""

    @staticmethod
    def calculate_column_stats(series: pd.Series) -> ColumnStats:
        """Calculates 11-point summary statistics for a numeric pandas Series."""
        clean_s = series.dropna()
        if clean_s.empty:
            return ColumnStats(count=0, mean=0.0, median=0.0, std=0.0, min=0.0, max=0.0, p25=0.0, p50=0.0, p75=0.0, p95=0.0, p99=0.0)

        return ColumnStats(
            count=len(clean_s),
            mean=round(float(clean_s.mean()), 2),
            median=round(float(clean_s.median()), 2),
            std=round(float(clean_s.std()), 2) if len(clean_s) > 1 else 0.0,
            min=round(float(clean_s.min()), 2),
            max=round(float(clean_s.max()), 2),
            p25=round(float(clean_s.quantile(0.25)), 2),
            p50=round(float(clean_s.quantile(0.50)), 2),
            p75=round(float(clean_s.quantile(0.75)), 2),
            p95=round(float(clean_s.quantile(0.95)), 2),
            p99=round(float(clean_s.quantile(0.99)), 2)
        )

    @classmethod
    def analyze_dataset(cls, merged_df: pd.DataFrame) -> EDASummary:
        """Executes full exploratory data analysis on time-aligned merged DataFrame."""
        if merged_df.empty or "demand_mw" not in merged_df.columns:
            logger.warning("Empty or invalid DataFrame passed to EDAEngine.")
            return EDASummary(dataset_records=0, insights_narrative=["No data available for EDA."])

        df = merged_df.copy()
        dt = pd.to_datetime(df["timestamp"]) if "timestamp" in df.columns else pd.Series(dtype="datetime64[ns]")

        # 1. Column Statistics
        demand_stats = cls.calculate_column_stats(df["demand_mw"])
        temp_stats = cls.calculate_column_stats(df["temperature_c"]) if "temperature_c" in df.columns else None

        # 2. Correlations
        correlations = []
        weather_features = ["temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms", "precipitation_mm"]
        for feat in weather_features:
            if feat in df.columns:
                valid_pair = df[["demand_mw", feat]].dropna()
                if len(valid_pair) > 2:
                    p_corr = valid_pair["demand_mw"].corr(valid_pair[feat], method="pearson")
                    s_corr = valid_pair["demand_mw"].corr(valid_pair[feat], method="spearman")
                    correlations.append(CorrelationResult(
                        feature=feat,
                        pearson_corr=round(float(p_corr), 4) if not np.isnan(p_corr) else 0.0,
                        spearman_corr=round(float(s_corr), 4) if not np.isnan(s_corr) else 0.0,
                        sample_size=len(valid_pair)
                    ))

        # 3. Peak and Min Period Load Analysis
        max_idx = df["demand_mw"].idxmax()
        min_idx = df["demand_mw"].idxmin()

        peak_row = df.loc[max_idx]
        min_row = df.loc[min_idx]

        hourly_avg = {}
        daily_avg = {}
        if not dt.empty:
            df["_hour"] = dt.dt.hour
            df["_dow"] = dt.dt.dayofweek
            hourly_avg = {int(h): round(float(m), 2) for h, m in df.groupby("_hour")["demand_mw"].mean().items()}
            daily_avg = {int(d): round(float(m), 2) for d, m in df.groupby("_dow")["demand_mw"].mean().items()}

        peak_hour = max(hourly_avg, key=hourly_avg.get) if hourly_avg else 14
        min_hour = min(hourly_avg, key=hourly_avg.get) if hourly_avg else 4

        load_periods = LoadPeriodPeakInfo(
            peak_demand_mw=round(float(peak_row["demand_mw"]), 2),
            peak_timestamp=str(peak_row.get("timestamp")),
            peak_temperature_c=round(float(peak_row["temperature_c"]), 2) if "temperature_c" in peak_row else None,
            min_demand_mw=round(float(min_row["demand_mw"]), 2),
            min_timestamp=str(min_row.get("timestamp")),
            min_temperature_c=round(float(min_row["temperature_c"]), 2) if "temperature_c" in min_row else None,
            peak_hour_of_day=peak_hour,
            min_hour_of_day=min_hour
        )

        # 4. Structured Insights Narrative
        insights = [
            f"Evaluated {len(df)} time-aligned records.",
            f"Grid load averaged {demand_stats.mean} MW (range: {demand_stats.min} MW to {demand_stats.max} MW).",
            f"Peak demand recorded at {load_periods.peak_timestamp} ({load_periods.peak_demand_mw} MW).",
            f"Diurnal load peaks around hour {peak_hour:02d}:00 and drops to minimum around hour {min_hour:02d}:00."
        ]

        if correlations:
            t_corr = next((c for c in correlations if c.feature == "temperature_c"), None)
            if t_corr:
                insights.append(f"Temperature vs Demand correlation: Pearson r = {t_corr.pearson_corr:.2f} (Note: correlation != causation).")

        return EDASummary(
            dataset_records=len(df),
            demand_stats=demand_stats,
            temperature_stats=temp_stats,
            correlations=correlations,
            load_periods=load_periods,
            hourly_average_demand=hourly_avg,
            daily_average_demand=daily_avg,
            insights_narrative=insights
        )
