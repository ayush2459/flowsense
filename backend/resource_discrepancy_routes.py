from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from resource_discrepancy_engine import analyze_facility

router = APIRouter(
    prefix="/api/resource-discrepancy",
    tags=["Resource Discrepancy"],
)


class ResourceTelemetry(BaseModel):
    facility_code: Optional[str] = None
    facility_name: Optional[str] = None

    energy_kwh: Optional[float] = Field(default=None, ge=0)
    expected_energy_kwh: Optional[float] = Field(default=None, gt=0)

    water_kl: Optional[float] = Field(default=None, ge=0)
    expected_water_kl: Optional[float] = Field(default=None, gt=0)

    power_factor: Optional[float] = Field(default=None, ge=0, le=1)
    load_factor: Optional[float] = Field(default=None, ge=0, le=1)


@router.post("/analyze")
def analyze_resource_discrepancy(data: ResourceTelemetry):
    try:
        telemetry = data.model_dump()
        return analyze_facility(telemetry)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unable to analyze telemetry: {exc}",
        ) from exc
