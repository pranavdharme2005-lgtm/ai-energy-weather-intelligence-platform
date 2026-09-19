"""Declarative SQLAlchemy ORM Data Schemas."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now():
    """Helper returning timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class WeatherData(Base):
    """Raw and processed meteorological observation records."""

    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    location = Column(String(100), nullable=False, default="London")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=False)
    humidity_pct = Column(Float, nullable=False)
    pressure_hpa = Column(Float, nullable=False)
    wind_speed_ms = Column(Float, nullable=False)
    cloud_cover_pct = Column(Float, nullable=True, default=0.0)
    precipitation_mm = Column(Float, nullable=True, default=0.0)
    weather_condition = Column(String(50), nullable=True, default="Clear")
    source = Column(String(50), nullable=False, default="Open-Meteo-API")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("location", "timestamp", "source", name="uq_weather_loc_time_src"),
        Index("idx_weather_time_loc", "timestamp", "location"),
    )


class EnergyData(Base):
    """Regional grid power consumption observations."""

    __tablename__ = "energy_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    demand_mw = Column(Float, nullable=False)
    peak_demand_flag = Column(Boolean, default=False, nullable=False)
    source = Column(String(50), nullable=False, default="PJM_OpenData_Historical")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("region", "timestamp", "source", name="uq_energy_reg_time_src"),
        Index("idx_energy_time_region", "timestamp", "region"),
    )


class RainPrediction(Base):
    """Machine learning inference output for rain probability."""

    __tablename__ = "rain_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    prediction_target_time = Column(DateTime(timezone=True), nullable=False)
    rain_predicted = Column(Boolean, nullable=False)
    probability = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False, default="v1.0.0")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class EnergyForecast(Base):
    """Machine learning forecasting output for upcoming grid demand."""

    __tablename__ = "energy_forecasts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    forecast_target_time = Column(DateTime(timezone=True), nullable=False)
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    forecasted_demand_mw = Column(Float, nullable=False)
    confidence_lower_mw = Column(Float, nullable=True)
    confidence_upper_mw = Column(Float, nullable=True)
    forecast_horizon = Column(String(20), nullable=False, default="24h")
    model_version = Column(String(50), nullable=False, default="v1.0.0")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Anomaly(Base):
    """Detected unexpected spikes, dips, or structural breaks in demand or weather."""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    metric_name = Column(String(100), nullable=False, default="demand_mw")
    variable = Column(String(100), nullable=False, default="demand_mw")
    actual_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    deviation = Column(Float, nullable=False, default=0.0)
    anomaly_score = Column(Float, nullable=False, default=0.5)
    severity = Column(String(20), nullable=False, default="MEDIUM")  # NORMAL, LOW, MEDIUM, HIGH, CRITICAL
    anomaly_type = Column(String(50), nullable=False, default="demand_zscore")
    description = Column(String(500), nullable=True)
    detection_method = Column(String(100), nullable=False, default="rolling_zscore")
    model_version = Column(String(50), nullable=False, default="v1.0.0")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)



class Alert(Base):
    """System and operational alerts generated from verified rules, anomalies & forecasts."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(String(100), nullable=False, index=True, default="alt_000")
    alert_type = Column(String(50), nullable=False, default="ENERGY_DEMAND_SPIKE")
    severity = Column(String(20), nullable=False, default="MEDIUM")  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, ACKNOWLEDGED, RESOLVED
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    title = Column(String(150), nullable=False)
    message = Column(String(500), nullable=False)
    reason = Column(String(500), nullable=True)
    observed_value = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    deviation = Column(Float, nullable=True)
    source = Column(String(100), nullable=True, default="rule_engine")
    detection_method = Column(String(100), nullable=True, default="threshold_rule")
    model_version = Column(String(50), nullable=False, default="v1.0.0")
    occurrence_count = Column(Integer, nullable=False, default=1)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class WeatherImpactRecord(Base):
    """Calculated weather-energy impact metrics and statistical associations."""

    __tablename__ = "weather_impact_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    analysis_type = Column(String(50), nullable=False)  # temperature, rain, humidity, correlation, lag, forecast_eval
    weather_variable = Column(String(50), nullable=False)  # temperature_c, humidity_pct, precipitation_mm, weather_condition
    metric_name = Column(String(100), nullable=False)  # avg_demand, correlation_pearson, mae_improvement, etc.
    metric_value = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False, default=0)
    details_json = Column(String(1000), nullable=True)  # JSON-encoded extra details or context
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ScenarioRun(Base):
    """Persisted record of an executed what-if scenario simulation."""

    __tablename__ = "scenario_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scenario_id = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    baseline_demand_mw = Column(Float, nullable=False)
    scenario_demand_mw = Column(Float, nullable=False)
    absolute_change_mw = Column(Float, nullable=False)
    percentage_change = Column(Float, nullable=False)
    baseline_inputs_json = Column(String(2000), nullable=False)
    scenario_inputs_json = Column(String(2000), nullable=False)
    out_of_range_warning = Column(Boolean, default=False, nullable=False)
    model_version = Column(String(50), nullable=False, default="v1.0.0")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AIInsight(Base):
    """Persisted record of AI Analyst daily intelligence reports and Q&A responses."""

    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    insight_type = Column(String(50), nullable=False)  # daily_intelligence, user_qa, anomaly_explanation, scenario_explanation
    region = Column(String(100), nullable=False, default="Grid_Alpha")
    ai_provider = Column(String(50), nullable=False, default="openai")  # openai, mock, fallback
    model_version = Column(String(50), nullable=False, default="gpt-4o-mini")
    summary_text = Column(String(2000), nullable=False)
    response_json = Column(String(4000), nullable=False)
    context_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)



