"""Maneuvers API routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/maneuvers", tags=["maneuvers"])


def _detector():
    from ..main import maneuver_detector
    return maneuver_detector


@router.get("")
async def list_maneuvers():
    """All detected maneuvers in current session."""
    return [e.to_dict() for e in _detector().events]


@router.get("/stats")
async def maneuver_stats():
    """Summary statistics for tacks and gybes."""
    return _detector().get_stats()


@router.post("/reset")
async def reset_maneuvers():
    """Clear maneuver history."""
    _detector().reset()
    return {"reset": True}
