"""Polar learning API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/polar", tags=["polar"])

_polars_dir = Path("data/polars")


def _deps():
    """Return the active PolarLearner (scoped to current sail type)."""
    from ..main import polar_learner
    return polar_learner


def _manager():
    from ..main import polar_manager
    return polar_manager


@router.get("/stats")
async def polar_stats():
    """Polar learning progress summary (scoped to active sail type)."""
    mgr = _manager()
    stats = _deps().get_stats()
    from ..performance.polar_manager import SAIL_CONFIGS
    info = SAIL_CONFIGS.get(mgr.active_sail_type, {})
    stats["sail_config"] = mgr.active_sail_type
    stats["sail_label"] = info.get("label", "?")
    stats["sail_short"] = info.get("short", "?")
    return stats


@router.get("/coverage")
async def polar_coverage():
    """Per-bin sample counts and learned BSP."""
    return _deps().get_coverage_matrix()


@router.post("/rebuild")
async def polar_rebuild(body: dict = None):
    """Trigger polar rebuild for the active sail type.

    Optional body: {"session_ids": [1, 3, 5]} to rebuild from specific sessions.
    If omitted, uses all sessions marked polar_included=1.
    """
    pl = _deps()
    pl.flush()
    session_ids = (body or {}).get("session_ids", None)
    result = pl.rebuild(session_ids=session_ids)
    if result is not None:
        mgr = _manager()
        mgr.set_polar(mgr.active_sail_type, result)
    return {
        "success": result is not None,
        "bins_ready": pl.get_stats().get("bins_ready", 0),
    }


@router.post("/activate")
async def polar_activate():
    """Switch pipeline to use the learned polar for targets."""
    import aquarela.main as _main
    pl = _main.polar_learner
    learned = pl.learned_polar
    if learned is None:
        raise HTTPException(status_code=404, detail="No learned polar available. Run /api/polar/rebuild first.")
    mgr = _manager()
    mgr.set_polar(mgr.active_sail_type, learned)
    _main.polar = mgr.active_polar
    return {"activated": True, "bins_ready": pl.get_stats().get("bins_ready", 0)}


@router.post("/reset-to-base")
async def polar_reset_to_base():
    """Switch back to the base (factory) polar for the active sail type."""
    import aquarela.main as _main
    mgr = _manager()
    if mgr.base_polar is not None:
        mgr.reset_to_base(mgr.active_sail_type)
        _main.polar = mgr.active_polar
        return {"reset": True}
    raise HTTPException(status_code=404, detail="No base polar loaded")


@router.post("/clear")
async def polar_clear():
    """Clear all learned polar data."""
    _deps().reset()
    return {"cleared": True}


@router.get("/diagram")
async def polar_diagram():
    """Full polar grid data for rendering a polar diagram.

    Returns base polar, learned polar (if any), and targets.
    """
    mgr = _manager()
    pl = _deps()
    base = mgr.base_polar
    learned = pl.learned_polar

    def _grid_to_curves(polar):
        if polar is None:
            return {}
        # Group by TWS → list of (TWA, BSP)
        curves = {}
        for (tws, twa), bsp in sorted(polar.bsp_grid.items()):
            tws_key = float(tws)
            if tws_key not in curves:
                curves[tws_key] = []
            curves[tws_key].append({"twa": twa, "bsp": round(bsp, 2)})
        return curves

    def _targets(polar):
        if polar is None:
            return {"upwind": {}, "downwind": {}}
        up = {}
        for tws, (twa, bsp, vmg) in polar.upwind_targets.items():
            up[float(tws)] = {"twa": round(twa, 1), "bsp": round(bsp, 2), "vmg": round(vmg, 2)}
        down = {}
        for tws, (twa, bsp, vmg) in polar.downwind_targets.items():
            down[float(tws)] = {"twa": round(twa, 1), "bsp": round(bsp, 2), "vmg": round(vmg, 2)}
        return {"upwind": up, "downwind": down}

    return {
        "base_curves": _grid_to_curves(base),
        "learned_curves": _grid_to_curves(learned),
        "base_targets": _targets(base),
        "learned_targets": _targets(learned),
        "has_learned": learned is not None,
        "sail_config": mgr.active_sail_type,
    }


@router.get("/snapshots")
async def polar_snapshots():
    """List saved polar snapshots (newest first)."""
    if not _polars_dir.exists():
        return []
    files = sorted(_polars_dir.glob("learned_*.json"), reverse=True)
    result = []
    for f in files:
        try:
            import json
            doc = json.loads(f.read_text())
            result.append({
                "filename": f.name,
                "name": doc.get("name", f.stem),
                "created": doc.get("created", ""),
                "total_samples": doc.get("total_samples", 0),
                "bins_ready": doc.get("bins_ready", 0),
            })
        except Exception:
            result.append({"filename": f.name, "name": f.stem, "created": "", "total_samples": 0, "bins_ready": 0})
    return result


@router.get("/snapshots/{filename}")
async def polar_download(filename: str):
    """Download a polar snapshot JSON file."""
    path = _polars_dir / filename
    if not path.exists() or not path.name.startswith("learned_"):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return FileResponse(path, media_type="application/json", filename=filename)
