"""Sail configuration API — select active sails, view/reset upwash tables."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/sails", tags=["sails"])


@router.get("")
async def get_sails():
    """Return current sail configuration, active selection, and labels."""
    from aquarela.main import config, upwash_tables
    from aquarela.performance.polar_manager import (
        SAIL_CONFIGS, MAIN_LABELS, HEADSAIL_LABELS,
    )
    key = config.sail_config_key()
    info = SAIL_CONFIGS.get(key, {})

    # Build a dynamic label using the actual headsail name (not category)
    main_label = MAIN_LABELS.get(config.active_main, config.active_main)
    hs_label = HEADSAIL_LABELS.get(config.active_headsail, config.active_headsail)
    dynamic_label = f"{main_label} + {hs_label}"

    return {
        "sails": config.sails,
        "active_main": config.active_main,
        "active_headsail": config.active_headsail,
        "active_config_key": key,
        "label": dynamic_label,
        "short": info.get("short", key),
        "all_configs": [
            {"key": k, **v} for k, v in SAIL_CONFIGS.items()
        ],
        "main_labels": MAIN_LABELS,
        "headsail_labels": HEADSAIL_LABELS,
    }


@router.post("")
async def set_sails(payload: dict):
    """Update active sail selection — switches upwash table AND polar."""
    from aquarela.main import config, polar_manager, polar_learners, current_state
    import aquarela.main as main_mod
    changed = False

    if "active_main" in payload:
        if payload["active_main"] not in config.sails.get("mains", []):
            raise HTTPException(400, f"Unknown main: {payload['active_main']}")
        config.active_main = payload["active_main"]
        changed = True

    if "active_headsail" in payload:
        all_headsails = []
        for names in config.sails.get("headsails", {}).values():
            all_headsails.extend(names)
        if payload["active_headsail"] not in all_headsails:
            raise HTTPException(400, f"Unknown headsail: {payload['active_headsail']}")
        config.active_headsail = payload["active_headsail"]
        changed = True

    if changed:
        key = config.sail_config_key()
        # Switch polar manager + learner
        polar_manager.active_sail_type = key
        main_mod.polar = polar_manager.active_polar
        main_mod.polar_learner = polar_learners[key]
        # Update current state so WebSocket broadcasts immediately
        current_state.active_sail_config = key
        config.save()

    return {
        "active_main": config.active_main,
        "active_headsail": config.active_headsail,
        "active_config_key": config.sail_config_key(),
    }


@router.get("/upwash")
async def get_upwash():
    """Return the upwash table for the active sail configuration."""
    from aquarela.main import config, upwash_tables
    key = config.sail_config_key()
    table = upwash_tables.get_table(key)
    if table is None:
        raise HTTPException(404, f"No upwash table for config: {key}")
    return {
        "config_key": key,
        "table": table.to_dict(),
    }


@router.post("/upwash/reset")
async def reset_upwash(payload: dict = None):
    """Reset an upwash table to initial values.

    Optional payload: {"config_key": "main_1__genoa"}
    If omitted, resets the active config's table.
    """
    from aquarela.main import config, upwash_tables
    from aquarela.pipeline.upwash_table import UpwashTable

    key = (payload or {}).get("config_key", config.sail_config_key())
    if key not in upwash_tables.tables:
        raise HTTPException(404, f"No upwash table for config: {key}")

    upwash_tables.tables[key] = UpwashTable.with_initial_values()
    upwash_tables.save("data/upwash_tables.json")

    return {"reset": key, "status": "ok"}
