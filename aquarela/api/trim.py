"""Trim book API routes."""

from fastapi import APIRouter, HTTPException

from ..training.trim_book import TrimSnapshot
from ..training.trim_guide import get_trim_guide

router = APIRouter(prefix="/api/trim", tags=["trim"])


def _deps():
    from ..main import trim_book, session_manager, current_state
    return trim_book, session_manager, current_state


@router.post("")
async def save_trim(
    cunningham: str = "",
    outhaul: str = "",
    vang: str = "",
    jib_lead: str = "",
    jib_halyard: str = "",
    traveller: str = "",
    forestay: str = "",
    notes: str = "",
    sea_state: str = "",
):
    """Save a trim snapshot with current conditions."""
    tb, sm, state = _deps()
    snap = TrimSnapshot(
        session_id=(
            sm.active_session.id if sm.active_session else None
        ),
        tws_kt=state.tws_kt,
        twa_deg=state.twa_deg,
        bsp_kt=state.bsp_kt,
        perf_pct=state.perf_pct,
        cunningham=cunningham,
        outhaul=outhaul,
        vang=vang,
        jib_lead=jib_lead,
        jib_halyard=jib_halyard,
        traveller=traveller,
        forestay=forestay,
        notes=notes,
        sea_state=sea_state,
    )
    snap_id = tb.save(snap)
    return {"id": snap_id, **snap.to_dict()}


@router.get("")
async def list_trims(limit: int = 50):
    """List recent trim snapshots."""
    tb, _, _ = _deps()
    return [s.to_dict() for s in tb.list_all(limit)]


@router.get("/best")
async def best_trim(tws: float, twa: float, sea_state: str = ""):
    """Find best-performing trim for given conditions."""
    tb, _, _ = _deps()
    snap = tb.best_for_conditions(tws, twa, sea_state=sea_state)
    if snap:
        return snap.to_dict()
    return {"match": None}


@router.delete("/{snap_id}")
async def delete_trim(snap_id: int):
    """Delete a trim snapshot."""
    tb, _, _ = _deps()
    if tb.delete(snap_id):
        return {"deleted": snap_id}
    raise HTTPException(status_code=404, detail="not found")


@router.get("/guide")
async def trim_guide(sea_state: str = ""):
    """Guided trim procedure for current conditions."""
    from ..main import current_state, polar_manager
    if current_state.tws_kt is None or current_state.twa_deg is None:
        raise HTTPException(status_code=400, detail="No wind data — start sailing first")
    return get_trim_guide(
        tws=current_state.tws_kt,
        twa=current_state.twa_deg,
        sail_type=polar_manager.active_sail_type,
        sea_state=sea_state,
    )
