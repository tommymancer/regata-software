# Unified Sail Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the two parallel sail selection systems (old 4-type polar learning vs new main+headsail upwash) into a single main+headsail selection that drives both upwash correction and polar learning.

**Architecture:** Replace the old `sail_type` string ("racing_white", "racing_gennaker", etc.) with the `sail_config_key` derived from `active_main` + `active_headsail` (e.g. "main_1__genoa"). PolarManager, PolarLearner, the DB schema, the API, and the frontend SailSelector all switch to this unified key. The upwash system already uses this key and needs no changes.

**Tech Stack:** Python 3.9, FastAPI, Svelte, SQLite

---

## Background

The project currently has **two independent sail selection systems**:

| System | Keys | Drives | UI |
|--------|------|--------|----|
| **Old (polar learning)** | 4 strings: `racing_white`, `racing_gennaker`, `racing_gennaker_runner`, `training_white` | `PolarManager`, `PolarLearner`, DB `polar_samples.sail_type` | `SailSelector.svelte` (2x3 grid) |
| **New (upwash)** | 6 keys: `main_N__category` (e.g. `main_1__genoa`) | `UpwashTableSet`, upwash learning | No UI (API-only `/api/sails`) |

This means the user must remember to switch both systems independently, and the categories don't even match. The fix is to **kill the old system** and make everything use the `sail_config_key`.

### Sail inventory (from config)

```json
{
  "mains": ["main_1", "main_2"],
  "headsails": {
    "jib": ["jib_1"],
    "genoa": ["genoa_1"],
    "gennaker": ["gennaker_1", "gennaker_2"]
  }
}
```

The `sail_config_key()` method derives `"{active_main}__{headsail_category}"` — e.g. `"main_1__genoa"`.

### What changes

1. **`SAIL_TYPES` dict in `polar_manager.py`** → replace with `SAIL_CONFIG_KEYS` from `upwash_table.py`
2. **`PolarManager`** → keyed by `sail_config_key` instead of `sail_type`
3. **`PolarLearner`** → `sail_type` param renamed conceptually, uses config keys
4. **`config.sail_type`** → removed, replaced by existing `active_main`/`active_headsail`
5. **DB `polar_samples` / `polar_learned`** → `sail_type` column keeps working, just stores new key values
6. **`BoatState.sail_type`** → removed (reuse existing `active_sail_config` field at line 52)
7. **API `/api/sail-type(s)`** → removed, unified with `/api/sails`
8. **`SailSelector.svelte`** → two-step picker (main + headsail) calling `/api/sails`
9. **`PolarPage.svelte` / `PolarDiagramPage.svelte`** → read from unified system

### What does NOT change

- `UpwashTableSet`, `UpwashTable`, upwash learning — already use `sail_config_key`
- `apply_wind_correction`, `compute_true_wind` — no sail awareness
- The physical sail inventory in config
- `aquarela/api/trim.py` / `aquarela/training/trim_guide.py` — `get_trim_guide()` uses `if "gennaker" in sail_type` which works with the new keys (e.g. `main_1__gennaker` contains `"gennaker"`)
- `polar_learner.py` internal `_sail_type` param name and DB column name `sail_type` — intentionally kept for backward compatibility, just stores new key values

### Upwind sharing logic

