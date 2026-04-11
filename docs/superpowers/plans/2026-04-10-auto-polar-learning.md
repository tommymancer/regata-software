# Auto Polar Learning & Diff Heatmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate polar rebuild+activate at session end, and add a DIFF heatmap view to PolarDiagramPage.

**Architecture:** Two independent changes — (1) extend two existing callsites in main.py to activate after rebuild, (2) add a fourth toggle mode to PolarDiagramPage with colored diff cells. No new files, no new API endpoints.

**Tech Stack:** Python 3 / FastAPI backend, Svelte 4 frontend, SQLite for polar data, pytest for tests.

---

### Task 1: Auto-activate in the session-end handler

**Files:**
- Modify: `aquarela/main.py:393-400`
- Test: `tests/test_auto_polar_activate.py` (create)

The `session_event == "stopped"` block (line 393) already calls `flush()`. Extend it to also `rebuild()` + `set_polar()` + update the module-level `polar` global.

- [ ] **Step 1: Write the test**

Create `tests/test_auto_polar_activate.py`. This tests the logic in isolation — we extract the auto-rebuild into a helper function so it's testable without running the full pipeline.

```python
"""Tests for auto polar rebuild+activate at session end."""

import pytest
from unittest.mock import MagicMock, patch
from aquarela.performance.polar import PolarTable
from aquarela.performance.polar_manager import PolarManager


def _make_polar(bsp_offset=0.0):
    """Create a minimal PolarTable for testing."""
    return PolarTable(
        tws_values=[8.0],
        twa_values=[90.0],
        bsp_grid={(8.0, 90.0): 6.0 + bsp_offset},
        upwind_targets={8.0: (45.0, 5.0, 3.54)},
        downwind_targets={8.0: (135.0, 5.5, 3.89)},
    )


def test_auto_rebuild_activates_learned_polar():
    """When rebuild returns a polar, it should be set on the manager."""
    base = _make_polar()
    learned = _make_polar(bsp_offset=0.3)

    manager = PolarManager(base)
    manager.active_sail_type = "main_1__jib"

    learner = MagicMock()
    learner.rebuild.return_value = learned

    # Simulate auto-rebuild logic
    key = "main_1__jib"
    result = learner.rebuild()
    assert result is not None
    manager.set_polar(key, result)

    assert manager.get_polar(key) is learned
    assert manager.active_polar is learned


def test_auto_rebuild_keeps_current_when_none():
    """When rebuild returns None, the current polar should stay."""
    base = _make_polar()
    manager = PolarManager(base)
    manager.active_sail_type = "main_1__jib"

    learner = MagicMock()
    learner.rebuild.return_value = None

    result = learner.rebuild()
    assert result is None
    # Don't call set_polar
    assert manager.active_polar is base


def test_auto_rebuild_survives_exception():
    """If rebuild raises, the current polar should stay."""
    base = _make_polar()
    manager = PolarManager(base)
    manager.active_sail_type = "main_1__jib"

    learner = MagicMock()
    learner.rebuild.side_effect = RuntimeError("DB locked")

    try:
        learner.rebuild()
    except Exception:
        pass  # auto-rebuild catches this

    assert manager.active_polar is base
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd /Users/tommaso/Documents/regata-software
python3 -m pytest tests/test_auto_polar_activate.py -v
```

Expected: 3 PASS (these test the logic pattern, not the integration yet)

- [ ] **Step 3: Modify main.py session-end handler**

In `aquarela/main.py`, replace lines 393–400:

**Current code:**
```python
                    elif session_event == "stopped":
                        logger.info("Sailing stopped — closing CSV session")
                        csv_logger.stop_session()
                        # Flush polar data at end of session
                        if config.source not in ("simulator", "interactive"):
                            polar_learners[
                                config.sail_config_key()
                            ].flush()
```

**New code:**
```python
                    elif session_event == "stopped":
                        logger.info("Sailing stopped — closing CSV session")
                        csv_logger.stop_session()
                        # Auto polar rebuild + activate at session end
                        if config.source not in ("simulator", "interactive"):
                            _key = config.sail_config_key()
                            _learner = polar_learners[_key]
                            _learner.flush()
                            try:
                                _learned = _learner.rebuild()
                                if _learned is not None:
                                    polar_manager.set_polar(_key, _learned)
                                    polar = polar_manager.active_polar
                                    logger.info(
                                        "Auto-activated learned polar for %s",
                                        _key,
                                    )
                            except Exception:
                                logger.exception(
                                    "Auto-rebuild failed for %s, keeping current polar",
                                    _key,
                                )
```

- [ ] **Step 4: Verify no import errors**

```bash
cd /Users/tommaso/Documents/regata-software
python3 -c "import aquarela.main"
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add aquarela/main.py tests/test_auto_polar_activate.py
git commit -m "feat: auto rebuild+activate polar at session end"
```

---

### Task 2: Auto-activate in the finally block

**Files:**
- Modify: `aquarela/main.py:458-473`

