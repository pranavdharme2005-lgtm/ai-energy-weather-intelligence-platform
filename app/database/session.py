"""SQLAlchemy Database Engine and Session Management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create engine with fallback connection handling for offline local environments
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False
    )
    # Test connection ping
    with engine.connect() as conn:
        pass
    logger.info("Successfully connected to PostgreSQL database.")
except Exception as e:
    logger.warning(f"Could not connect to PostgreSQL URL ({settings.DATABASE_URL}). Error: {e}. Falling back to SQLite file database.")
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
