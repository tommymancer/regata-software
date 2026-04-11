# UI Polish Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize spacing, typography, and visual consistency across the Aquarela frontend without changing layouts.

**Architecture:** Add CSS design tokens (spacing + typography scale) to App.svelte, then propagate to all components and pages. Replace fragile `:global()` overrides with component props. Add subtle value-change transitions.

**Tech Stack:** Svelte 4, CSS custom properties, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-10-ui-polish-pass-design.md`

---

### Task 1: Add CSS Design Tokens to App.svelte

**Files:**
- Modify: `frontend/src/App.svelte` (style section, `.app` rule ~line 259, `:global(.page)` rule ~line 287)

- [ ] **Step 1: Add spacing and typography tokens to `.app` rule**

In the `<style>` section of App.svelte, add these variables inside the existing `.app { ... }` rule (around line 259):

```css
.app {
  /* existing styles... */

  /* Spacing tokens — hybrid */
  --gap-compact: 6px;
  --gap-airy: 12px;
  --pad-compact: 4px;
  --pad-airy: 8px;

  /* Typography scale */
  --label-xs-size: 9px;
  --label-xs-weight: 700;
  --label-xs-spacing: 0.08em;
  --label-sm-size: 11px;
  --label-sm-weight: 700;
  --label-sm-spacing: 0.12em;
  --label-md-size: 13px;
  --label-md-weight: 800;
  --label-md-spacing: 0.12em;
}
```

- [ ] **Step 2: Update `:global(.page)` defaults**

Change the existing `:global(.page)` rule (~line 287) from hardcoded values to tokens:

```css
:global(.page) {
  padding: var(--pad-airy);
  gap: var(--gap-airy);
  /* rest stays the same */
}
```

This makes airy the default; carousel pages will override with compact.

- [ ] **Step 3: Build frontend and verify no visual regression**

```bash
cd frontend && npm run build
```

Expected: Build succeeds. No visual change yet (tokens defined but not consumed).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.svelte
git commit -m "feat(ui): add spacing and typography design tokens to App.svelte"
```

---

### Task 2: Update InstrumentField.svelte — Typography Tokens + Value Transition

**Files:**
- Modify: `frontend/src/components/InstrumentField.svelte` (styles ~lines 25-76)

- [ ] **Step 1: Replace label typography with tokens**

In the `.label` rule (~line 38), change from hardcoded values. Note: base label goes from 13px to 11px (`label-sm`) — this is intentional to create room in the compact layout. The lg/md size variants (Step 3) keep their larger sizes.

```css
/* Before */
.label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-dim);
  text-transform: uppercase;
  margin-bottom: 2px;
}

/* After */
.label {
  font-size: var(--label-sm-size);  /* 13px → 11px, intentional tightening */
  font-weight: var(--label-sm-weight);
  letter-spacing: var(--label-sm-spacing);
  color: var(--text-dim);
  text-transform: uppercase;
  margin-bottom: 2px;
}
```

- [ ] **Step 2: Replace unit typography with tokens**

In the `.unit` rule (~line 51), change. Note: base unit goes from 12px to 9px (`label-xs`) — intentional, units should be small. Size variants (Step 3) keep their larger sizes.

```css
/* Before */
.unit {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--text-dim);
  margin-top: 2px;
}

/* After */
.unit {
  font-size: var(--label-xs-size);  /* 12px → 9px, intentional shrink for units */
  font-weight: var(--label-xs-weight);
  letter-spacing: var(--label-xs-spacing);
  color: var(--text-dim);
  margin-top: 2px;
}
```

- [ ] **Step 3: Keep size-variant label overrides for lg/md**

The `.field-lg .label` (16px) and `.field-md .label` (14px) rules override the base. Keep these — only standardize weight and spacing:

```css
.field-lg .label { font-size: 16px; font-weight: var(--label-md-weight); letter-spacing: var(--label-md-spacing); }
.field-lg .unit  { font-size: 16px; }
.field-md .label { font-size: 14px; font-weight: var(--label-sm-weight); letter-spacing: var(--label-sm-spacing); }
.field-md .unit  { font-size: 14px; }
.field-sm .label { font-size: var(--label-sm-size); }
.field-sm .unit  { font-size: var(--label-xs-size); }
```

