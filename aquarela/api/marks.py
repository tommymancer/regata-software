"""Marks / Navigation API routes."""

from fastapi import APIRouter, HTTPException

from ..race.marks import MarkStore

router = APIRouter(prefix="/api/marks", tags=["marks"])


def _store() -> MarkStore:
    from ..main import mark_store
    return mark_store


@router.get("")
async def list_marks():
    """All available marks."""
    return [m.to_dict() for m in _store().list_marks()]


@router.post("/active")
async def set_active_mark(name: str):
    """Set navigation target mark by name."""
    store = _store()
    if store.set_active(name):
        return {"active": name}
    raise HTTPException(status_code=404, detail=f"Mark '{name}' not found")


@router.delete("/active")
async def clear_active_mark():
    """Clear navigation target."""
    _store().clear_active()
    return {"active": None}


@router.get("/active")
async def get_active_mark():
    """Current navigation target."""
    m = _store().active_mark
    if m:
        return m.to_dict()
    return {"active": None}


@router.post("/next")
async def next_mark():
    """Advance to the next mark in the course sequence (mark rounding)."""
    store = _store()
    m = store.next_mark()
    if m:
        return {
            "active": m.name,
            "leg": store.course_leg,
            "total_legs": store.course_total_legs,
        }
    raise HTTPException(status_code=404, detail="No course sequence or already at last mark")
