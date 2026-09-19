"""SQLAlchemy Database Engine and Session Management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

import os

IS_POSTGRESQL = False
DB_STATUS_MESSAGE = ""

# Resolve DATABASE_URL: Streamlit Secrets -> Environment Variable -> App Settings -> SQLite Default
raw_db_url = ""
try:
    import streamlit as st
    if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
        raw_db_url = str(st.secrets["DATABASE_URL"])
except Exception:
    pass

if not raw_db_url:
    raw_db_url = os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", "sqlite:///energy_intelligence.db")

# Prevent connecting to localhost/127.0.0.1 PostgreSQL in cloud environment
if ("localhost" in raw_db_url or "127.0.0.1" in raw_db_url) and "sqlite" not in raw_db_url:
    logger.warning(
        f"[DB CONFIGURATION NOTICE] Localhost PostgreSQL URL detected ({raw_db_url}). "
        "Unreachable in cloud deployment. Switching to local SQLite database 'energy_intelligence.db'."
    )
    raw_db_url = "sqlite:///energy_intelligence.db"

try:
    engine = create_engine(
        raw_db_url,
        pool_pre_ping=True,
        echo=False
    )
    # Test connection ping
    with engine.connect() as conn:
        pass
    IS_POSTGRESQL = "sqlite" not in raw_db_url
    DB_STATUS_MESSAGE = "PostgreSQL Connected" if IS_POSTGRESQL else "SQLite Database Active"
    logger.info(f"Successfully connected to database engine ({raw_db_url.split('@')[-1] if '@' in raw_db_url else raw_db_url}).")
except Exception as e:
    IS_POSTGRESQL = False
    DB_STATUS_MESSAGE = "SQLite Fallback Mode (Configured DB connection failed)"
    logger.warning(
        f"[DB CONFIGURATION WARNING] Could not connect to database URL ({raw_db_url}). "
        f"Error: {e}. Falling back to SQLite file database 'energy_intelligence.db'. "
        "To use production PostgreSQL, set DATABASE_URL in Streamlit Cloud Secrets."
    )
    engine = create_engine("sqlite:///energy_intelligence.db", connect_args={"check_same_thread": False}, echo=False)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency generator for FastAPI database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database tables based on ORM models and executes column migrations for SQLite fallback."""
    from app.database.models import Base
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")

        # Lightweight column migration check for SQLite
        with engine.begin() as conn:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)

            if "alerts" in inspector.get_table_names():
                existing_cols = [c["name"] for c in inspector.get_columns("alerts")]
                new_cols = {
                    "alert_id": "VARCHAR(100) DEFAULT 'alt_000'",
                    "status": "VARCHAR(20) DEFAULT 'ACTIVE'",
                    "region": "VARCHAR(100) DEFAULT 'Grid_Alpha'",
                    "reason": "VARCHAR(500)",
                    "observed_value": "FLOAT",
                    "expected_value": "FLOAT",
                    "deviation": "FLOAT",
                    "source": "VARCHAR(100) DEFAULT 'rule_engine'",
                    "detection_method": "VARCHAR(100) DEFAULT 'threshold_rule'",
                    "model_version": "VARCHAR(50) DEFAULT 'v1.0.0'",
                    "occurrence_count": "INTEGER DEFAULT 1",
                    "last_seen_at": "TIMESTAMP",
                    "resolved_at": "TIMESTAMP"
                }
                for col_name, col_type in new_cols.items():
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}"))
                            logger.info(f"Added column '{col_name}' to 'alerts' table.")
                        except Exception as ex:
                            logger.warning(f"Could not add column '{col_name}' to alerts: {ex}")

            if "anomalies" in inspector.get_table_names():
                existing_cols = [c["name"] for c in inspector.get_columns("anomalies")]
                anomaly_new_cols = {
                    "region": "VARCHAR(100) DEFAULT 'Grid_Alpha'",
                    "metric_name": "VARCHAR(100) DEFAULT 'demand_mw'",
                    "variable": "VARCHAR(100) DEFAULT 'demand_mw'",
                    "actual_value": "FLOAT DEFAULT 0.0",
                    "expected_value": "FLOAT DEFAULT 0.0",
                    "deviation": "FLOAT DEFAULT 0.0",
                    "anomaly_score": "FLOAT DEFAULT 0.5",
                    "severity": "VARCHAR(20) DEFAULT 'MEDIUM'",
                    "anomaly_type": "VARCHAR(50) DEFAULT 'demand_zscore'",
                    "description": "VARCHAR(500)",
                    "detection_method": "VARCHAR(100) DEFAULT 'rolling_zscore'",
                    "model_version": "VARCHAR(50) DEFAULT 'v1.0.0'"
                }
                for col_name, col_type in anomaly_new_cols.items():
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE anomalies ADD COLUMN {col_name} {col_type}"))
                            logger.info(f"Added column '{col_name}' to 'anomalies' table.")
                        except Exception as ex:
                            logger.warning(f"Could not add column '{col_name}' to anomalies: {ex}")

    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    # Auto-seed initial telemetry if weather or energy tables are empty
    try:
        from datetime import datetime, timedelta, timezone
        from app.database.models import WeatherData, EnergyData
        from app.data.ingestion import SyntheticDataIngestor
        from app.data.validator import DataValidator
        from app.database.repository import WeatherRepository, EnergyRepository

        with SessionLocal() as db_session:
            w_count = db_session.query(WeatherData).count()
            e_count = db_session.query(EnergyData).count()

            if w_count == 0 or e_count == 0:
                logger.info("Empty database detected on boot. Seeding initial telemetry data...")
                ingestor = SyntheticDataIngestor()
                now = datetime.now(timezone.utc)
                start_time = now - timedelta(hours=72)

                if w_count == 0:
                    df_w = ingestor.fetch_weather_data("London", start_time, now)
                    recs_w, _ = DataValidator.validate_weather_batch(df_w.to_dict(orient="records"))
                    WeatherRepository.upsert_weather_records(db_session, recs_w)
                    logger.info("Successfully seeded weather telemetry records.")

                if e_count == 0:
                    df_e = ingestor.fetch_energy_data("Grid_Alpha", start_time, now)
                    recs_e, _ = DataValidator.validate_energy_batch(df_e.to_dict(orient="records"))
                    EnergyRepository.upsert_energy_records(db_session, recs_e)
                    logger.info("Successfully seeded energy load telemetry records.")
    except Exception as seed_err:
        logger.warning(f"Auto-seeding initial telemetry failed: {seed_err}")


# Automatically run init_db on module import to guarantee all required tables exist
try:
    init_db()
except Exception as _init_err:
    logger.warning(f"Auto-initialization of DB on import failed: {_init_err}")