The current polar learner shares upwind bins (TWA < 90) across all sail types because headsail type only matters downwind. This logic is preserved — the SQL filter `WHERE ((twa_bin < 90) OR (twa_bin >= 90 AND sail_type = ?))` still works, just with config keys instead of old type names.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `aquarela/performance/polar_manager.py` | Modify | Replace `SAIL_TYPES` with config-key-based approach, add Italian labels |
| `aquarela/performance/polar_learner.py` | Modify | Accept config key as `sail_type` (param name unchanged for DB compat) |
| `aquarela/config.py` | Modify | Remove `sail_type` field |
| `aquarela/pipeline/state.py` | Modify | Remove `sail_type` field (reuse existing `active_sail_config`) |
| `aquarela/api/polar.py` | Modify | Replace `SAIL_TYPES` import with `SAIL_CONFIGS`, update labels |
| `aquarela/main.py` | Modify | Remove old `/api/sail-type(s)`, unify polar init with config keys |
| `aquarela/api/sails.py` | Modify | Extend to also switch polar learner/manager when sails change |
| `aquarela/logging/db.py` | Modify | Add migration for old sail_type values |
| `frontend/src/components/SailSelector.svelte` | Rewrite | Two-step picker: main + headsail |
| `frontend/src/stores/boat.js` | Modify | Replace `sailType` derived store |
| `frontend/src/pages/PolarPage.svelte` | Modify | Use unified sail config |
| `frontend/src/pages/PolarDiagramPage.svelte` | Modify | Use unified sail config |
| `tests/test_polar_manager.py` | Modify | Update for new keys |
| `tests/test_polar_learner.py` | Modify | Update for new keys |
| `tests/test_config.py` | Modify | Remove `sail_type` assertions |

---

## Task 1: PolarManager — Switch to Config Keys

**Files:**
- Modify: `aquarela/performance/polar_manager.py`
- Test: `tests/test_polar_manager.py`

Replace `SAIL_TYPES` dict with a new `SAIL_CONFIGS` dict keyed by config keys, with Italian labels for the UI.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_polar_manager.py — add/replace tests

from aquarela.performance.polar_manager import SAIL_CONFIGS, PolarManager

class TestSailConfigs:
    def test_has_six_keys(self):
        assert len(SAIL_CONFIGS) == 6

    def test_keys_match_upwash(self):
        from aquarela.pipeline.upwash_table import SAIL_CONFIG_KEYS
        assert set(SAIL_CONFIGS.keys()) == set(SAIL_CONFIG_KEYS)

    def test_each_has_label_and_short(self):
        for key, info in SAIL_CONFIGS.items():
            assert "label" in info
            assert "short" in info

class TestPolarManagerConfigKeys:
    def test_init_creates_six_entries(self):
        pm = PolarManager()
        for key in SAIL_CONFIGS:
            # All keys must be present (returns base_polar or None, no KeyError)
            assert key in pm._polars

    def test_set_active_valid(self):
        pm = PolarManager()
        pm.active_sail_type = "main_1__genoa"
        assert pm.active_sail_type == "main_1__genoa"

    def test_set_active_invalid_raises(self):
        import pytest
        pm = PolarManager()
        with pytest.raises(ValueError):
            pm.active_sail_type = "racing_white"  # old key should fail
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_polar_manager.py -v`

- [ ] **Step 3: Implement**

Replace `polar_manager.py`:

```python
"""PolarManager — holds one PolarTable per sail configuration.

Manages 6 independent polar tables (2 mains × 3 headsail categories).
All start from the same base polar and diverge as real sailing data is learned.
"""

from typing import Dict, Optional

from ..pipeline.upwash_table import SAIL_CONFIG_KEYS
from .polar import PolarTable

SAIL_CONFIGS: Dict[str, dict] = {
    "main_1__jib":       {"label": "Randa 1 + Fiocco",     "short": "R1/F"},
    "main_1__genoa":     {"label": "Randa 1 + Genoa",      "short": "R1/G"},
    "main_1__gennaker":  {"label": "Randa 1 + Gennaker",   "short": "R1/GK"},
    "main_2__jib":       {"label": "Randa 2 + Fiocco",     "short": "R2/F"},
    "main_2__genoa":     {"label": "Randa 2 + Genoa",      "short": "R2/G"},
    "main_2__gennaker":  {"label": "Randa 2 + Gennaker",   "short": "R2/GK"},
}