- [ ] **Step 4: Add value transition**

In the `<script>` section, add a reactive flash on value change. Important: track previous value to avoid strobing on every WebSocket tick:

```javascript
let flash = false;
let prevValue = value;
$: if (value !== prevValue) {
  prevValue = value;
  flash = true;
  setTimeout(() => flash = false, 120);
}
```

Add to the `.value` CSS rule:

```css
.value {
  /* existing styles */
  transition: opacity 0.12s ease;
}
.value.flash {
  opacity: 0.85;
}
```

In the template, add the class binding. Note: the element is a `<span>`, not `<div>`, and uses Svelte's `style:color` shorthand:

```svelte
<span class="value" class:flash style:color>{value}</span>
```

- [ ] **Step 5: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/InstrumentField.svelte
git commit -m "feat(ui): apply typography tokens and value transition to InstrumentField"
```

---

### Task 3: Update HeelGauge.svelte — Add `expanded` Prop

**Files:**
- Modify: `frontend/src/components/HeelGauge.svelte` (~lines 1-124)
- Modify: `frontend/src/pages/RegattaPage.svelte` (remove `:global()` overrides ~lines 320-343, use prop)

- [ ] **Step 1: Add `expanded` prop to HeelGauge**

In the `<script>` section, add:

```javascript
export let expanded = false;
```

In the template, add a class to the wrapper:

```svelte
<div class="heel-gauge" class:expanded>
```

- [ ] **Step 2: Add expanded styles to HeelGauge**

After the existing styles, add expanded overrides (values taken from RegattaPage's current `:global()` rules):

```css
.heel-gauge.expanded {
  max-width: 100%;
  gap: 10px;
}
.expanded .bar-bg {
  height: 28px;
  border-radius: 6px;
}
.expanded .needle {
  width: 4px;
}
.expanded .label {
  font-size: 14px;
  width: 40px;
}
.expanded .value {
  font-size: 48px;
  font-weight: 800;
  width: 80px;
}
```

- [ ] **Step 3: Remove `:global()` overrides from RegattaPage**

In RegattaPage.svelte, delete the entire block of `:global()` heel overrides (~lines 320-343):

```css
/* DELETE all of these */
.heel-section :global(.heel-gauge) { ... }
.heel-section :global(.bar-bg) { ... }
.heel-section :global(.needle) { ... }
.heel-section :global(.label) { ... }
.heel-section :global(.value) { ... }
```

- [ ] **Step 4: Pass `expanded` prop in RegattaPage template**

In RegattaPage.svelte's template, change:

```svelte
<!-- Before -->
<HeelGauge value={...} />

<!-- After -->
<HeelGauge value={...} expanded={true} />
```

- [ ] **Step 5: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/HeelGauge.svelte frontend/src/pages/RegattaPage.svelte
git commit -m "feat(ui): replace HeelGauge :global() overrides with expanded prop"
```

---

### Task 4: Update SailSelector.svelte — onMount Fetch + Full Label

**Files:**
- Modify: `frontend/src/components/SailSelector.svelte` (~lines 1-112)

- [ ] **Step 1: Add onMount import and eager fetch**

In the `<script>` section, add `onMount` import and fetch sail data immediately:

```javascript
import { onMount } from "svelte";
import { boatState } from "../stores/boat.js";

let open = false;
let sailData = null;
let loading = false;

onMount(async () => {
  try {
    const res = await fetch("/api/sails");
    sailData = await res.json();
  } catch (e) { /* ignore */ }
});
```

- [ ] **Step 2: Update button label to show full name**

Change line 13 from `sailData?.short` to `sailData?.label`:

```javascript
/* Before (line 13) */
$: shortLabel = sailData?.short ?? configKey;

/* After */
$: shortLabel = sailData?.label ?? configKey;
```

