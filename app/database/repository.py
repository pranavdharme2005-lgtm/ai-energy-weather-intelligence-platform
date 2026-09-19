"""Database Repository Layer providing reusable persistence & duplicate prevention methods."""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.models import WeatherData, EnergyData, EnergyForecast, Anomaly, Alert, WeatherImpactRecord, ScenarioRun, AIInsight
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WeatherRepository:
    """Repository managing WeatherData persistence and duplicate prevention."""

    @staticmethod
    def upsert_weather_records(db: Session, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Inserts weather records while preventing duplicates.
        
        Returns:
            Tuple[int, int]: (inserted_count, duplicate_count)
        """
        inserted_count = 0
        duplicate_count = 0

        for rec in records:
            # Check existing record by (location, timestamp, source)
            ts = rec["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))

            existing = db.query(WeatherData).filter(
                WeatherData.location == rec.get("location", "London"),
                WeatherData.timestamp == ts,
                WeatherData.source == rec.get("source", "Open-Meteo-API")
            ).first()

            if existing:
                duplicate_count += 1
                continue

            try:
                weather_obj = WeatherData(
                    timestamp=ts,
                    location=rec.get("location", "London"),
                    latitude=rec.get("latitude"),
                    longitude=rec.get("longitude"),
                    temperature_c=float(rec["temperature_c"]),
                    humidity_pct=float(rec["humidity_pct"]),
                    pressure_hpa=float(rec["pressure_hpa"]),
                    wind_speed_ms=float(rec["wind_speed_ms"]),
                    cloud_cover_pct=float(rec.get("cloud_cover_pct", 0.0)),
                    precipitation_mm=float(rec.get("precipitation_mm", 0.0)),
                    weather_condition=rec.get("weather_condition", "Clear"),
                    source=rec.get("source", "Open-Meteo-API")
                )
                db.add(weather_obj)
                db.commit()
                inserted_count += 1
            except IntegrityError:
                db.rollback()
                duplicate_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Error persisting weather record {rec}: {e}")

        logger.info(f"Weather Repository Upsert Complete: {inserted_count} inserted, {duplicate_count} duplicates skipped.")
        return inserted_count, duplicate_count

    @staticmethod
    def get_latest(db: Session, location: str = "London", limit: int = 24) -> List[WeatherData]:
        """Retrieves recent weather observations."""
        recs = db.query(WeatherData).filter(WeatherData.location == location).order_by(WeatherData.timestamp.desc()).limit(limit).all()
        if not recs and db is not None:
            try:
                from datetime import datetime, timedelta, timezone
                from app.data.ingestion import SyntheticDataIngestor
                from app.data.validator import DataValidator
                now = datetime.now(timezone.utc)
                df = SyntheticDataIngestor().fetch_weather_data(location, now - timedelta(hours=limit + 12), now)
                valid_recs, _ = DataValidator.validate_weather_batch(df.to_dict(orient="records"))
                WeatherRepository.upsert_weather_records(db, valid_recs)
                recs = db.query(WeatherData).filter(WeatherData.location == location).order_by(WeatherData.timestamp.desc()).limit(limit).all()
            except Exception as e:
                logger.warning(f"On-demand weather seeding failed: {e}")
        return recs


class EnergyRepository:
    """Repository managing EnergyData persistence and duplicate prevention."""

    @staticmethod
    def upsert_energy_records(db: Session, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Inserts energy demand records while preventing duplicates.
        
        Returns:
            Tuple[int, int]: (inserted_count, duplicate_count)
        """
        inserted_count = 0
        duplicate_count = 0

        for rec in records:
            ts = rec["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))

            existing = db.query(EnergyData).filter(
                EnergyData.region == rec.get("region", "Grid_Alpha"),
                EnergyData.timestamp == ts,
                EnergyData.source == rec.get("source", "PJM_OpenData_Historical")
            ).first()

            if existing:
                duplicate_count += 1
                continue

            try:
                energy_obj = EnergyData(
                    timestamp=ts,
                    region=rec.get("region", "Grid_Alpha"),
                    demand_mw=float(rec["demand_mw"]),
                    peak_demand_flag=bool(rec.get("peak_demand_flag", False)),
                    source=rec.get("source", "PJM_OpenData_Historical")
                )
                db.add(energy_obj)
                db.commit()
                inserted_count += 1
            except IntegrityError:
                db.rollback()
                duplicate_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Error persisting energy record {rec}: {e}")

        logger.info(f"Energy Repository Upsert Complete: {inserted_count} inserted, {duplicate_count} duplicates skipped.")
        return inserted_count, duplicate_count

    @staticmethod
    def get_latest(db: Session, region: str = "Grid_Alpha", limit: int = 24) -> List[EnergyData]:
        """Retrieves recent energy demand observations."""
        recs = db.query(EnergyData).filter(EnergyData.region == region).order_by(EnergyData.timestamp.desc()).limit(limit).all()
        if not recs and db is not None:
            try:
                from datetime import datetime, timedelta, timezone
                from app.data.ingestion import SyntheticDataIngestor
                from app.data.validator import DataValidator
                now = datetime.now(timezone.utc)
                df = SyntheticDataIngestor().fetch_energy_data(region, now - timedelta(hours=limit + 12), now)
                valid_recs, _ = DataValidator.validate_energy_batch(df.to_dict(orient="records"))
                EnergyRepository.upsert_energy_records(db, valid_recs)
                recs = db.query(EnergyData).filter(EnergyData.region == region).order_by(EnergyData.timestamp.desc()).limit(limit).all()
            except Exception as e:
                logger.warning(f"On-demand energy seeding failed: {e}")
        return recs

    @staticmethod
    def save_forecasts(db: Session, forecasts: List[Dict[str, Any]]) -> int:
        """Persists generated demand forecasts to database.
        
        Returns:
            int: Number of forecasts persisted.
        """
        count = 0
        for f in forecasts:
            try:
                obj = EnergyForecast(
                    timestamp=f["timestamp"],
                    forecast_target_time=f["forecast_target_time"],
                    region=f.get("region", "Grid_Alpha"),
                    forecasted_demand_mw=float(f["forecasted_demand_mw"]),
                    confidence_lower_mw=float(f["confidence_lower_mw"]) if f.get("confidence_lower_mw") is not None else None,
                    confidence_upper_mw=float(f["confidence_upper_mw"]) if f.get("confidence_upper_mw") is not None else None,
                    forecast_horizon=f.get("forecast_horizon", "24h"),
                    model_version=f.get("model_version", "v1.0.0")
                )
                db.add(obj)
                count += 1
            except Exception as e:
                logger.error(f"Error persisting forecast record {f}: {e}")
        try:
            db.commit()
            logger.info(f"Persisted {count} energy forecasts to database.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit forecast records: {e}")
            count = 0
        return count


class AnomalyRepository:
    """Repository managing Anomaly persistence."""

    @staticmethod
    def save_anomalies(db: Session, anomaly_records: List[Dict[str, Any]]) -> int:
        """Persists detected anomaly records to database.
        
        Returns:
            int: Count of persisted anomalies.
        """
        count = 0
        for rec in anomaly_records:
            try:
                ts = rec["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))

                obj = Anomaly(
                    timestamp=ts,
                    region=rec.get("region", "Grid_Alpha"),
                    metric_name=rec.get("metric_name", rec.get("variable", "demand_mw")),
                    variable=rec.get("variable", rec.get("metric_name", "demand_mw")),
                    actual_value=float(rec.get("actual_value", rec.get("observed_value", 0.0))),
                    expected_value=float(rec["expected_value"]),
                    deviation=float(rec.get("deviation", 0.0)),
                    anomaly_score=float(rec.get("anomaly_score", 0.5)),
                    severity=rec.get("severity", "MEDIUM"),
                    anomaly_type=rec.get("anomaly_type", "demand_zscore"),
                    description=rec.get("description", rec.get("reason", "Anomaly detected")),
                    detection_method=rec.get("detection_method", "rolling_zscore"),
                    model_version=rec.get("model_version", "v1.0.0")
                )
                db.add(obj)
                count += 1
            except Exception as e:
                logger.error(f"Error persisting anomaly record {rec}: {e}")
        try:
            db.commit()
            logger.info(f"Persisted {count} anomaly records to database.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit anomaly records: {e}")
            count = 0
        return count

    @staticmethod
    def get_latest(db: Session, region: str = "Grid_Alpha", limit: int = 50) -> List[Anomaly]:
        """Retrieves recent anomaly records."""
        try:
            return db.query(Anomaly).filter(Anomaly.region == region).order_by(Anomaly.timestamp.desc()).limit(limit).all()
        except Exception:
            try:
                return db.query(Anomaly).order_by(Anomaly.timestamp.desc()).limit(limit).all()
            except Exception:
                return []


class WeatherImpactRepository:
    """Repository managing WeatherImpactRecord persistence."""

    @staticmethod
    def save_impact_records(db: Session, records: List[Dict[str, Any]]) -> int:
        """Persists weather impact metrics to database.
        
        Returns:
            int: Count of persisted records.
        """
        count = 0
        now_utc = datetime.now(timezone.utc)
        for rec in records:
            try:
                ts = rec.get("timestamp", now_utc)
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

                obj = WeatherImpactRecord(
                    timestamp=ts,
                    region=rec.get("region", "Grid_Alpha"),
                    analysis_type=rec.get("analysis_type", "general"),
                    weather_variable=rec.get("weather_variable", "temperature_c"),
                    metric_name=rec.get("metric_name", "avg_demand"),
                    metric_value=float(rec.get("metric_value", 0.0)),
                    sample_count=int(rec.get("sample_count", 0)),
                    details_json=rec.get("details_json", None)
                )
                db.add(obj)
                count += 1
            except Exception as e:
                logger.error(f"Error persisting weather impact record {rec}: {e}")
        try:
            db.commit()
            logger.info(f"Persisted {count} weather impact records to database.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit weather impact records: {e}")
            count = 0
        return count

    @staticmethod
    def get_latest(db: Session, region: str = "Grid_Alpha", analysis_type: str = None, limit: int = 50) -> List[WeatherImpactRecord]:
        """Retrieves recent weather impact analytics records."""
        query = db.query(WeatherImpactRecord).filter(WeatherImpactRecord.region == region)
        if analysis_type:
            query = query.filter(WeatherImpactRecord.analysis_type == analysis_type)
        return query.order_by(WeatherImpactRecord.timestamp.desc()).limit(limit).all()


class ScenarioRepository:
    """Repository managing ScenarioRun persistence."""

    @staticmethod
    def save_scenario_run(db: Session, record: Dict[str, Any]) -> int:
        """Persists executed scenario run to database.
        
        Returns:
            int: ID of persisted scenario run, or 0 if failed.
        """
        import json
        try:
            obj = ScenarioRun(
                scenario_id=record.get("scenario_id", "sim_001"),
                region=record.get("region", "Grid_Alpha"),
                baseline_demand_mw=float(record.get("baseline_demand_mw", 0.0)),
                scenario_demand_mw=float(record.get("scenario_demand_mw", 0.0)),
                absolute_change_mw=float(record.get("absolute_change_mw", 0.0)),
                percentage_change=float(record.get("percentage_change", 0.0)),
                baseline_inputs_json=json.dumps(record.get("baseline_inputs", {})),
                scenario_inputs_json=json.dumps(record.get("scenario_inputs", {})),
                out_of_range_warning=bool(record.get("out_of_range_warning", False)),
                model_version=record.get("model_version", "v1.0.0")
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            logger.info(f"Persisted ScenarioRun {obj.scenario_id} to database.")
            return obj.id
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit ScenarioRun record: {e}")
            return 0

    @staticmethod
    def get_recent_scenarios(db: Session, region: str = "Grid_Alpha", limit: int = 20) -> List[ScenarioRun]:
        """Retrieves recent executed scenario runs."""
        return db.query(ScenarioRun).filter(ScenarioRun.region == region).order_by(ScenarioRun.created_at.desc()).limit(limit).all()


class AIInsightRepository:
    """Repository managing AIInsight persistence."""

    @staticmethod
    def save_insight(db: Session, record: Dict[str, Any]) -> int:
        """Persists generated AI Analyst insight or Q&A response to database.
        
        Returns:
            int: ID of persisted insight, or 0 if failed.
        """
        import json
        try:
            obj = AIInsight(
                insight_type=record.get("insight_type", "daily_intelligence"),
                region=record.get("region", "Grid_Alpha"),
                ai_provider=record.get("ai_provider", "openai"),
                model_version=record.get("model_version", "gpt-4o-mini"),
                summary_text=record.get("summary", record.get("summary_text", "")),
                response_json=json.dumps(record.get("response_json", record)),
                context_hash=record.get("context_hash", None)
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            logger.info(f"Persisted AIInsight {obj.id} ({obj.insight_type}) to database.")
            return obj.id
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit AIInsight record: {e}")
            return 0

    @staticmethod
    def get_latest_insight(db: Session, region: str = "Grid_Alpha", insight_type: str = "daily_intelligence") -> Optional[AIInsight]:
        """Retrieves latest AI insight of specified type."""
        return db.query(AIInsight).filter(
            AIInsight.region == region,
            AIInsight.insight_type == insight_type
        ).order_by(AIInsight.created_at.desc()).first()


class AlertRepository:
    """Repository managing Alert persistence, updates, deduplication, and lifecycle transitions."""

    @staticmethod
    def save_or_update_alert(db: Session, record: Dict[str, Any]) -> int:
        """Upserts alert record. If active alert with same alert_id exists, updates occurrence_count and last_seen_at."""
        now_utc = datetime.now(timezone.utc)
        alert_id = record.get("alert_id", "alt_000")
        region = record.get("region", "Grid_Alpha")

        try:
            # Check for existing active/acknowledged alert with same alert_id
            existing = db.query(Alert).filter(
                Alert.alert_id == alert_id,
                Alert.region == region,
                Alert.status.in_(["ACTIVE", "ACKNOWLEDGED"])
            ).first()

            if existing:
                existing.occurrence_count += 1
                existing.last_seen_at = now_utc
                # Allow severity escalation if new record is more severe
                severities = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
                new_sev = record.get("severity", existing.severity)
                if new_sev in severities and existing.severity in severities:
                    if severities.index(new_sev) > severities.index(existing.severity):
                        existing.severity = new_sev
                        existing.title = record.get("title", existing.title)
                        existing.message = record.get("message", existing.message)
                db.commit()
                db.refresh(existing)
                logger.info(f"Updated existing Alert {existing.id} ({existing.alert_id}) count={existing.occurrence_count}")
                return existing.id

            ts = record.get("timestamp", now_utc)
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            obj = Alert(
                alert_id=alert_id,
                alert_type=record.get("alert_type", "ENERGY_DEMAND_SPIKE"),
                severity=record.get("severity", "MEDIUM"),
                status=record.get("status", "ACTIVE"),
                timestamp=ts,
                region=region,
                title=record.get("title", "Alert Triggered"),
                message=record.get("message", "Alert condition met."),
                reason=record.get("reason", None),
                observed_value=float(record["observed_value"]) if record.get("observed_value") is not None else None,
                expected_value=float(record["expected_value"]) if record.get("expected_value") is not None else None,
                deviation=float(record["deviation"]) if record.get("deviation") is not None else None,
                source=record.get("source", "rule_engine"),
                detection_method=record.get("detection_method", "threshold_rule"),
                model_version=record.get("model_version", "v1.0.0"),
                occurrence_count=record.get("occurrence_count", 1),
                is_acknowledged=bool(record.get("is_acknowledged", False)),
                created_at=now_utc,
                last_seen_at=now_utc
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            logger.info(f"Persisted new Alert {obj.id} ({obj.alert_id}) type={obj.alert_type} severity={obj.severity}")
            return obj.id
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist Alert record: {e}")
            return 0

    @staticmethod
    def get_active_alerts(db: Session, region: str = "Grid_Alpha") -> List[Alert]:
        """Retrieves currently ACTIVE alerts for specified region."""
        return db.query(Alert).filter(
            Alert.region == region,
            Alert.status == "ACTIVE"
        ).order_by(Alert.timestamp.desc()).all()

    @staticmethod
    def get_recent_alerts(db: Session, region: str = "Grid_Alpha", limit: int = 50) -> List[Alert]:
        """Retrieves recent alerts regardless of status."""
        return db.query(Alert).filter(Alert.region == region).order_by(Alert.created_at.desc()).limit(limit).all()

    @staticmethod
    def acknowledge_alert(db: Session, alert_db_id: int) -> bool:
        """Transitions alert state to ACKNOWLEDGED."""
        alert = db.query(Alert).filter(Alert.id == alert_db_id).first()
        if alert and alert.status == "ACTIVE":
            alert.status = "ACKNOWLEDGED"
            alert.is_acknowledged = True
            db.commit()
            logger.info(f"Alert {alert_db_id} transitioned to ACKNOWLEDGED.")
            return True
        return False

    @staticmethod
    def resolve_alert(db: Session, alert_db_id: int) -> bool:
        """Transitions alert state to RESOLVED and records resolved_at timestamp."""
        alert = db.query(Alert).filter(Alert.id == alert_db_id).first()
        if alert and alert.status in ["ACTIVE", "ACKNOWLEDGED"]:
            alert.status = "RESOLVED"
            alert.resolved_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Alert {alert_db_id} transitioned to RESOLVED.")
            return True
        return False

    @staticmethod
    def get_alert_summary(db: Session, region: str = "Grid_Alpha") -> Dict[str, Any]:
        """Generates summary count statistics for alerts in specified region."""
        alerts = db.query(Alert).filter(Alert.region == region).all()
        summary = {
            "total_alerts": len(alerts),
            "active_alerts": sum(1 for a in alerts if a.status == "ACTIVE"),
            "acknowledged_alerts": sum(1 for a in alerts if a.status == "ACKNOWLEDGED"),
            "resolved_alerts": sum(1 for a in alerts if a.status == "RESOLVED"),
            "severity_counts": {
                "CRITICAL": sum(1 for a in alerts if a.severity == "CRITICAL" and a.status == "ACTIVE"),
                "HIGH": sum(1 for a in alerts if a.severity == "HIGH" and a.status == "ACTIVE"),
                "MEDIUM": sum(1 for a in alerts if a.severity == "MEDIUM" and a.status == "ACTIVE"),
                "LOW": sum(1 for a in alerts if a.severity == "LOW" and a.status == "ACTIVE"),
                "INFO": sum(1 for a in alerts if a.severity == "INFO" and a.status == "ACTIVE"),
            },
            "by_type": {}
        }
        for a in alerts:
            summary["by_type"][a.alert_type] = summary["by_type"].get(a.alert_type, 0) + 1
        return summary