class PolarManager:
    """Holds a dict of PolarTable for all 6 sail configurations."""

    def __init__(self, base_polar: Optional[PolarTable] = None) -> None:
        self._base_polar = base_polar
        self._active_sail_type: str = "main_1__genoa"
        self._polars: Dict[str, Optional[PolarTable]] = {
            key: base_polar for key in SAIL_CONFIGS
        }

    @property
    def active_sail_type(self) -> str:
        return self._active_sail_type

    @active_sail_type.setter
    def active_sail_type(self, sail_type: str) -> None:
        if sail_type not in SAIL_CONFIGS:
            raise ValueError(f"Unknown sail config: {sail_type}")
        self._active_sail_type = sail_type

    @property
    def active_polar(self) -> Optional[PolarTable]:
        return self._polars.get(self._active_sail_type)

    @property
    def base_polar(self) -> Optional[PolarTable]:
        return self._base_polar

    def get_polar(self, sail_type: str) -> Optional[PolarTable]:
        return self._polars.get(sail_type)

    def set_polar(self, sail_type: str, polar: PolarTable) -> None:
        if sail_type not in SAIL_CONFIGS:
            raise ValueError(f"Unknown sail config: {sail_type}")
        self._polars[sail_type] = polar

    def reset_to_base(self, sail_type: str) -> None:
        if sail_type not in SAIL_CONFIGS:
            raise ValueError(f"Unknown sail config: {sail_type}")
        self._polars[sail_type] = self._base_polar
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_polar_manager.py -v`

- [ ] **Step 5: Commit**

```bash
git add aquarela/performance/polar_manager.py tests/test_polar_manager.py
git commit -m "refactor: PolarManager uses sail config keys instead of sail types"
```

---

## Task 2: Config — Remove `sail_type`, Add Labels Helper

**Files:**
- Modify: `aquarela/config.py:70` (remove `sail_type`)
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py — add

def test_no_sail_type_field():
    """sail_type field should no longer exist."""
    cfg = AquarelaConfig()
    assert not hasattr(cfg, "sail_type")

def test_sail_config_key_default():
    cfg = AquarelaConfig()
    assert cfg.sail_config_key() == "main_1__genoa"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_config.py::test_no_sail_type_field -v`

- [ ] **Step 3: Implement**

In `aquarela/config.py`:

**a) Remove field** — delete line 70:
```python
sail_type: str = "racing_white"
```

**b) Update `load()`** — remove `sail_type=raw.get("sail_type", "racing_white"),` from the `cls(...)` call (line ~114). Add backward-compat mapping BEFORE the `cls(...)` call:

```python
# Backward compat: if old sail_type present but no active_main, map to new fields
_old_st = raw.get("sail_type")
_default_main = "main_1"
_default_head = "genoa_1"
if _old_st and "active_main" not in raw:
    _mapping = {
        "training_white": ("main_1", "genoa_1"),
        "racing_white": ("main_1", "genoa_1"),
        "racing_gennaker": ("main_1", "gennaker_1"),
        "racing_gennaker_runner": ("main_1", "gennaker_1"),
    }
    _default_main, _default_head = _mapping.get(_old_st, ("main_1", "genoa_1"))
```

Then in the `cls(...)` call, use these defaults:
```python
active_main=raw.get("active_main", _default_main),
active_headsail=raw.get("active_headsail", _default_head),
```

