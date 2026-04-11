"""Interactive simulator API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..nmea.source_interactive import InteractiveSource

router = APIRouter(prefix="/api/sim", tags=["simulator"])


class HelmInput(BaseModel):
    heading: Optional[float] = None
    delta: Optional[float] = None


class PositionInput(BaseModel):
    lat: float
    lon: float
    heading: Optional[float] = None


class WindInput(BaseModel):
    twd: Optional[float] = None
    tws: Optional[float] = None
    twd_delta: Optional[float] = None
    tws_delta: Optional[float] = None


def _source() -> InteractiveSource:
    from ..main import active_source
    if not isinstance(active_source, InteractiveSource):
        raise HTTPException(status_code=409, detail="Not in interactive mode")
    return active_source


@router.post("/helm")
async def sim_helm(payload: HelmInput):
    """Change boat heading (interactive mode only)."""
    src = _source()
    hdg = src.set_heading(heading=payload.heading, delta=payload.delta)
    return {"heading": round(hdg, 1)}


@router.post("/position")
async def sim_position(payload: PositionInput):
    """Teleport boat to a lat/lon (interactive mode only)."""
    src = _source()
    return src.set_position(lat=payload.lat, lon=payload.lon, heading=payload.heading)


@router.post("/wind")
async def sim_wind(payload: WindInput):
    """Set wind conditions (interactive mode only)."""
    src = _source()
    return src.set_wind(
        twd=payload.twd,
        tws=payload.tws,
        twd_delta=payload.twd_delta,
        tws_delta=payload.tws_delta,
    )


@router.get("/state")
async def sim_state():
    """Current simulator state (interactive mode only)."""
    src = _source()
    return {
        "heading": round(src.heading, 1),
        "twd": round(src.twd_base, 1),
        "tws": round(src.tws_base, 1),
        "lat": src.lat,
        "lon": src.lon,
    }
