"""Comprehensive Data Quality Engine for Energy & Weather Telemetries."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SubScoreBreakdown(BaseModel):
    """Component scores contributing to overall Data Quality Score."""
    completeness_score: float = Field(..., ge=0.0, le=100.0)
    validity_score: float = Field(..., ge=0.0, le=100.0)
    uniqueness_score: float = Field(..., ge=0.0, le=100.0)
    continuity_score: float = Field(..., ge=0.0, le=100.0)
    overall_quality_score: float = Field(..., ge=0.0, le=100.0)


class ComprehensiveQualityReport(BaseModel):
    """Detailed Data Quality Assessment Summary Report."""
    dataset_name: str
    total_records: int
    missing_cells: int
    missing_cell_pct: float
    duplicate_records: int
    duplicate_record_pct: float
    invalid_value_count: int
    outlier_count: int
    timestamp_gaps_count: int
    expected_frequency: str
    scores: SubScoreBreakdown
    issues_summary: List[str] = Field(default_factory=list)


class DataQualityEngine:
    """Evaluates time-series dataframes for completeness, validity, uniqueness, continuity, and outliers."""

    WEATHER_BOUNDS = {
        "temperature_c": (-50.0, 65.0),
        "humidity_pct": (0.0, 100.0),
        "pressure_hpa": (800.0, 1100.0),
        "wind_speed_ms": (0.0, 120.0),
        "cloud_cover_pct": (0.0, 100.0),
        "precipitation_mm": (0.0, 500.0)
    }

    ENERGY_BOUNDS = {
        "demand_mw": (0.0, 50000.0)
    }

    @classmethod
    def evaluate_weather_dataframe(
        cls, df: pd.DataFrame, key_cols: List[str] = None
    ) -> ComprehensiveQualityReport:
        """Evaluates weather DataFrame against quality, bound, and continuity metrics."""
        key_cols = key_cols or ["location", "timestamp", "source"]
        return cls._evaluate_dataframe(df, dataset_name="Weather", bounds=cls.WEATHER_BOUNDS, key_cols=key_cols)

    @classmethod
    def evaluate_energy_dataframe(
        cls, df: pd.DataFrame, key_cols: List[str] = None
    ) -> ComprehensiveQualityReport:
        """Evaluates energy demand DataFrame against quality, bound, and continuity metrics."""
        key_cols = key_cols or ["region", "timestamp", "source"]
        return cls._evaluate_dataframe(df, dataset_name="Energy", bounds=cls.ENERGY_BOUNDS, key_cols=key_cols)

    @classmethod
    def _evaluate_dataframe(
        cls, df: pd.DataFrame, dataset_name: str, bounds: Dict[str, Tuple[float, float]], key_cols: List[str]
    ) -> ComprehensiveQualityReport:
        """Core evaluation algorithm calculating transparent component scores and overall quality score."""
        issues = []
        if df.empty:
            return ComprehensiveQualityReport(
                dataset_name=dataset_name,
                total_records=0,
                missing_cells=0,
                missing_cell_pct=0.0,
                duplicate_records=0,
                duplicate_record_pct=0.0,
                invalid_value_count=0,
                outlier_count=0,
                timestamp_gaps_count=0,
                expected_frequency="None",
                scores=SubScoreBreakdown(
                    completeness_score=0.0, validity_score=0.0, uniqueness_score=0.0,
                    continuity_score=0.0, overall_quality_score=0.0
                ),
                issues_summary=["DataFrame is empty."]
            )

        total_records = len(df)
        total_cells = df.size
        missing_cells = int(df.isnull().sum().sum())
        missing_cell_pct = round((missing_cells / (total_cells + 1e-6)) * 100.0, 2)

        # Uniqueness Check
        check_keys = [k for k in key_cols if k in df.columns]
        if check_keys:
            duplicate_records = int(df.duplicated(subset=check_keys).sum())
        else:
            duplicate_records = int(df.duplicated().sum())

        duplicate_record_pct = round((duplicate_records / (total_records + 1e-6)) * 100.0, 2)

        # Validity Check
        invalid_value_count = 0
        for col, (min_val, max_val) in bounds.items():
            if col in df.columns:
                out_cnt = int(((df[col] < min_val) | (df[col] > max_val)).sum())
                if out_cnt > 0:
                    invalid_value_count += out_cnt
                    issues.append(f"Column '{col}': {out_cnt} values outside physical bounds [{min_val}, {max_val}].")

        # Outlier Detection (Z-score > 3.0 or IQR)
        outlier_count = 0
        for col in bounds.keys():
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                series = df[col].dropna()
                if len(series) > 3:
                    q1 = series.quantile(0.25)
                    q3 = series.quantile(0.75)
                    iqr = q3 - q1
                    outliers = ((series < (q1 - 1.5 * iqr)) | (series > (q3 + 1.5 * iqr))).sum()
                    outlier_count += int(outliers)

        # Timestamp Continuity & Gap Detection
        timestamp_gaps_count = 0
        freq_str = "1h"
        if "timestamp" in df.columns:
            ts_series = pd.to_datetime(df["timestamp"]).sort_values()
            diffs = ts_series.diff().dropna()
            if not diffs.empty:
                median_diff = diffs.median()
                freq_str = str(median_diff)
                # Count gaps where interval > 1.5x expected step
                gaps = (diffs > median_diff * 1.5).sum()
                timestamp_gaps_count = int(gaps)
                if timestamp_gaps_count > 0:
                    issues.append(f"Found {timestamp_gaps_count} time-series gaps exceeding expected interval ({freq_str}).")

        if missing_cells > 0:
            issues.append(f"Total missing values: {missing_cells} cells ({missing_cell_pct}%).")
        if duplicate_records > 0:
            issues.append(f"Total duplicate records: {duplicate_records} ({duplicate_record_pct}%).")

        # Transparent Component Score Calculations
        completeness_score = max(100.0 - missing_cell_pct, 0.0)
        uniqueness_score = max(100.0 - duplicate_record_pct, 0.0)
        validity_score = max(100.0 - (invalid_value_count / (total_cells + 1e-6)) * 100.0, 0.0)
        continuity_score = max(100.0 - (timestamp_gaps_count / (total_records + 1e-6)) * 100.0, 0.0)

        # Formula: 35% Completeness + 30% Validity + 20% Uniqueness + 15% Continuity
        overall_score = round(
            0.35 * completeness_score +
            0.30 * validity_score +
            0.20 * uniqueness_score +
            0.15 * continuity_score,
            2
        )

        scores = SubScoreBreakdown(
            completeness_score=round(completeness_score, 2),
            validity_score=round(validity_score, 2),
            uniqueness_score=round(uniqueness_score, 2),
            continuity_score=round(continuity_score, 2),
            overall_quality_score=overall_score
        )

        logger.info(f"Data Quality Engine calculated overall score for {dataset_name}: {overall_score}%")

        return ComprehensiveQualityReport(
            dataset_name=dataset_name,
            total_records=total_records,
            missing_cells=missing_cells,
            missing_cell_pct=missing_cell_pct,
            duplicate_records=duplicate_records,
            duplicate_record_pct=duplicate_record_pct,
            invalid_value_count=invalid_value_count,
            outlier_count=outlier_count,
            timestamp_gaps_count=timestamp_gaps_count,
            expected_frequency=freq_str,
            scores=scores,
            issues_summary=issues
        )