**c) Update `save()`** — delete line 155:
```python
"sail_type": self.sail_type,
```
This line would raise `AttributeError` since the field no longer exists.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
git add aquarela/config.py tests/test_config.py
git commit -m "refactor: remove sail_type from config, use active_main/active_headsail only"
```

---

## Task 3: BoatState — Remove `sail_type`, Reuse `active_sail_config`

**Files:**
- Modify: `aquarela/pipeline/state.py:102`
- Modify: all files referencing `state.sail_type` (grep to find them)

`BoatState` already has `active_sail_config` at line 52 (added by the upwash implementation). The pipeline already sets `state.active_sail_config = _sail_key` at `main.py:284`. The old `sail_type` field at line 102 is redundant — remove it and point all consumers to `active_sail_config`.

- [ ] **Step 1: Find all references**

Run: `grep -rn "\.sail_type" aquarela/ tests/ frontend/src/ --include="*.py" --include="*.svelte" --include="*.js"`

- [ ] **Step 2: Remove `sail_type` from BoatState**

In `aquarela/pipeline/state.py`, **delete** line 102:
```python
sail_type: str = "racing_white"             # active sail type key
```

The existing `active_sail_config` field (line 52) replaces it.

- [ ] **Step 3: Update all Python references to `state.sail_type`**

In `aquarela/main.py`:
- **Delete** line 294: `state.sail_type = polar_manager.active_sail_type` (redundant — `state.active_sail_config` is already set at line 284)
- Replace every `current_state.sail_type` with `current_state.active_sail_config`
- In the old `POST /api/sail-type` handler (being removed in Task 4): `current_state.sail_type = new_st` → delete along with the endpoint

- [ ] **Step 4: Update frontend store**

In `frontend/src/stores/boat.js`, line 55, replace:
```javascript
export const sailType = derived(boatState, ($s) => $s?.sail_type ?? "racing_white");
```
with:
```javascript
export const sailConfig = derived(boatState, ($s) => $s?.active_sail_config ?? "main_1__genoa");
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/ -v -k "not test_polar_learner and not test_simulator"`

- [ ] **Step 6: Commit**

```bash
git add aquarela/pipeline/state.py aquarela/main.py frontend/src/stores/boat.js
git commit -m "refactor: remove BoatState.sail_type, use active_sail_config"
```

---

## Task 4: Main.py — Unify Polar Init and Remove Old API

**Files:**
- Modify: `aquarela/main.py:123-137` (polar init), lines 735-773 (old API)

- [ ] **Step 1: Update polar initialization**

Replace lines 123-137 in main.py:

```python
from .performance.polar_manager import SAIL_CONFIGS, PolarManager

# Polar manager (6 sail configs, all starting from the same base)
polar_manager: PolarManager = PolarManager(base_polar=_base_polar)
polar_manager.active_sail_type = config.sail_config_key()

polar: PolarTable | None = polar_manager.active_polar

