# Auto Polar Learning & Impact Visibility

## Goal

Automate the polar learning lifecycle (rebuild + activate) so it happens silently at session end, and add a dedicated diff heatmap view to PolarDiagramPage so the user can see exactly where and how much the learned polar differs from the base.

## Architecture

Two independent changes:

1. **Backend**: auto-rebuild + auto-activate at session end
2. **Frontend**: diff heatmap view in PolarDiagramPage

No new dependencies. No new API endpoints. Uses existing infrastructure.

---

## 1. Auto-Learning (Backend)

### Trigger

When `SessionManager.end_session()` fires (GPS idle, connection closed, or explicit stop), the system automatically rebuilds and activates the learned polar.

### Existing Code in main.py

There are **two** places that already touch polar rebuild/flush:

1. **`session_event == "stopped"` block (line ~393)**: calls `polar_learners[key].flush()` for the active sail config. This fires during normal pipeline operation when sailing stops.

2. **`finally` block (line ~458)**: runs on pipeline shutdown. Flushes ALL learners, then calls `rebuild()` on the active learner — but **does not activate** the result (no `set_polar`, no `_main.polar` update). This is the gap to fix.

### Changes

**At the `session_event == "stopped"` callsite** (primary trigger — fires every time a sailing session ends):

After the existing `flush()` call, add rebuild + activate:

```python
elif session_event == "stopped":
    logger.info("Sailing stopped — closing CSV session")
    csv_logger.stop_session()
    if config.source not in ("simulator", "interactive"):
        key = config.sail_config_key()
        learner = polar_learners[key]
        learner.flush()  # already exists
        try:
            learned = learner.rebuild()
            if learned is not None:
                polar_manager.set_polar(key, learned)
                polar = polar_manager.active_polar  # update module-level global
                logger.info("Auto-activated learned polar for %s", key)
        except Exception:
            logger.exception("Auto-rebuild failed, keeping current polar")
```

**In the `finally` block** (pipeline shutdown — crash or cancel):

The existing code already calls `rebuild()` but discards the result. Extend it to also activate:

```python
finally:
    csv_logger.stop_session()
    for _st, _pl in polar_learners.items():
        _pl.flush()
    if config.source not in ("simulator", "interactive"):
        key = config.sail_config_key()
        _active_learner = polar_learners[key]
        learned = _active_learner.rebuild()
        if learned is not None:
            polar_manager.set_polar(key, learned)
            polar = polar_manager.active_polar  # activate for next startup
            logger.info("Auto-activated learned polar for %s", key)
    ...
```

Note: `polar` here is the module-level global in `main.py` — since both callsites are inside functions defined in the `main` module, direct assignment to `polar` updates the module global (no `import aquarela.main` needed, unlike the API endpoints which live in a different module).

Key details:
- Use `polar_learners[key]` (the dict), not the `polar_learner` convenience alias which may be stale if sail config changed mid-session
- `flush()` is called before `rebuild()` at session-end; `rebuild()` also calls `flush()` internally, so the double-call is harmless (buffer empty after first)
- The `/api/polar/activate` endpoint uses a different pattern (`import aquarela.main as _main; _main.polar = ...`) because it lives in `api/polar.py`. The main.py callsites can assign `polar` directly

### Scope

Rebuild runs only for the **active sail config** at session end. Other sail configs are unaffected — they rebuild when they next accumulate data and a session ends while they're active.

### Error Handling

- If `rebuild()` fails or returns None (not enough data): log info, keep current polar
- If `set_polar()` fails: log error, keep current polar
- No user-facing error — the system degrades silently to the previous polar

### Existing Filters (unchanged)

All sample filters remain as-is:

- Maneuver rejection (+ 15s cooldown)
- BSP range: 1.5–20 kt
- TWS range: 4–20 kt
- TWA minimum: 25°
- TWS stability: < 2 kt variation in 5s window
- Sensor freshness: < 2s age
- Source: never simulator/interactive
- Per-session `polar_included` flag

Rebuild aggregation also unchanged:

- 95th percentile per bin
- Minimum 50 samples per bin
- Weighted merge with base (max weight 0.9)

### PolarPage Changes

The REBUILD and ATTIVA buttons move into a collapsible "Manuale" section at the bottom of the page. Add a status line above the coverage grid: "Ultimo rebuild: {timestamp}" so the user knows the auto-system is working. The page's primary purpose becomes viewing coverage and managing session inclusion.

---

## 2. Diff Heatmap View (Frontend — PolarDiagramPage)

### Current State

PolarDiagramPage already has:
- Toggle between BASE / APPRESA / ATTIVA views
- A `cellDiff(tws, twa)` function computing `learned − base`
- Inline diff display: small "+0.1" / "−0.2" text below the BSP value in green/red
- Live wind highlight (closest TWS column + TWA row)

The API `GET /api/polar/diagram` returns `base_curves`, `learned_curves`, `base_targets`, `learned_targets`, `has_learned`, `sail_config`. No backend changes needed.

### What's New

Add a fourth toggle button **DIFF** alongside the existing BASE / APPRESA / ATTIVA. When selected:

- Each cell shows **only** the delta `learned − base` (no BSP value)
- Text: delta with sign, e.g. "+0.3", "−0.1", rounded to 1 decimal
- **Background color** (not cell opacity — text must stay fully readable on cockpit screen):
  - Positive (faster): `rgba(0, 230, 118, alpha)` (green)
  - Negative (slower): `rgba(255, 23, 68, alpha)` (red)
  - `alpha = clamp(|delta| / 0.5, 0.1, 0.5)` — 0.5 kt diff is max saturation
- Cells with no data (either base or learned missing): grey text "---", no background
- Text color: always full white for readability

The existing inline diff display (small text below BSP) remains in the ATTIVA/APPRESA views — the DIFF view is a dedicated full-grid visualization, not a replacement.

### cellDiff() Adaptation

The existing `cellDiff(tws, twa)` returns `null` for both "no data" and "diff < 0.05 kt" — these two cases can't be distinguished. For DIFF mode, add a new function `cellDiffRaw(tws, twa)` that returns:

- A number (the delta) when both base and learned have data for the cell
- `null` when either is missing

The 0.05 kt threshold is only used for the inline display (existing views). In DIFF mode, show all deltas including small ones — the color intensity already communicates magnitude.

### Toggle Implementation

Four buttons: `ATTIVA | BASE | APPRESA | DIFF`. The DIFF button only appears when `data.has_learned` is true (same condition as APPRESA). Active button uses accent color (existing pattern).

---

## What's NOT Changing

- Sample collection pipeline (PolarLearner.update) — unchanged
- Stability filters and thresholds — unchanged
- Database schema (polar_samples, polar_learned) — unchanged
- Snapshot saving — unchanged (rebuild already saves snapshots)
- Manual session exclusion (polar_included flag) — unchanged
- API endpoints — unchanged (no new endpoints)
- RegattaPage and other navigation pages — unchanged
