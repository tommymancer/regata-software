"""Race timer API routes."""

from fastapi import APIRouter

from ..race.timer import RaceTimer

router = APIRouter(prefix="/api/race", tags=["race"])


def _timer() -> RaceTimer:
    from ..main import race_timer
    return race_timer


@router.post("/start")
async def race_start(minutes: int = 5):
    """Start countdown (typical: 5, 3, or 1 minute sequence)."""
    timer = _timer()
    timer.start(minutes)
    return {"state": timer.state, "countdown_secs": minutes * 60}


@router.post("/sync/up")
async def race_sync_up():
    """Add 1 minute to countdown (synchronise to committee signal)."""
    timer = _timer()
    timer.sync_up()
    return {"state": timer.state}


@router.post("/sync/down")
async def race_sync_down():
    """Remove 1 minute from countdown."""
    timer = _timer()
    timer.sync_down()
    return {"state": timer.state}


@router.post("/stop")
async def race_stop():
    """Stop timer (back to idle)."""
    timer = _timer()
    timer.stop()
    return {"state": timer.state}


@router.post("/reset")
async def race_reset():
    """Full reset."""
    timer = _timer()
    timer.reset()
    return {"state": timer.state}


@router.get("/state")
async def race_state():
    """Current timer state."""
    timer = _timer()
    return {
        "state": timer.state,
        "secs": timer.get_seconds(),
    }