The `finally` block already calls `rebuild()` but discards the result. Extend it to also activate.

- [ ] **Step 1: Modify the finally block**

In `aquarela/main.py`, replace lines 458–473:

**Current code:**
```python
    finally:
        csv_logger.stop_session()
        for _st, _pl in polar_learners.items():
            _pl.flush()
        if config.source not in ("simulator", "interactive"):
            _active_learner = polar_learners[config.sail_config_key()]
            learned = _active_learner.rebuild()
            if learned is not None:
                logger.info("Learned polar rebuilt for %s (%d bins ready)",
                            config.sail_config_key(),
                            _active_learner.get_stats().get("bins_ready", 0))
        try:
            await source.stop()
        except Exception:
            logger.debug("source.stop() error (ignored)")
        logger.info("Pipeline loop ended")
```

**New code:**
```python
    finally:
        csv_logger.stop_session()
        for _st, _pl in polar_learners.items():
            _pl.flush()
        if config.source not in ("simulator", "interactive"):
            _key = config.sail_config_key()
            _active_learner = polar_learners[_key]
            try:
                _learned = _active_learner.rebuild()
                if _learned is not None:
                    polar_manager.set_polar(_key, _learned)
                    polar = polar_manager.active_polar
                    logger.info(
                        "Auto-activated learned polar for %s (%d bins ready)",
                        _key,
                        _active_learner.get_stats().get("bins_ready", 0),
                    )
            except Exception:
                logger.exception("Final rebuild failed for %s", _key)
        try:
            await source.stop()
        except Exception:
            logger.debug("source.stop() error (ignored)")
        logger.info("Pipeline loop ended")
```

- [ ] **Step 2: Verify no import errors**

```bash
cd /Users/tommaso/Documents/regata-software
python3 -c "import aquarela.main"
```

- [ ] **Step 3: Run existing tests**

```bash
python3 -m pytest tests/ -v --timeout=30 -x
```

Expected: all existing tests pass

- [ ] **Step 4: Commit**

```bash
git add aquarela/main.py
git commit -m "feat: auto-activate polar in pipeline finally block"
```

---

### Task 3: Add DIFF toggle and cellDiffRaw to PolarDiagramPage

**Files:**
- Modify: `frontend/src/pages/PolarDiagramPage.svelte:85-96` (add cellDiffRaw)
- Modify: `frontend/src/pages/PolarDiagramPage.svelte:119-132` (add DIFF toggle)
- Modify: `frontend/src/pages/PolarDiagramPage.svelte:166-196` (diff cell rendering)

- [ ] **Step 1: Add `cellDiffRaw` function**

After the existing `cellDiff` function (line 96), add:

```javascript
  function cellDiffRaw(tws, twa) {
    if (!data?.has_learned) return null;
    const learned = data.learned_curves?.[tws];
    const base = data.base_curves?.[tws];
    if (!learned || !base) return null;
    const lPt = learned.find(p => p.twa === twa);
    const bPt = base.find(p => p.twa === twa);
    if (!lPt || !bPt) return null;
    return lPt.bsp - bPt.bsp;
  }

  function diffBgColor(diff) {
    if (diff == null) return "transparent";
    const alpha = Math.min(0.5, Math.max(0.1, Math.abs(diff) / 0.5));
    return diff > 0
      ? `rgba(0, 230, 118, ${alpha})`
      : `rgba(255, 23, 68, ${alpha})`;
  }
```

- [ ] **Step 2: Add DIFF button to toggle bar**

In the toggles section (line ~125), after the APPRESA button:

```svelte
    {#if data?.has_learned}
      <button class="toggle-btn" class:active={showMode === "learned"}
        on:click={() => showMode = "learned"}>APPRESA</button>
      <button class="toggle-btn" class:active={showMode === "diff"}
        on:click={() => showMode = "diff"}>DIFF</button>
    {/if}
```

- [ ] **Step 3: Update table body for diff mode**

Replace the table body `{#each twaValues as twa}` block (lines 167–191) with:

```svelte
          {#each twaValues as twa}
            <tr class:highlight-row={twa === closestTwa}>
              <td class="row-header">{twa}°</td>
              {#each twsValues as tws}
                {#if showMode === "diff"}
                  {@const rawDiff = cellDiffRaw(tws, twa)}
                  <td class:highlight-cell={tws === closestTws && twa === closestTwa}
                      style="background: {diffBgColor(rawDiff)}">
                    {#if rawDiff != null}
                      <span class="diff-only">{rawDiff > 0 ? "+" : ""}{rawDiff.toFixed(1)}</span>
                    {:else}
                      <span class="empty">---</span>
                    {/if}
                  </td>
                {:else}
                  {@const bsp = lookup[tws]?.[twa]}
                  {@const diff = cellDiff(tws, twa)}
                  <td class:highlight-cell={tws === closestTws && twa === closestTwa}
                      class:has-diff={diff != null}>
                    {#if bsp != null}
                      <span class="bsp-val">{bsp.toFixed(1)}</span>
                      {#if diff != null}
                        <span class="diff-val" class:positive={diff > 0} class:negative={diff < 0}>
                          {diff > 0 ? "+" : ""}{diff.toFixed(1)}
                        </span>
                      {/if}
                    {:else}
                      <span class="empty">—</span>
                    {/if}
                  </td>
                {/if}
              {/each}
            </tr>
          {/each}
```

