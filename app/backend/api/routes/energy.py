"""Energy Demand Telemetry API Router."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session, PaginationParams
from app.backend.api.schemas.energy import EnergyDataDTO, EnergySummaryDTO
from app.database.repository import EnergyRepository
from app.data.ingestion import SyntheticDataIngestor

router = APIRouter(prefix="/energy", tags=["Energy Load Telemetry"])
ingestor = SyntheticDataIngestor()


@router.get("/current", response_model=EnergyDataDTO, summary="Current Energy Load Observation")
def get_current_energy(
    region: str = Query(default=settings.DEFAULT_REGION, description="Target electrical grid region"),
    db: Session = Depends(get_database_session)
):
    """Retrieves latest grid load observation for specified region."""
    records = EnergyRepository.get_latest(db, region=region, limit=1)
    if records:
        r = records[0]
        return EnergyDataDTO(
            timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
            region=r.region,
            demand_mw=r.demand_mw,
            peak_demand_flag=r.peak_demand_flag,
            source=r.source
        )

    # Fallback ingestion if DB is unseeded
    now = datetime.now()
    df = ingestor.fetch_energy_data(region=region, start_time=now - timedelta(hours=1), end_time=now)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No energy demand records found for region '{region}'.")

    row = df.iloc[-1].to_dict()
    return EnergyDataDTO(
        timestamp=str(row.get("timestamp", now.isoformat())),
        region=region,
        demand_mw=float(row.get("demand_mw", 2800.0)),
        peak_demand_flag=bool(row.get("peak_demand_flag", False)),
        source="PJM_OpenData_Historical"
    )


@router.get("/latest", response_model=EnergyDataDTO, summary="Alias for Current Energy Load Observation")
def get_latest_energy_alias(
    region: str = Query(default=settings.DEFAULT_REGION),
    db: Session = Depends(get_database_session)
):
    """Alias for /energy/current."""
    return get_current_energy(region=region, db=db)


@router.get("/history", response_model=List[EnergyDataDTO], summary="Historical Energy Load Feed")
def get_energy_history(
    region: str = Query(default=settings.DEFAULT_REGION, description="Target electrical grid region"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_database_session)
):
    """Retrieves recent historical grid load records."""
    records = EnergyRepository.get_latest(db, region=region, limit=pagination.limit)
    if records:
        return [
            EnergyDataDTO(
                timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                region=r.region,
                demand_mw=r.demand_mw,
                peak_demand_flag=r.peak_demand_flag,
                source=r.source
            ) for r in records
        ]

    now = datetime.now()
    df = ingestor.fetch_energy_data(region=region, start_time=now - timedelta(hours=pagination.limit), end_time=now)
    results = []
    for _, row in df.iterrows():
        results.append(EnergyDataDTO(
            timestamp=str(row["timestamp"]),
            region=region,
            demand_mw=float(row["demand_mw"]),
            peak_demand_flag=bool(row.get("peak_demand_flag", False)),
            source="PJM_OpenData_Historical"
        ))
    return results


@router.get("/summary", response_model=EnergySummaryDTO, summary="Aggregated Energy Demand Summary Analytics")
def get_energy_summary(
    region: str = Query(default=settings.DEFAULT_REGION, description="Target electrical grid region"),
    db: Session = Depends(get_database_session)
):
    """Computes summary statistics across recent grid load observations."""
    records = EnergyRepository.get_latest(db, region=region, limit=48)
    if not records:
        curr = get_current_energy(region=region, db=db)
        return EnergySummaryDTO(
            region=region,
            current_demand_mw=curr.demand_mw,
            avg_demand_mw=curr.demand_mw,
            max_demand_mw=curr.demand_mw,
            min_demand_mw=curr.demand_mw,
            peak_incidents_count=1 if curr.peak_demand_flag else 0,
            records_analyzed=1
        )

    demands = [r.demand_mw for r in records]
    peaks = sum(1 for r in records if r.peak_demand_flag)

    return EnergySummaryDTO(
        region=region,
        current_demand_mw=records[0].demand_mw,
        avg_demand_mw=round(sum(demands) / len(demands), 2),
        max_demand_mw=round(max(demands), 2),
        min_demand_mw=round(min(demands), 2),
        peak_incidents_count=peaks,
        records_analyzed=len(records)
    )