The `GET /api/sails` response includes both `short` ("R1/G") and `label` ("Randa 1 + Genoa"). The `shortLabel` variable name is kept for backward compatibility but now shows the full label. After the `onMount` fetch, the button immediately displays "Randa 1 + Genoa" instead of "main_1__genoa".

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SailSelector.svelte
git commit -m "feat(ui): show full sail label in SailSelector button"
```

---

### Task 5: Update StatusBar.svelte — Typography Tokens

**Files:**
- Modify: `frontend/src/components/StatusBar.svelte` (styles ~lines 34-88)

- [ ] **Step 1: Apply typography tokens to StatusBar labels**

Update the `.status-bar` font properties (~line 41):

```css
/* Before */
font-size: 11px;
font-weight: 600;
letter-spacing: 0.06em;

/* After */
font-size: var(--label-sm-size);
font-weight: var(--label-sm-weight);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/StatusBar.svelte
git commit -m "feat(ui): apply typography tokens to StatusBar"
```

---

### Task 6: Update RegattaPage.svelte — Compact Spacing + Typography Tokens

**Files:**
- Modify: `frontend/src/pages/RegattaPage.svelte` (styles ~lines 118-344)

Note: HeelGauge `:global()` removal was done in Task 3. This task handles spacing and typography.

- [ ] **Step 1: Replace page-level spacing**

Update the `.page` override (~line 123):

```css
/* Before */
padding: 4px 6px;
gap: 6px;

/* After */
padding: var(--pad-compact) var(--gap-compact);
gap: var(--gap-compact);
```

- [ ] **Step 2: Replace KPI box spacing**

Update `.kpi-row` gap (~line 155):

```css
gap: var(--gap-compact);
```

And `.kpi-box` padding (~line 171):

```css
padding: var(--pad-compact) 2px;
```

- [ ] **Step 3: Replace KPI label typography**

Update `.kpi-label` (~line 181):

```css
/* Before */
font-size: 11px;
font-weight: 600;
letter-spacing: 0.1em;

/* After */
font-size: var(--label-sm-size);
font-weight: var(--label-sm-weight);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 4: Replace light-label typography**

Update `.light-label` (~line 257):

```css
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-xs-spacing);
```

- [ ] **Step 5: Replace tws-label typography**

Update `.tws-label` (~line 226):

```css
font-size: var(--label-sm-size);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 6: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/RegattaPage.svelte
git commit -m "feat(ui): apply compact spacing and typography tokens to RegattaPage"
```

---

### Task 7: Update SensorsPage.svelte — Compact Spacing + Typography

**Files:**
- Modify: `frontend/src/pages/SensorsPage.svelte` (styles ~lines 96-167)

- [ ] **Step 1: Replace page-level and grid spacing**

```css
/* page padding ~line 101 */
padding: var(--gap-compact);

/* grid gap ~line 106 */
gap: var(--gap-compact);

/* cell padding ~line 118 */
padding: var(--gap-compact) var(--pad-compact);
```

- [ ] **Step 2: Replace label typography**

Update `.cell .label` (~line 126). SensorsPage labels are currently 14px — use `label-md` (13px) rather than `label-sm` (11px) since this page needs larger labels for cockpit readability:

```css
/* Before */
font-size: 14px;
font-weight: 600;
letter-spacing: 0.12em;

/* After */
font-size: var(--label-md-size);  /* 14px → 13px, mild tightening */
font-weight: var(--label-md-weight);
letter-spacing: var(--label-md-spacing);
```

- [ ] **Step 3: Replace source typography**

Update `.source` (~line 155):

```css
font-size: var(--label-xs-size);
letter-spacing: var(--label-xs-spacing);
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SensorsPage.svelte
git commit -m "feat(ui): apply compact spacing and typography tokens to SensorsPage"
```

---

### Task 8: Update CourseSetupPage.svelte — Compact Tokens

