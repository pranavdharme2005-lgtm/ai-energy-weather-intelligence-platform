"""Production Database Initialization and Health Audit Script."""

import sys
from pathlib import Path
from sqlalchemy import inspect, text

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import settings
from app.database.session import engine, init_db, SessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("Initializing production database tables...")
    init_db()

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Verified Database Connection. Active Tables: {tables}")

    expected_tables = [
        "weather_data",
        "energy_data",
        "rain_predictions",
        "energy_forecasts",
        "anomalies",
        "alerts",
        "weather_impact_records",
        "scenario_runs",
        "ai_insights"
    ]

    missing = [t for t in expected_tables if t not in tables]
    if missing:
        logger.warning(f"Missing expected tables: {missing}")
    else:
        logger.info("All 9 required production database tables verified successfully.")

    # Perform read/write ping test
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.info("Database read ping test passed.")
    except Exception as e:
        logger.error(f"Database query test failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
