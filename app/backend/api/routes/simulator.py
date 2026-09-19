"""What-If Scenario Simulator API Router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.backend.api.dependencies import get_database_session
from app.backend.api.schemas.simulator import SimulationRequest, SimulationResultDTO
from app.services.simulator import WhatIfSimulatorService

router = APIRouter(prefix="/simulator", tags=["What-If Scenario Simulator"])


@router.post("/run", response_model=SimulationResultDTO, summary="Execute What-If Energy Scenario Simulation")
def run_scenario_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_database_session)
):
    """Executes Stage 8 weather shock simulation without retraining ML models."""
    overrides = {}
    if request.temperature_c_delta != 0.0:
        overrides["temperature_c_delta"] = request.temperature_c_delta
    if request.humidity_pct_delta != 0.0:
        overrides["humidity_pct_delta"] = request.humidity_pct_delta
    if request.precipitation_mm_delta > 0.0:
        overrides["precipitation_mm_delta"] = request.precipitation_mm_delta
    if request.wind_speed_m_s_delta != 0.0:
        overrides["wind_speed_m_s_delta"] = request.wind_speed_m_s_delta

    try:
        sim_res = WhatIfSimulatorService.run_scenario(
            db=db,
            scenario_overrides=overrides,
            region=request.region or settings.DEFAULT_REGION
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Scenario simulation execution failed: {str(e)}")

    if not sim_res:
        raise HTTPException(status_code=503, detail="Scenario simulation failed to compute demand trajectory.")

    base_mw = float(sim_res.get("baseline_demand_mw", sim_res.get("baseline_forecast_mw", 0.0)))
    scen_mw = float(sim_res.get("scenario_demand_mw", sim_res.get("scenario_forecast_mw", 0.0)))
    abs_diff = float(sim_res.get("absolute_change_mw", sim_res.get("absolute_difference_mw", 0.0)))
    pct_diff = float(sim_res.get("percentage_change", sim_res.get("percentage_difference_pct", 0.0)))
    
    warns = sim_res.get("training_range_warnings", [])
    if not warns and sim_res.get("out_of_range_warning"):
        warns = [str(sim_res.get("out_of_range_warning"))]

    return SimulationResultDTO(
        baseline_forecast_mw=round(base_mw, 2),
        scenario_forecast_mw=round(scen_mw, 2),
        absolute_difference_mw=round(abs_diff, 2),
        percentage_difference_pct=round(pct_diff, 2),
        training_range_warnings=[str(w) for w in warns if w],
        uncertainty_available=True,
        model_version=str(sim_res.get("model_version", "v1.0-Stage5"))
    )