**Files:**
- Modify: `frontend/src/pages/CourseSetupPage.svelte` (styles ~lines 320-597)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 324-325 */
gap: var(--gap-airy); /* 10px → 12px, slightly more airy since this is setup */
padding: var(--pad-airy); /* 12px → 8px, but this page has forms so keep airy */
```

Note: CourseSetupPage is in the carousel but is a setup/form page. Spec deviation: uses `--gap-airy` / `--pad-airy` instead of compact, because its content is form-like (mark list, buttons) not dense KPI data.

- [ ] **Step 2: Replace section header typography**

```css
/* section-title ~line ~430 */
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-sm-spacing); /* keep wider spacing for section titles */
```

- [ ] **Step 3: Replace mark-status and type-badge typography**

```css
/* .mark-status */
font-size: var(--label-sm-size);
font-weight: var(--label-sm-weight);
letter-spacing: var(--label-xs-spacing);

/* .type-badge */
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CourseSetupPage.svelte
git commit -m "feat(ui): apply spacing and typography tokens to CourseSetupPage"
```

---

### Task 9: Update RaceTimerPage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/RaceTimerPage.svelte` (styles ~lines 265-476)

Note: RaceTimerPage is in the carousel but has timer/button/form content. Spec deviation: uses airy tokens like CourseSetupPage.

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 278-279 */
gap: var(--gap-airy); /* 10px → 12px */
padding: var(--pad-airy); /* 10px → 8px */
```

- [ ] **Step 2: Replace field label typography**

```css
/* .field .label ~line 390 */
font-size: var(--label-xs-size);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 3: Replace field unit typography**

```css
/* .field .unit */
font-size: var(--label-xs-size);
color: var(--text-dim);
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/RaceTimerPage.svelte
git commit -m "feat(ui): apply spacing and typography tokens to RaceTimerPage"
```

---

### Task 10: Update MapPage.svelte — Compact Tokens

**Files:**
- Modify: `frontend/src/pages/MapPage.svelte` (styles ~lines 581-645)

MapPage is mostly a canvas — minimal CSS changes needed.

- [ ] **Step 1: Replace helm overlay spacing**

```css
/* .helm-overlay gap ~line 595 */
gap: var(--gap-compact);
```

- [ ] **Step 2: Replace helm toggle typography**

```css
/* .helm-toggle */
font-size: var(--label-xs-size);
font-weight: var(--label-sm-weight);
letter-spacing: var(--label-xs-spacing);
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MapPage.svelte
git commit -m "feat(ui): apply compact tokens to MapPage"
```

---

### Task 11: Update CalibrationPage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/CalibrationPage.svelte` (styles ~lines 418-713)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 422-423 */
padding: var(--pad-airy);
gap: var(--gap-airy);
```

- [ ] **Step 2: Replace section title typography**

```css
/* .section-title ~line 447 */
font-size: var(--label-xs-size);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 3: Replace live-label and cal-label typography**

```css
/* .live-label */
font-size: var(--label-xs-size); /* 8px → 9px, slightly larger */
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-sm-spacing);

/* .cal-label */
font-size: var(--label-sm-size);
```

- [ ] **Step 4: Replace auto-title typography**

```css
/* .auto-title */
font-size: var(--label-sm-size); /* 12px → 11px */
font-weight: var(--label-md-weight);
letter-spacing: var(--label-md-spacing);
```

- [ ] **Step 5: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/CalibrationPage.svelte
git commit -m "feat(ui): apply airy spacing and typography tokens to CalibrationPage"
```

---

### Task 12: Update PolarDiagramPage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/PolarDiagramPage.svelte` (styles ~lines 199-377)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 203-204 */
padding: var(--pad-airy);
gap: var(--pad-airy);
```

- [ ] **Step 2: Replace toggle and target label typography**

```css
/* .toggle-btn */
font-size: var(--label-xs-size); /* 10px → 9px */
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-xs-spacing);