# Polar learning: one PolarLearner per sail config
polar_learners: dict[str, PolarLearner] = {
    key: PolarLearner(base_polar=_base_polar, hz=config.sample_rate_hz, sail_type=key)
    for key in SAIL_CONFIGS
}
polar_learner: PolarLearner = polar_learners[config.sail_config_key()]
```

- [ ] **Step 2: Update pipeline loop references**

- Every `polar_learners[polar_manager.active_sail_type]` reference in the pipeline loop should use `config.sail_config_key()` as the dict key.
- **Delete** `state.sail_type = polar_manager.active_sail_type` (line ~294) — the `state.active_sail_config` field is already set at line 284 by the upwash integration.

- [ ] **Step 3: Remove old API endpoints**

Delete the three endpoints:
- `GET /api/sail-types` (line ~735)
- `GET /api/sail-type` (line ~745)
- `POST /api/sail-type` (line ~753)

These are replaced by the existing `/api/sails` router.

- [ ] **Step 4: Remove `SAIL_TYPES` import**

Change import from:
```python
from .performance.polar_manager import SAIL_TYPES, PolarManager
```
to:
```python
from .performance.polar_manager import SAIL_CONFIGS, PolarManager
```

- [ ] **Step 5: Run server smoke test**

Run: `python3 -c "from aquarela.main import app; print('OK')"`

- [ ] **Step 6: Commit**

```bash
git add aquarela/main.py
git commit -m "refactor: unify polar init with sail config keys, remove old sail-type API"
```

---

## Task 5: Sails API — Extend to Switch Polar Manager/Learner

**Files:**
- Modify: `aquarela/api/sails.py`

When the user changes sails via `POST /api/sails`, the handler must also switch the active polar and polar learner. Currently it only saves config.

- [ ] **Step 1: Update `POST /api/sails`**

```python
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
```

- [ ] **Step 2: Extend `GET /api/sails` to include labels**

```python
@router.get("")
async def get_sails():
    """Return current sail configuration, active selection, and labels."""
    from aquarela.main import config, upwash_tables
    from aquarela.performance.polar_manager import SAIL_CONFIGS
    key = config.sail_config_key()
    info = SAIL_CONFIGS.get(key, {})
    return {
        "sails": config.sails,
        "active_main": config.active_main,
        "active_headsail": config.active_headsail,
        "active_config_key": key,
        "label": info.get("label", key),
        "short": info.get("short", key),
        "all_configs": [
            {"key": k, **v} for k, v in SAIL_CONFIGS.items()
        ],
    }
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest tests/ -v -k "sails"`

- [ ] **Step 4: Commit**

```bash
git add aquarela/api/sails.py
git commit -m "feat: POST /api/sails also switches polar manager and learner"
```

---

## Task 6: DB Migration — Map Old Sail Type Values

**Files:**
- Modify: `aquarela/logging/db.py`

Add a migration that maps old `sail_type` values in `polar_samples` and `polar_learned` to the new config keys. This preserves existing learned data.

- [ ] **Step 1: Add migration**

In `db.py`, after existing migrations, add:

```python
# Migration: map old sail_type values to new config keys
_OLD_TO_NEW = {
    "training_white": "main_1__genoa",
    "racing_white": "main_1__genoa",
    "racing_gennaker": "main_1__gennaker",
    "racing_gennaker_runner": "main_1__gennaker",
}
for _old, _new in _OLD_TO_NEW.items():
    try:
        conn.execute(
            "UPDATE polar_samples SET sail_type = ? WHERE sail_type = ?",
            (_new, _old),
        )
        conn.execute(
            "UPDATE polar_learned SET sail_type = ? WHERE sail_type = ?",
            (_new, _old),
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
```

Note: `racing_white` and `training_white` both map to `main_1__genoa` (white sails = main + genoa, most common). `racing_gennaker` and `racing_gennaker_runner` both map to `main_1__gennaker`. The user hasn't actually learned separate polars for main_2, so this is the best mapping.

- [ ] **Step 2: Commit**

```bash
git add aquarela/logging/db.py
git commit -m "feat: DB migration maps old sail_type values to new config keys"
```

---

## Task 7: Frontend — Rewrite SailSelector

**Files:**
- Rewrite: `frontend/src/components/SailSelector.svelte`
- Modify: `frontend/src/stores/boat.js`

Replace the old 4-button grid with a two-step picker that calls `/api/sails`.

- [ ] **Step 1: Update the store**

In `frontend/src/stores/boat.js`:
```javascript
// Replace sailType with sailConfig (reads from active_sail_config field in BoatState)
export const sailConfig = derived(boatState, ($s) => $s?.active_sail_config ?? "main_1__genoa");
```

- [ ] **Step 2: Rewrite SailSelector.svelte**

The new component:
- Shows the short label of the active config (e.g. "R1/G") as a button
- On tap, opens a modal with two sections: RANDA (main) and PRUA (headsail)
- Each section shows buttons for available options
- Active selections highlighted
- On change, calls `POST /api/sails` with updated `active_main` and/or `active_headsail`
- Updates the store optimistically

```svelte
<!--
  SailSelector — Two-step sail picker (main + headsail).
  Calls POST /api/sails to switch both upwash and polar systems.
-->
<script>
  import { boatState } from "../stores/boat.js";

  let open = false;
  let sailData = null;
  let loading = false;

  $: configKey = $boatState?.active_sail_config ?? "main_1__genoa";
  $: shortLabel = sailData?.short ?? configKey;

  async function openPicker() {
    open = true;
    try {
      const res = await fetch("/api/sails");
      sailData = await res.json();
    } catch (e) {
      sailData = null;
    }
  }

  async function pickMain(main) {
    if (!sailData || main === sailData.active_main) return;
    loading = true;
    try {
      const res = await fetch("/api/sails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_main: main }),
      });
      if (res.ok) {
        const data = await res.json();
        sailData = { ...sailData, active_main: data.active_main, active_config_key: data.active_config_key };
        boatState.update(s => s ? { ...s, active_sail_config: data.active_config_key } : s);
        // Re-fetch to update labels
        const r2 = await fetch("/api/sails");
        sailData = await r2.json();
      }
    } catch (e) { /* ignore */ }
    loading = false;
  }

  async function pickHeadsail(headsail) {
    if (!sailData || headsail === sailData.active_headsail) return;
    loading = true;
    try {
      const res = await fetch("/api/sails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_headsail: headsail }),
      });
      if (res.ok) {
        const data = await res.json();
        sailData = { ...sailData, active_headsail: data.active_headsail, active_config_key: data.active_config_key };
        boatState.update(s => s ? { ...s, active_sail_config: data.active_config_key } : s);
        const r2 = await fetch("/api/sails");
        sailData = await r2.json();
      }
    } catch (e) { /* ignore */ }
    loading = false;
  }

  // Build flat headsail list from the nested config
  $: allHeadsails = sailData ? Object.entries(sailData.sails?.headsails ?? {}).flatMap(
    ([cat, names]) => names.map(n => ({ name: n, category: cat }))
  ) : [];
