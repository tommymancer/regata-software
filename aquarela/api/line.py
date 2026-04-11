"""Start line / VMC / sight bearing API routes."""

import logging

from fastapi import APIRouter, HTTPException

from ..race.marks import Mark
from ..race.navigation import bearing_to

router = APIRouter(prefix="/api", tags=["line"])
logger = logging.getLogger("aquarela")


def _deps():
    from ..main import (
        current_state, start_line, sight_triangulator,
        mark_store, course_setup,
    )
    return current_state, start_line, sight_triangulator, mark_store, course_setup


@router.post("/line/rc")
async def log_rc():
    """Capture RC boat position from current GPS."""
    state, sl, _, _, _ = _deps()
    if state.lat is None or state.lon is None:
        raise HTTPException(status_code=400, detail="No GPS fix")
    sl.log_rc(state.lat, state.lon)
    return {"rc": {"lat": state.lat, "lon": state.lon}}


@router.post("/line/pin")
async def log_pin():
    """Capture pin end position from current GPS."""
    state, sl, _, _, _ = _deps()
    if state.lat is None or state.lon is None:
        raise HTTPException(status_code=400, detail="No GPS fix")
    sl.log_pin(state.lat, state.lon)
    return {"pin": {"lat": state.lat, "lon": state.lon}}


@router.post("/line/sight")
async def sight_mark():
    """Capture windward mark bearing from current heading.

    Also feeds the sight triangulator.  After 2+ sightings, auto-triangulates
    and adds the computed mark to the mark store as the active target.
    """
    state, sl, tri, ms, _ = _deps()
    if state.heading_mag is None:
        raise HTTPException(status_code=400, detail="No heading data")
    if state.lat is None or state.lon is None:
        raise HTTPException(status_code=400, detail="No GPS fix")

    heading = state.heading_mag
    sl.sight_mark(heading)
    count = tri.add_sighting(state.lat, state.lon, heading)

    result: dict = {
        "mark_bearing": heading,
        "sight_count": count,
        "computed_mark": None,
    }

    computed = tri.computed_mark()
    if computed is not None:
        result["computed_mark"] = computed
        ms.add_mark(
            Mark("Windward (computed)", computed["lat"], computed["lon"], "windward")
        )
        ms.set_active("Windward (computed)")
        ms.set_course_sequence([
            "Windward (computed)", "Leeward", "Windward (computed)",
        ])

        mid = sl.line_midpoint()
        if mid is not None:
            accurate_brg = bearing_to(mid[0], mid[1], computed["lat"], computed["lon"])
            sl.state.mark_bearing = accurate_brg

        logger.info(
            "Mark triangulated at (%.5f, %.5f) from %d sightings",
            computed["lat"], computed["lon"], count,
        )

    return result


@router.get("/line")
async def get_line():
    """Current start line + mark state."""
    state, sl, _, _, _ = _deps()
    result = sl.state.to_dict()
    lb = sl.line_bearing()
    ll = sl.line_length_m()
    result["line_bearing"] = round(lb, 1) if lb is not None else None
    result["line_length_m"] = round(ll, 0) if ll is not None else None
    if state.twd_deg is not None:
        bias = sl.line_bias_deg(state.twd_deg)
        result["line_bias_deg"] = round(bias, 1) if bias is not None else None
        offset = sl.course_offset_deg(state.twd_deg)
        result["course_offset_deg"] = round(offset, 1) if offset is not None else None
    return result


@router.post("/line/reset")
async def reset_line():
    """Clear mark captures + sight bearings.  Re-populates start line from course."""
    _, sl, tri, ms, cs = _deps()
    sl.reset()
    tri.reset()
    ms.remove_mark("Windward (computed)")
    if cs is not None:
        sl.log_rc(cs.rc_lat, cs.rc_lon)
        sl.log_pin(cs.pin_lat, cs.pin_lon)
    return {"reset": True}


@router.get("/course")
async def get_course():
    """Generated race course (ghost marks for simulation)."""
    _, _, _, _, cs = _deps()
    if cs is not None:
        return cs.to_dict()
    return None


@router.get("/sight/bearings")
async def get_sight_bearings():
    """All sight-mark bearing lines + computed mark position."""
    _, _, tri, _, _ = _deps()
    return {
        "sightings": tri.get_sightings(),
        "computed_mark": tri.computed_mark(),
        "count": tri.count,
    }