/* .target-label */
font-size: var(--label-xs-size); /* 8px → 9px */
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PolarDiagramPage.svelte
git commit -m "feat(ui): apply airy tokens to PolarDiagramPage"
```

---

### Task 13: Update PolarPage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/PolarPage.svelte` (styles ~lines 324-697)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 328-329 */
padding: var(--pad-airy);
gap: var(--gap-airy);
```

- [ ] **Step 2: Replace stat-label, section-title, step-label typography**

```css
/* .stat-label */
font-size: var(--label-xs-size);
letter-spacing: var(--label-xs-spacing);

/* .section-title */
font-size: var(--label-xs-size);
letter-spacing: var(--label-sm-spacing);

/* .step-label */
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-xs-spacing);
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PolarPage.svelte
git commit -m "feat(ui): apply airy tokens to PolarPage"
```

---

### Task 14: Update TrimPage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/TrimPage.svelte` (styles ~lines 109-184)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 115-116 */
gap: var(--gap-airy);
padding: var(--pad-airy);
```

- [ ] **Step 2: Replace best-label typography**

```css
/* .best-label */
font-size: var(--label-xs-size);
letter-spacing: var(--label-xs-spacing);
```

- [ ] **Step 3: Replace best-header typography**

```css
/* .best-header */
font-size: var(--label-sm-size); /* 12px → 11px */
letter-spacing: var(--label-sm-spacing);
font-weight: var(--label-sm-weight);
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/TrimPage.svelte
git commit -m "feat(ui): apply airy tokens to TrimPage"
```

---

### Task 15: Update TrimGuidePage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/TrimGuidePage.svelte` (styles ~lines 289-667)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 294-295 */
padding: var(--pad-airy);
gap: var(--gap-airy);
```

- [ ] **Step 2: Replace condition-label, sea-title, perf-label, review-label typography**

```css
/* .cond-label */
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-sm-spacing);

/* .sea-title */
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-sm-spacing);

/* .perf-label */
font-size: var(--label-xs-size);
font-weight: var(--label-xs-weight);
letter-spacing: var(--label-sm-spacing);

/* .review-label */
font-size: var(--label-xs-size);
letter-spacing: var(--label-xs-spacing);
```

- [ ] **Step 3: Replace step-label typography**

```css
/* .step-label */
font-size: var(--label-sm-size); /* 12px → 11px */
font-weight: var(--label-md-weight);
letter-spacing: var(--label-md-spacing);
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/TrimGuidePage.svelte
git commit -m "feat(ui): apply airy tokens to TrimGuidePage"
```

---

### Task 16: Update SystemPage.svelte — Airy Tokens

**Files:**
- Modify: `frontend/src/pages/SystemPage.svelte` (styles ~lines 189-314)

- [ ] **Step 1: Replace page-level spacing**

```css
/* ~line 193-194 */
padding: var(--pad-airy);
gap: var(--gap-airy); /* 16px → 12px, slightly tighter */
```

- [ ] **Step 2: Replace section-title typography**

```css
/* .section-title */
font-size: var(--label-xs-size); /* 10px → 9px */
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 3: Replace mode-label typography**

```css
/* .mode-label */
font-size: var(--label-md-size);
font-weight: var(--label-md-weight);
letter-spacing: var(--label-sm-spacing);
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SystemPage.svelte
git commit -m "feat(ui): apply airy tokens to SystemPage"
```

---

### Task 17: Final Build + Full Visual Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Full frontend build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Start backend and verify in browser**

```bash
cd /Users/tommaso/Documents/regata-software && python -m aquarela.main --simulator
```

Open `http://localhost:8080` and check:
- SailSelector shows full label ("Randa 1 + Genoa")
- RegattaPage: compact spacing, consistent label typography
- SensorsPage: compact spacing, consistent labels
- CalibrationPage: airy spacing
- PolarPage/PolarDiagramPage: airy spacing
- HeelGauge in RegattaPage: expanded without `:global()` hacks
- Value transitions: numbers change smoothly

- [ ] **Step 3: Run all tests**

```bash
cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -x -q
```

Expected: All tests pass (CSS-only changes shouldn't break backend tests).

- [ ] **Step 4: Final commit if any fixups needed**

```bash
git add -A && git commit -m "fix(ui): polish pass final adjustments"
```
