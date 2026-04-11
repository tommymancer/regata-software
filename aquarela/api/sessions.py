"""Sessions API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _mgr():
    from ..main import session_manager
    return session_manager


def _polar_deps():
    from ..main import polar_learner
    return polar_learner


class PolarIncludedBody(BaseModel):
    polar_included: bool


@router.get("")
async def list_sessions(limit: int = 50):
    """List recent sessions with polar sample counts."""
    mgr = _mgr()
    pl = _polar_deps()
    sessions = mgr.list_sessions(limit)
    polar_stats = {
        row["session_id"]: row["sample_count"]
        for row in pl.get_session_polar_stats()
    }
    result = []
    for s in sessions:
        d = s.to_dict()
        d["polar_samples"] = polar_stats.get(s.id, 0)
        result.append(d)
    return result


@router.get("/active")
async def active_session():
    """Current active session."""
    s = _mgr().active_session
    return s.to_dict() if s else {"active": None}


@router.post("/start")
async def start_session(session_type: str = "training"):
    """Manually start a session."""
    s = _mgr().force_start(session_type)
    return s.to_dict()


@router.post("/stop")
async def stop_session():
    """Manually stop the active session."""
    s = _mgr().force_stop()
    return s.to_dict() if s else {"active": None}


@router.post("/{session_id}/polar-included")
async def set_polar_included(session_id: int, body: PolarIncludedBody):
    """Toggle whether a session's polar data is used in rebuilds."""
    mgr = _mgr()
    session = mgr.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    mgr.set_polar_included(session_id, body.polar_included)
    return {"session_id": session_id, "polar_included": body.polar_included}


@router.get("/{session_id}/maneuvers")
async def session_maneuvers(session_id: int):
    """List all maneuvers for a specific session."""
    from ..training.maneuvers import list_maneuvers_for_session
    mgr = _mgr()
    rows = list_maneuvers_for_session(mgr._get_conn(), session_id)
    return rows
