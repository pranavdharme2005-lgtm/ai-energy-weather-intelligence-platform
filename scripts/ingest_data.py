"""Data Ingestion CLI Runner Script for Stage 2."""

import argparse
import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import settings
from app.database.session import SessionLocal, init_db
from app.data.ingestion import DataIngestionService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Energy Intelligence Data Ingestion Runner")
    parser.add_argument("--location", type=str, default=settings.DEFAULT_LOCATION, help="Target weather location name")
    parser.add_argument("--latitude", type=float, default=settings.DEFAULT_LATITUDE, help="Target latitude coordinate")
    parser.add_argument("--longitude", type=float, default=settings.DEFAULT_LONGITUDE, help="Target longitude coordinate")
    parser.add_argument("--region", type=str, default=settings.DEFAULT_REGION, help="Target energy grid region name")

    args = parser.parse_args()

    logger.info("Initializing Database tables for ingestion run...")
    init_db()

    db = SessionLocal()
    service = DataIngestionService()

    try:
        report = service.run_pipeline(
            db=db,
            location=args.location,
            latitude=args.latitude,
            longitude=args.longitude,
            region=args.region
        )

        summary_output = f"""
==================================================
INGESTION DATA QUALITY SUMMARY REPORT
==================================================
Weather (Location: {args.location}, Source: Open-Meteo-API):
  - Records Received:  {report.weather_received}
  - Valid Records:     {report.weather_valid}
  - Invalid Records:   {report.weather_invalid}
  - Duplicates Skipped:{report.weather_duplicates}
  - Database Inserted: {report.weather_inserted}

Energy (Region: {args.region}, Source: PJM_OpenData_Historical):
  - Records Received:  {report.energy_received}
  - Valid Records:     {report.energy_valid}
  - Invalid Records:   {report.energy_invalid}
  - Duplicates Skipped:{report.energy_duplicates}
  - Database Inserted: {report.energy_inserted}
==================================================
"""
        print(summary_output)
        logger.info("Data Ingestion Job completed successfully.")

    except Exception as e:
        logger.error(f"Fatal error during data ingestion: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