</script>

<button class="sail-btn" on:click={openPicker} title="Cambia vele">
  {shortLabel}
</button>

{#if open}
  <div class="overlay" on:click|self={() => (open = false)}>
    <div class="picker">
      <div class="section-title">RANDA</div>
      <div class="grid">
        {#each sailData?.sails?.mains ?? [] as main}
          <button
            class="sail-option"
            class:active={main === sailData?.active_main}
            disabled={loading}
            on:click={() => pickMain(main)}
          >
            {main.replace("_", " ").toUpperCase()}
          </button>
        {/each}
      </div>

      <div class="section-title">PRUA</div>
      <div class="grid">
        {#each allHeadsails as hs}
          <button
            class="sail-option"
            class:active={hs.name === sailData?.active_headsail}
            disabled={loading}
            on:click={() => pickHeadsail(hs.name)}
          >
            {hs.name.replace("_", " ").toUpperCase()}
            <span class="opt-label">{hs.category}</span>
          </button>
        {/each}
      </div>
    </div>
  </div>
{/if}
```

(Styles carry over from the existing component — same `.overlay`, `.picker`, `.sail-option`, `.active` classes.)

- [ ] **Step 3: Update PolarPage.svelte**

In `frontend/src/pages/PolarPage.svelte`, update any `sail_short` references. The `/api/polar/stats` endpoint will return the new short label.

- [ ] **Step 4: Update PolarDiagramPage.svelte**

The raw config key (e.g. `"main_1__genoa"`) is not human-readable for the title. Add a JS-side label map mirroring the backend `SAIL_CONFIGS`:

```javascript
import { boatState, sailConfig } from "../stores/boat.js";

// Replace the old SAIL_SHORT dict with the new config labels
const SAIL_LABELS = {
  "main_1__jib":       "R1/F",
  "main_1__genoa":     "R1/G",
  "main_1__gennaker":  "R1/GK",
  "main_2__jib":       "R2/F",
  "main_2__genoa":     "R2/G",
  "main_2__gennaker":  "R2/GK",
};
```

Replace the title line:
```svelte
<!-- OLD: -->
<h2 class="title">TABELLA POLARE — {SAIL_SHORT[$sailType] || $sailType}</h2>
<!-- NEW: -->
<h2 class="title">TABELLA POLARE — {SAIL_LABELS[$sailConfig] || $sailConfig}</h2>
```

Replace the reactive refetch trigger:
```javascript
// OLD: $: $sailType, fetchData();
// NEW: $: $sailConfig, fetchData();
```

- [ ] **Step 5: Build frontend**

Run: `cd frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SailSelector.svelte frontend/src/stores/boat.js frontend/src/pages/PolarPage.svelte frontend/src/pages/PolarDiagramPage.svelte
git commit -m "feat: unified two-step sail selector (main + headsail)"
```

---

## Task 8: Polar API — Update to Use SAIL_CONFIGS

**Files:**
- Modify: `aquarela/api/polar.py` (the actual file containing polar stats/coverage endpoints)
- Modify: `aquarela/main.py` (if any remaining `SAIL_TYPES` references exist)

The polar API endpoints are in `aquarela/api/polar.py`, NOT in `main.py`. This file imports `SAIL_TYPES` and uses it for labels in stats responses.

- [ ] **Step 1: Update `aquarela/api/polar.py`**

Replace the import:
```python
# OLD:
from ..performance.polar_manager import SAIL_TYPES
# NEW:
from ..performance.polar_manager import SAIL_CONFIGS
```

Replace all `SAIL_TYPES[...]` lookups with `SAIL_CONFIGS.get(...)`. For example:
```python
# OLD:
info = SAIL_TYPES[mgr.active_sail_type]
stats["sail_type"] = mgr.active_sail_type
stats["sail_label"] = info["label"]
stats["sail_short"] = info["short"]

# NEW:
info = SAIL_CONFIGS.get(mgr.active_sail_type, {})
stats["sail_config"] = mgr.active_sail_type
stats["sail_label"] = info.get("label", "?")
stats["sail_short"] = info.get("short", "?")
```

Also update the `/api/polar/diagram` endpoint response to use `sail_config` instead of `sail_type`.

- [ ] **Step 2: Check `main.py` for remaining `SAIL_TYPES` references**

Run: `grep -n "SAIL_TYPES" aquarela/main.py`

Replace any remaining references with `SAIL_CONFIGS`. The import at the top should already be updated from Task 4.

- [ ] **Step 3: Run full backend test suite**

Run: `python3 -m pytest tests/ -v -k "not test_simulator"`

- [ ] **Step 4: Commit**

```bash
git add aquarela/api/polar.py aquarela/main.py
git commit -m "refactor: polar API uses SAIL_CONFIGS labels"
```

---

## Task 9: Fix Polar Learner Tests

**Files:**
- Modify: `tests/test_polar_learner.py`

The existing polar learner tests have a pre-existing bug (9 bindings vs 8 columns) unrelated to this refactor. Additionally, any tests referencing `"racing_white"` need updating to `"main_1__genoa"`.

- [ ] **Step 1: Update sail_type references in tests**

Replace all `sail_type="racing_white"` with `sail_type="main_1__genoa"` in test fixtures.

- [ ] **Step 2: Fix the binding count bug**

The `polar_samples` table has 9 columns (`session_id, timestamp, tws_bin, twa_bin, bsp_kt, tws_kt, twa_deg, perf_pct, sail_type`) but `PolarLearner._buffer.append(...)` provides 9 values. Check if the DB schema is missing the `perf_pct` column (the `INSERT` specifies 9 columns but the table `CREATE` might list only 8). Add the missing column or fix the insert.

- [ ] **Step 3: Run polar learner tests**

Run: `python3 -m pytest tests/test_polar_learner.py -v`

- [ ] **Step 4: Commit**

```bash
git add tests/test_polar_learner.py aquarela/performance/polar_learner.py aquarela/logging/db.py
git commit -m "fix: polar learner tests use new config keys, fix binding count"
```

---

## Task 10: Full Integration Test

**Files:**
- Run all tests, build frontend, verify full stack

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`

Expected: all tests pass (except `test_simulator` which requires pytest-asyncio).

- [ ] **Step 2: Build frontend**

Run: `cd frontend && npm run build`

- [ ] **Step 3: Smoke test**

Run: `python3 -c "from aquarela.main import app; print('Server imports OK')"`

- [ ] **Step 4: Verify WebSocket heartbeat includes `sail_config`**

Start the server briefly and check that the heartbeat JSON includes `active_sail_config` (not `sail_type`).

- [ ] **Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore: unified sail selection — integration verified"
```
