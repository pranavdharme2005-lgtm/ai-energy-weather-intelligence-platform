"""CLI Runner Script for Energy & Weather Anomaly Detection Engine."""

import argparse
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import settings
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run Energy & Weather Anomaly Detection Engine")
    parser.add_argument("--region", type=str, default="Grid_Alpha")
    parser.add_argument("--location", type=str, default="London")
    parser.add_argument("--hours", type=int, default=168, help="Analysis window in hours")
    parser.add_argument("--save-db", action="store_true", help="Persist detected anomalies to database")

    args = parser.parse_args()

    logger.info(f"Running Anomaly Detection CLI for region={args.region}, location={args.location}...")
    service = AnomalyDetectionService()
    results = service.run_full_detection(
        region=args.region,
        location=args.location,
        hours=args.hours,
        save_to_db=args.save_db
    )

    summary = results["summary"]
    anomalies = results["anomalies"]

    print("\n" + "=" * 75)
    print("STAGE 6: ENERGY & WEATHER ANOMALY DETECTION REPORT")
    print("=" * 75)
    print(f"Target Region               : {results['region']}")
    print(f"Target Location             : {results['location']}")
    print(f"Time Window Analyzed        : Past {results['window_hours']} Hours")
    print(f"Total Observations Analyzed : {results['total_records_analyzed']}")
    print(f"Total Anomalies Detected    : {summary['total_anomalies']}")
    print(f"High / Critical Severity    : {summary['high_severity_count']} High | {summary['critical_severity_count']} Critical")

    print("\nSeverity Breakdown:")
    for sev, cnt in summary["severity_breakdown"].items():
        if cnt > 0:
            print(f"  • {sev:<10}: {cnt}")

    print("\nAnomaly Category Breakdown:")
    for a_type, cnt in summary["type_breakdown"].items():
        print(f"  • {a_type:<25}: {cnt}")

    if anomalies:
        print("\nTop Detected Anomaly Events:")
        print(f"{'Timestamp (UTC)':<20} | {'Type':<20} | {'Actual':<8} | {'Expected':<8} | {'Severity':<8} | {'Score':<5} | {'Reason'}")
        print("-" * 110)

        # Show top 10 anomalies sorted by score
        sorted_anoms = sorted(anomalies, key=lambda x: x["anomaly_score"], reverse=True)[:10]
        for a in sorted_anoms:
            ts_str = str(a["timestamp"])[:19]
            print(
                f"{ts_str:<20} | {a['anomaly_type']:<20} | {a['actual_value']:<8.1f} | "
                f"{a['expected_value']:<8.1f} | {a['severity']:<8} | {a['anomaly_score']:<5.2f} | {a['description'][:45]}..."
            )

    print("\n" + "=" * 75)
    logger.info("Anomaly Detection CLI finished successfully.")


if __name__ == "__main__":
    main()
