"""Main Runnable CLI Launcher for Energy Intelligence Platform."""

import argparse
import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_backend(port: int = None, host: str = None):
    """Launches the FastAPI backend server using Uvicorn."""
    target_port = port or settings.PORT
    target_host = host or settings.HOST
    logger.info(f"Launching FastAPI backend server at http://{target_host}:{target_port} ...")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.backend.main:app",
        "--host", target_host,
        "--port", str(target_port),
        "--reload" if settings.DEBUG else "--no-reload"
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_frontend(port: int = None):
    """Launches the Streamlit control center dashboard."""
    target_port = port or settings.STREAMLIT_PORT
    logger.info(f"Launching Streamlit dashboard at http://localhost:{target_port} ...")
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "app/frontend/main.py",
        "--server.port", str(target_port),
        "--server.address", "localhost"
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_ingest():
    """Triggers the data ingestion script."""
    logger.info("Executing Data Ingestion script...")
    cmd = [sys.executable, "scripts/ingest_data.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_eda():
    """Triggers the Data Quality Engine & EDA Analysis script."""
    logger.info("Executing Data Quality & EDA Pipeline script...")
    cmd = [sys.executable, "scripts/run_eda.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_train_rain():
    """Triggers the Rain Prediction ML Model training script."""
    logger.info("Executing Rain Prediction ML Model training script...")
    cmd = [sys.executable, "scripts/train_rain_model.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_train_energy():
    """Triggers the Energy Demand Forecaster ML Model training script."""
    logger.info("Executing Energy Demand Forecaster ML Model training script...")
    cmd = [sys.executable, "scripts/train_energy_model.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_anomaly():
    """Triggers the Energy & Weather Anomaly Detection script."""
    logger.info("Executing Energy & Weather Anomaly Detection script...")
    cmd = [sys.executable, "scripts/run_anomaly_detection.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_weather_impact():
    """Triggers the Weather Impact Analytics Module script."""
    logger.info("Executing Weather Impact Analytics script...")
    cmd = [sys.executable, "scripts/run_weather_impact.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_simulate():
    """Triggers the What-If Energy Scenario Simulator script."""
    logger.info("Executing What-If Energy Scenario Simulator script...")
    cmd = [sys.executable, "scripts/run_scenario_simulator.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_ai_analyst():
    """Triggers the AI Energy Analyst Module script."""
    logger.info("Executing AI Energy Analyst Module script...")
    cmd = [sys.executable, "scripts/run_ai_analyst.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_alerts():
    """Triggers the Smart Alert Center script."""
    logger.info("Executing Smart Alert Center script...")
    cmd = [sys.executable, "scripts/run_smart_alerts.py"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def run_tests():
    """Executes pytest suite."""
    logger.info("Executing Pytest test suite...")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def main():
    parser = argparse.ArgumentParser(description="Energy Intelligence Platform Launcher CLI")
    parser.add_argument(
        "mode",
        choices=["backend", "frontend", "ingest", "eda", "train-rain", "train-energy", "anomaly", "weather-impact", "simulate", "ai-analyst", "alerts", "test"],
        help="Target runtime mode: 'backend', 'frontend', 'ingest', 'eda', 'train-rain', 'train-energy', 'anomaly', 'weather-impact', 'simulate', 'ai-analyst', 'alerts', or 'test'"
    )
    parser.add_argument("--port", type=int, default=None, help="Custom port override")
    parser.add_argument("--host", type=str, default=None, help="Custom host override")

    args = parser.parse_args()

    if args.mode == "backend":
        run_backend(port=args.port, host=args.host)
    elif args.mode == "frontend":
        run_frontend(port=args.port)
    elif args.mode == "ingest":
        run_ingest()
    elif args.mode == "eda":
        run_eda()
    elif args.mode == "train-rain":
        run_train_rain()
    elif args.mode == "train-energy":
        run_train_energy()
    elif args.mode == "anomaly":
        run_anomaly()
    elif args.mode == "weather-impact":
        run_weather_impact()
    elif args.mode == "simulate":
        run_simulate()
    elif args.mode == "ai-analyst":
        run_ai_analyst()
    elif args.mode == "alerts":
        run_alerts()
    elif args.mode == "test":
        run_tests()



if __name__ == "__main__":
    main()
