"""Data Quality Validation Engine for Stage 2 Ingestion Pipelines."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataQualityReport(BaseModel):
    """Data quality assessment summary report schema."""
    total_records: int
    valid_count: int = 0
    invalid_count: int = 0
    missing_count: int = 0
    duplicate_count: int = 0
    out_of_range_count: int = 0
    passed_validation: bool = True
    issues: List[str] = Field(default_factory=list)


class DataValidator:
    """Validates weather and energy telemetry records for physical bounds, UTC timestamps, and completeness."""

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
    def validate_weather_data(cls, df: pd.DataFrame) -> DataQualityReport:
        """Validates weather dataframe against schemas and physical bounds (Stage 1 compatibility)."""
        issues = []
        if df.empty:
            return DataQualityReport(
                total_records=0, valid_count=0, invalid_count=0, missing_count=0, duplicate_count=0,
                out_of_range_count=0, passed_validation=False, issues=["DataFrame is empty."]
            )

        total_records = len(df)
        missing_count = int(df.isnull().sum().sum())
        duplicate_count = int(df.duplicated(subset=["timestamp", "location"]).sum())
        out_of_range_count = 0

        for col, (min_val, max_val) in cls.WEATHER_BOUNDS.items():
            if col in df.columns:
                out_bounds = ((df[col] < min_val) | (df[col] > max_val)).sum()
                if out_bounds > 0:
                    out_of_range_count += int(out_bounds)
                    issues.append(f"Column '{col}' has {out_bounds} values outside range [{min_val}, {max_val}].")

        if missing_count > 0:
            issues.append(f"Found {missing_count} total null values.")
        if duplicate_count > 0:
            issues.append(f"Found {duplicate_count} duplicate timestamp records.")

        passed = len(issues) == 0

        return DataQualityReport(
            total_records=total_records,
            valid_count=total_records if passed else 0,
            invalid_count=0 if passed else total_records,
            missing_count=missing_count,
            duplicate_count=duplicate_count,
            out_of_range_count=out_of_range_count,
            passed_validation=passed,
            issues=issues
        )

    @classmethod
    def validate_energy_data(cls, df: pd.DataFrame) -> DataQualityReport:
        """Validates energy load dataframe against schemas and domain bounds (Stage 1 compatibility)."""
        issues = []
        if df.empty:
            return DataQualityReport(
                total_records=0, valid_count=0, invalid_count=0, missing_count=0, duplicate_count=0,
                out_of_range_count=0, passed_validation=False, issues=["DataFrame is empty."]
            )

        total_records = len(df)
        missing_count = int(df.isnull().sum().sum())
        duplicate_count = int(df.duplicated(subset=["timestamp", "region"]).sum())
        out_of_range_count = 0

        for col, (min_val, max_val) in cls.ENERGY_BOUNDS.items():
            if col in df.columns:
                out_bounds = ((df[col] < min_val) | (df[col] > max_val)).sum()
                if out_bounds > 0:
                    out_of_range_count += int(out_bounds)
                    issues.append(f"Column '{col}' has {out_bounds} values outside range [{min_val}, {max_val}].")

        if missing_count > 0:
            issues.append(f"Found {missing_count} total null values.")
        if duplicate_count > 0:
            issues.append(f"Found {duplicate_count} duplicate timestamp records.")

        passed = len(issues) == 0

        return DataQualityReport(
            total_records=total_records,
            valid_count=total_records if passed else 0,
            invalid_count=0 if passed else total_records,
            missing_count=missing_count,
            duplicate_count=duplicate_count,
            out_of_range_count=out_of_range_count,
            passed_validation=passed,
            issues=issues
        )

    @classmethod
    def validate_weather_record(cls, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates a single weather record dictionary against domain bounds."""
        issues = []

        for req in ["timestamp", "location", "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms"]:
            if req not in record or record[req] is None:
                issues.append(f"Missing required field '{req}'.")

        if issues:
            return False, issues

        ts = record["timestamp"]
        if not isinstance(ts, (datetime, pd.Timestamp)):
            issues.append(f"Invalid timestamp type: {type(ts)}.")

        temp = record["temperature_c"]
        if not isinstance(temp, (int, float)) or not (-50.0 <= temp <= 65.0):
            issues.append(f"Temperature {temp}°C outside physical bounds [-50, 65].")

        humidity = record["humidity_pct"]
        if not isinstance(humidity, (int, float)) or not (0.0 <= humidity <= 100.0):
            issues.append(f"Humidity {humidity}% outside bounds [0, 100].")

        pressure = record["pressure_hpa"]
        if not isinstance(pressure, (int, float)) or not (800.0 <= pressure <= 1100.0):
            issues.append(f"Pressure {pressure}hPa outside bounds [800, 1100].")

        wind = record["wind_speed_ms"]
        if not isinstance(wind, (int, float)) or wind < 0.0:
            issues.append(f"Wind speed {wind}m/s cannot be negative.")

        precip = record.get("precipitation_mm", 0.0)
        if isinstance(precip, (int, float)) and precip < 0.0:
            issues.append(f"Precipitation {precip}mm cannot be negative.")

        is_valid = len(issues) == 0
        return is_valid, issues

    @classmethod
    def validate_energy_record(cls, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates a single energy record dictionary against physical bounds."""
        issues = []

        for req in ["timestamp", "region", "demand_mw"]:
            if req not in record or record[req] is None:
                issues.append(f"Missing required field '{req}'.")

        if issues:
            return False, issues

        ts = record["timestamp"]
        if not isinstance(ts, (datetime, pd.Timestamp)):
            issues.append(f"Invalid timestamp type: {type(ts)}.")

        demand = record["demand_mw"]
        if not isinstance(demand, (int, float)) or demand < 0.0:
            issues.append(f"Energy demand {demand} MW cannot be negative.")

        is_valid = len(issues) == 0
        return is_valid, issues

    @classmethod
    def validate_weather_batch(cls, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], DataQualityReport]:
        """Validates a list of weather records, returning valid records and DataQualityReport."""
        valid_records = []
        all_issues = []

        for idx, rec in enumerate(records):
            is_valid, issues = cls.validate_weather_record(rec)
            if is_valid:
                valid_records.append(rec)
            else:
                formatted = f"Record #{idx} [{rec.get('timestamp')}] invalid: {', '.join(issues)}"
                all_issues.append(formatted)
                logger.warning(formatted)

        report = DataQualityReport(
            total_records=len(records),
            valid_count=len(valid_records),
            invalid_count=len(records) - len(valid_records),
            issues=all_issues
        )
        return valid_records, report

    @classmethod
    def validate_energy_batch(cls, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], DataQualityReport]:
        """Validates a list of energy records, returning valid records and DataQualityReport."""
        valid_records = []
        all_issues = []

        for idx, rec in enumerate(records):
            is_valid, issues = cls.validate_energy_record(rec)
            if is_valid:
                valid_records.append(rec)
            else:
                formatted = f"Record #{idx} [{rec.get('timestamp')}] invalid: {', '.join(issues)}"
                all_issues.append(formatted)
                logger.warning(formatted)

        report = DataQualityReport(
            total_records=len(records),
            valid_count=len(valid_records),
            invalid_count=len(records) - len(valid_records),
            issues=all_issues
        )
        return valid_records, report
