"""Course setup API routes (pre-race buoy mapping)."""

import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..race.course_setup import CourseSetupManager
from ..race.marks import Mark
from ..race.navigation import bearing_to

_COURSE_FILE = Path("data/course.json")

router = APIRouter(prefix="/api/course-setup", tags=["course-setup"])
logger = logging.getLogger("aquarela")


class AddMarkBody(BaseModel):
    name: str
    mark_type: str = "generic"


class SetMarkTypeBody(BaseModel):
    mark_type: str = "generic"


class CourseSequenceBody(BaseModel):
    marks: List[str] = []


def _deps():
    from ..main import course_setup_mgr, current_state, mark_store, start_line
    return course_setup_mgr, current_state, mark_store, start_line


def _save_course(result, marks_detail):
    """Persist applied course to disk so it survives restarts."""
    try:
        _COURSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "marks": marks_detail,
            "sequence": result.get("sequence", []),
            "rc": result.get("rc"),
            "pin": result.get("pin"),
        }
        _COURSE_FILE.write_text(json.dumps(doc, indent=2))
        logger.info("Course saved to %s", _COURSE_FILE)
    except Exception as e:
        logger.warning("Failed to save course: %s", e)


def restore_course():
    """Restore a previously applied course from disk.

    Called once at startup. Rebuilds MarkStore, start line, and leg bearing.
    """
    if not _COURSE_FILE.exists():
        return
    try:
        doc = json.loads(_COURSE_FILE.read_text())
    except Exception as e:
        logger.warning("Failed to load course file: %s", e)
        return

    from ..main import mark_store, start_line

    mark_store.clear_course_marks()
    for m in doc.get("marks", []):
        mark_store.add_mark(Mark(m["name"], m["lat"], m["lon"], m["mark_type"]))

    seq = doc.get("sequence", [])
    mark_store.set_course_sequence(seq)
    mark_store.next_mark()

    rc = doc.get("rc")
    pin = doc.get("pin")
    if rc:
        start_line.log_rc(rc["lat"], rc["lon"])
    if pin:
        start_line.log_pin(pin["lat"], pin["lon"])

    if rc and pin:
        mid_lat = (rc["lat"] + pin["lat"]) / 2
        mid_lon = (rc["lon"] + pin["lon"]) / 2
        for name in seq:
            mark = mark_store.get(name)
            if mark and mark.mark_type == "windward":
                brg = bearing_to(mid_lat, mid_lon, mark.lat, mark.lon)
                start_line.sight_mark(brg)
                break

    logger.info("Course restored: %d marks, sequence=%s", len(doc.get("marks", [])), seq)


@router.get("/status")
async def course_setup_status():
    """Full course setup state for frontend."""
    mgr, _, _, _ = _deps()
    return mgr.status()


@router.post("/marks")
async def course_setup_add_mark(body: AddMarkBody):
    """Add a mark to the course setup."""
    mgr, _, _, _ = _deps()
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    m = mgr.add_mark(name, body.mark_type)
    return m.to_dict()


@router.delete("/marks/{name}")
async def course_setup_remove_mark(name: str):
    """Remove a mark from the course setup."""
    mgr, _, _, _ = _deps()
    ok = mgr.remove_mark(name)
    return {"removed": ok, "name": name}


@router.post("/marks/{name}/gps")
async def course_setup_log_gps(name: str):
    """Log current GPS position for a mark."""
    mgr, state, _, _ = _deps()
    if state.lat is None or state.lon is None:
        raise HTTPException(status_code=400, detail="No GPS fix")
    return mgr.log_gps(name, state.lat, state.lon)


@router.post("/marks/{name}/sight")
async def course_setup_sight(name: str):
    """Add a sight bearing for mark triangulation."""
    mgr, state, _, _ = _deps()
    if state.lat is None or state.lon is None:
        raise HTTPException(status_code=400, detail="No GPS fix")
    heading = state.heading_mag
    if heading is None:
        raise HTTPException(status_code=400, detail="No heading data")
    return mgr.add_sight(name, state.lat, state.lon, heading)


@router.post("/marks/{name}/reset")
async def course_setup_reset_mark(name: str):
    """Reset a mark's position and sightings."""
    mgr, _, _, _ = _deps()
    ok = mgr.reset_mark(name)
    return {"reset": ok, "name": name}


@router.post("/marks/{name}/type")
async def course_setup_set_type(name: str, body: SetMarkTypeBody):
    """Set the type of a mark."""
    mgr, _, _, _ = _deps()
    ok = mgr.set_mark_type(name, body.mark_type)
    return {"name": name, "mark_type": body.mark_type, "ok": ok}


@router.post("/sequence")
async def course_setup_set_sequence(body: CourseSequenceBody):
    """Set the course leg sequence."""
    mgr, _, _, _ = _deps()
    seq = mgr.set_sequence(body.marks)
    return {"sequence": seq}


@router.post("/apply")
async def course_setup_apply():
    """Apply resolved marks to navigation engine + start line."""
    mgr, _, ms, sl = _deps()
    result = mgr.apply(ms)

    if result.get("rc"):
        sl.log_rc(result["rc"]["lat"], result["rc"]["lon"])
        logger.info("Start line RC set from course setup: %.5f, %.5f",
                     result["rc"]["lat"], result["rc"]["lon"])
    if result.get("pin"):
        sl.log_pin(result["pin"]["lat"], result["pin"]["lon"])
        logger.info("Start line PIN set from course setup: %.5f, %.5f",
                     result["pin"]["lat"], result["pin"]["lon"])

    # Compute leg bearing from start line midpoint to first windward mark
    if result.get("rc") and result.get("pin"):
        mid_lat = (result["rc"]["lat"] + result["pin"]["lat"]) / 2
        mid_lon = (result["rc"]["lon"] + result["pin"]["lon"]) / 2
        # Find the first windward mark in the sequence
        for name in result.get("sequence", []):
            mark = ms.get(name)
            if mark and mark.mark_type == "windward":
                brg = bearing_to(mid_lat, mid_lon, mark.lat, mark.lon)
                sl.sight_mark(brg)
                logger.info("Leg bearing to %s: %.1f° (computed from course setup)", name, brg)
                break

    # Auto-activate the first mark in the sequence so BTW/DTW work immediately
    first = ms.next_mark()
    if first:
        result["active_mark"] = first.name
        logger.info("Auto-activated first mark: %s", first.name)

    # Persist course to disk for restart recovery
    marks_detail = []
    for m in mgr._marks.values():
        if m.is_resolved:
            marks_detail.append({
                "name": m.name, "lat": m.lat, "lon": m.lon, "mark_type": m.mark_type,
            })
    _save_course(result, marks_detail)

    logger.info("Course setup applied: %d marks, sequence=%s", result["total"], result["sequence"])
    return result