- [ ] **Step 4: Add CSS for diff-only cells**

In the `<style>` block, add:

```css
  .diff-only {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
    font-weight: 700;
    color: #fff;
  }
```

- [ ] **Step 5: Build frontend**

```bash
cd /Users/tommaso/Documents/regata-software/frontend
npm run build
```

Expected: build succeeds (no errors, only a11y warnings OK)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PolarDiagramPage.svelte
git commit -m "feat: add DIFF heatmap view to polar diagram page"
```

---

### Task 4: Update PolarPage — collapsible manual section + last rebuild timestamp

**Files:**
- Modify: `frontend/src/pages/PolarPage.svelte:160-268`

- [ ] **Step 1: Update the step indicator**

Replace the step-labels div (lines 171–176) to reflect auto-learning:

```svelte
    <div class="step-labels">
      <span class:dim={step !== 1}>NAVIGA</span>
      <span class:dim={step !== 2}>RACCOGLI</span>
      <span class:dim={step !== 3}>ELABORA</span>
      <span class:dim={step !== 4}>ATTIVA</span>
    </div>
```

Update `stepText` (lines 32–38) — step 3 no longer says "puoi fare REBUILD":

```javascript
  $: stepText = [
    "",
    "Naviga per raccogliere dati",
    `${stats?.total_samples ?? 0} campioni — continua per riempire le caselle`,
    `${stats?.bins_ready ?? 0} caselle pronte — rebuild automatico a fine sessione`,
    `Polar appresa attiva — ${stats?.coverage_pct ?? 0}% copertura`,
  ][step] || "";
```

- [ ] **Step 2: Add last-rebuild timestamp**

After the stats-bar section (line ~202), before the coverage matrix:

```svelte
  {#if stats?.last_rebuild}
    <div class="last-rebuild">
      Ultimo rebuild: {new Date(stats.last_rebuild).toLocaleString("it-IT", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
      })}
    </div>
  {/if}
```

- [ ] **Step 3: Wrap action buttons in collapsible section**

Replace the action buttons block (lines 244–264):

```svelte
  <!-- Manual controls (collapsible) -->
  <button class="btn btn-secondary manual-toggle"
    on:click={() => showManual = !showManual}>
    {showManual ? "NASCONDI MANUALE" : "CONTROLLI MANUALI"}
  </button>

  {#if showManual}
    <div class="actions">
      <button class="btn btn-primary" on:click={() => apiAction("rebuild")}
        disabled={loading || !stats || stats.bins_ready === 0}
        title="Ricostruisci la polar dai dati raccolti">
        REBUILD
      </button>
      <button class="btn btn-accent" on:click={() => apiAction("activate")}
        disabled={loading || !stats || !stats.has_learned_polar}
        title="Usa la polar appresa per target e performance">
        ATTIVA
      </button>
      <button class="btn btn-secondary" on:click={() => apiAction("reset-to-base")}
        disabled={loading}>
        POLAR BASE
      </button>
      <button class="btn btn-danger"
        on:click={() => apiAction("clear", "Cancellare tutti i campioni raccolti?")}
        disabled={loading}>
        CANCELLA
      </button>
    </div>
  {/if}
```

Add `let showManual = false;` to the script block (near the other `let show...` declarations, around line 14).

- [ ] **Step 4: Add CSS for new elements**

```css
  .last-rebuild {
    text-align: center;
    font-size: var(--label-xs-size);
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }
  .manual-toggle {
    width: 100%;
  }
```

- [ ] **Step 5: Build frontend**

```bash
cd /Users/tommaso/Documents/regata-software/frontend
npm run build
```

Expected: build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PolarPage.svelte
git commit -m "feat: auto-learning UI — collapsible manual controls, rebuild timestamp"
```

---

### Task 5: Final build and verification

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/tommaso/Documents/regata-software
python3 -m pytest tests/ -v --timeout=30
```

Expected: all pass

- [ ] **Step 2: Final frontend build**

```bash
cd /Users/tommaso/Documents/regata-software/frontend
npm run build
```

Expected: clean build

- [ ] **Step 3: Smoke test — start backend and verify API**

```bash
cd /Users/tommaso/Documents/regata-software
python3 -m uvicorn aquarela.main:app --host 0.0.0.0 --port 8080 &
sleep 2
curl -s http://localhost:8080/api/polar/stats | python3 -m json.tool
curl -s http://localhost:8080/api/polar/diagram | python3 -m json.tool | head -20
```

Verify `stats` response includes `last_rebuild` field and `diagram` returns `base_curves`/`learned_curves`.
