"""CLI Runner Script for Stage 3 Data Quality Engine & EDA Analysis."""

import argparse
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import settings
from app.database.session import SessionLocal, init_db
from app.database.repository import WeatherRepository, EnergyRepository
from app.data.ingestion import DataIngestionService
from app.data.quality_engine import DataQualityEngine
from app.data.cleaner import DataCleaner
from app.data.features import add_calendar_features, create_lag_features, create_rolling_features, merge_weather_energy
from app.services.eda import EDAEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Data Quality Engine & EDA Runner")
    parser.add_argument("--location", type=str, default=settings.DEFAULT_LOCATION)
    parser.add_argument("--region", type=str, default=settings.DEFAULT_REGION)

    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        logger.info("Executing Ingestion Pipeline to ensure fresh data in DB...")
        ingest_service = DataIngestionService()
        ingest_service.run_pipeline(db=db, location=args.location, region=args.region)

        # 1. Fetch Records from Database
        w_records = WeatherRepository.get_latest(db, location=args.location, limit=100)
        e_records = EnergyRepository.get_latest(db, region=args.region, limit=100)

        w_df = pd.DataFrame([{
            "timestamp": r.timestamp, "location": r.location, "temperature_c": r.temperature_c,
            "humidity_pct": r.humidity_pct, "pressure_hpa": r.pressure_hpa, "wind_speed_ms": r.wind_speed_ms,
            "cloud_cover_pct": r.cloud_cover_pct, "precipitation_mm": r.precipitation_mm,
            "weather_condition": r.weather_condition, "source": r.source
        } for r in w_records])

        e_df = pd.DataFrame([{
            "timestamp": r.timestamp, "region": r.region, "demand_mw": r.demand_mw,
            "peak_demand_flag": r.peak_demand_flag, "source": r.source
        } for r in e_records])

        print("\n" + "=" * 60)
        print("1. DATA QUALITY ENGINE EVALUATION")
        print("=" * 60)

        w_q_report = DataQualityEngine.evaluate_weather_dataframe(w_df)
        e_q_report = DataQualityEngine.evaluate_energy_dataframe(e_df)

        print(f"\n[Weather Quality Score: {w_q_report.scores.overall_quality_score}%]")
        print(f"  - Completeness: {w_q_report.scores.completeness_score}% | Validity: {w_q_report.scores.validity_score}%")
        print(f"  - Uniqueness:   {w_q_report.scores.uniqueness_score}% | Continuity: {w_q_report.scores.continuity_score}%")
        print(f"  - Outliers:     {w_q_report.outlier_count} | Timestamp Gaps: {w_q_report.timestamp_gaps_count}")

        print(f"\n[Energy Quality Score: {e_q_report.scores.overall_quality_score}%]")
        print(f"  - Completeness: {e_q_report.scores.completeness_score}% | Validity: {e_q_report.scores.validity_score}%")
        print(f"  - Uniqueness:   {e_q_report.scores.uniqueness_score}% | Continuity: {e_q_report.scores.continuity_score}%")
        print(f"  - Outliers:     {e_q_report.outlier_count} | Timestamp Gaps: {e_q_report.timestamp_gaps_count}")

        # 2. Data Cleaning & Outlier Classification
        print("\n" + "=" * 60)
        print("2. DATA CLEANING & OUTLIER CLASSIFICATION")
        print("=" * 60)

        cleaned_w = DataCleaner.clean_weather_data(w_df)
        cleaned_e = DataCleaner.clean_energy_data(e_df)

        cleaned_w = DataCleaner.detect_and_classify_outliers(cleaned_w, "temperature_c")
        cleaned_e = DataCleaner.detect_and_classify_outliers(cleaned_e, "demand_mw")

        # 3. Time-Aware Merging & Feature Engineering
        print("\n" + "=" * 60)
        print("3. TIME-AWARE ALIGNMENT MERGE & FEATURE PREPARATION")
        print("=" * 60)

        merged = merge_weather_energy(cleaned_w, cleaned_e, tolerance_minutes=30)
        feat_df = add_calendar_features(merged)
        feat_df = create_lag_features(feat_df, target_col="demand_mw", lags=[1, 24])
        feat_df = create_rolling_features(feat_df, target_col="demand_mw", windows=[6])

        print(f"Aligned dataset created: {len(feat_df)} records, {feat_df.shape[1]} columns.")
        print(f"Engineered Features: {[c for c in feat_df.columns if '_' in c or c in ['hour', 'month', 'season']]}")

        # 4. Statistical Analysis & EDA Insights
        print("\n" + "=" * 60)
        print("4. EXPLORATORY DATA ANALYSIS (EDA) & STATISTICAL INSIGHTS")
        print("=" * 60)

        eda_summary = EDAEngine.analyze_dataset(merged)

        if eda_summary.demand_stats:
            d = eda_summary.demand_stats
            print(f"\nEnergy Load Stats (MW): Mean={d.mean}, Median={d.median}, Std={d.std}, Min={d.min}, Max={d.max}")
            print(f"Percentiles: 25%={d.p25}, 50%={d.p50}, 75%={d.p75}, 95%={d.p95}, 99%={d.p99}")

        if eda_summary.correlations:
            print("\nCross-Domain Correlations with Energy Demand:")
            for corr in eda_summary.correlations:
                print(f"  - {corr.feature:18s}: Pearson r = {corr.pearson_corr:+.4f}, Spearman r = {corr.spearman_corr:+.4f}")
            print(f"  * Note: {eda_summary.correlations[0].disclaimer}")

        print("\nKey Insights Narrative:")
        for note in eda_summary.insights_narrative:
            print(f"  • {note}")

        print("\n" + "=" * 60)
        logger.info("EDA Pipeline Job finished successfully.")

    except Exception as e:
        logger.error(f"Error during EDA execution: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
