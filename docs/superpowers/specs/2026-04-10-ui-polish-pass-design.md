# UI Polish Pass — Design Spec

**Date:** 2026-04-10
**Status:** Draft

## Goal

Standardize visual inconsistencies across the Aquarela frontend: spacing, typography, SailSelector display, StatusBar treatment, HeelGauge CSS cleanup, and subtle transitions. No layout changes, no new features — only polish.

## Decisions

| Topic | Choice | Detail |
|-------|--------|--------|
| Spacing | Hybrid | Carousel pages use compact spacing; menu pages use airy spacing |
| Typography | 3-level scale | `label-xs` (9px/700/0.08em), `label-sm` (11px/700/0.12em), `label-md` (13px/800/0.12em) |
| SailSelector | Full label | Shows "Randa 1 + Genoa" instead of config key |
| StatusBar | Flat | Stays flat background as app chrome; cards keep gradient as content |

## Design

### 1. CSS Design Tokens

Add variables to `App.svelte`'s `<style>` section, in the `.app { ... }` rule (theme-independent base). No `global.css` exists — all CSS variables live in App.svelte's scoped styles.

```css
/* Spacing — hybrid */
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
```

Also update the existing `:global(.page)` rule in App.svelte (currently hardcodes `padding: 8px; gap: 12px`) to use the tokens as defaults.

### 2. SailSelector.svelte

- Add an `onMount` fetch to `GET /api/sails` so the label is available immediately (currently `sailData` is only populated after the picker is opened).
- The button shows `sailData?.label ?? shortLabel` (e.g. "Randa 1 + Genoa").
- `GET /api/sails` already returns a `label` field from `SAIL_CONFIGS`.
- The picker overlay (RANDA + PRUA grid) stays unchanged.

### 3. StatusBar.svelte

- Background stays `var(--card)` with `border-top: 1px solid var(--border)` (it's a bottom bar — no changes to current background or border direction).
- Labels inside adopt `label-xs` / `label-sm` variables instead of hardcoded font sizes/weights.

### 4. HeelGauge Cleanup

- Remove `:global(.heel-gauge-wrapper)` overrides with `!important` from RegattaPage.
- HeelGauge accepts an `expanded` prop (boolean, default false).
- The default HeelGauge is the compact version (current base styles). When `expanded={true}`, HeelGauge internally applies larger dimensions (28px bar height, 48px value font) — matching what RegattaPage currently forces via `:global()`.
- RegattaPage uses `<HeelGauge expanded={true} />` instead of `:global()` overrides.
- This eliminates fragile cross-component style coupling.

### 5. Carousel Pages

Pages in the swipe carousel: **CourseSetupPage**, **RaceTimerPage**, **RegattaPage**, **MapPage**, **SensorsPage**.

Note: UpwindPage and DownwindPage exist as files but are not in App.svelte's carousel. They are excluded from this pass (see Scope Boundaries).

- Replace hardcoded `gap`/`padding` values with `var(--gap-compact)` / `var(--pad-compact)`.
- Replace label font properties with the typography scale variables:
  - KPI titles (TWA, VMC, BSP, etc.) → `label-sm`
  - Units (kt, nm, °) → `label-xs`
  - Section headers → `label-md`

### 6. InstrumentField.svelte

This is the core KPI display component used across carousel pages. It has hardcoded `.label` (13px/700/0.12em) and `.unit` (12px/600/0.05em) styles, plus size variants (lg/md/sm).

- Map `.label` styles to use `label-sm` tokens.
- Map `.unit` styles to use `label-xs` tokens.
- For the `lg` size variant (currently 16px label), keep the larger size — only standardize weight and letter-spacing to match the scale.
- Add a `transition: opacity 0.12s ease` on the `.value` element. On value change, briefly dip opacity to 0.85 and back (requires a small reactive snippet: `$: if (value) { flash = true; setTimeout(() => flash = false, 120) }`) to soften number flashes.

### 7. Menu Pages

Pages accessible from the hamburger menu: **CalibrationPage**, **TrimPage**, **TrimGuidePage**, **PolarDiagramPage**, **PolarPage**, **SystemPage**.

- Replace hardcoded `gap`/`padding` values with `var(--gap-airy)` / `var(--pad-airy)`.
- Same typography scale adoption as carousel pages.

### 8. Transitions

- The opacity flash on value change is implemented in `InstrumentField.svelte` (Section 6).
- No complex animations. Touch feedback (`opacity: 0.7` on `:active`) already exists on buttons — keep as is.

## Scope Boundaries

- **In scope:** CSS variables, typography standardization, SailSelector label, HeelGauge prop, spacing alignment, value transitions.
- **Out of scope:** Layout restructuring, new components, canvas gauge changes, theme color changes, new pages. UpwindPage, DownwindPage, NavPage, WindRosePage, PerformancePage are not mounted in App.svelte and are excluded.

## Files Affected

- `frontend/src/App.svelte` — add design tokens to `.app` rule, update `:global(.page)` defaults
- `frontend/src/components/SailSelector.svelte` — add onMount fetch, show label instead of key
- `frontend/src/components/StatusBar.svelte` — adopt typography variables
- `frontend/src/components/HeelGauge.svelte` — add `expanded` prop, internalize size variants
- `frontend/src/components/InstrumentField.svelte` — adopt typography tokens, add value transition
- `frontend/src/pages/RegattaPage.svelte` — remove HeelGauge `:global()` overrides, use `expanded` prop, adopt tokens
- `frontend/src/pages/CourseSetupPage.svelte` — adopt compact tokens
- `frontend/src/pages/RaceTimerPage.svelte` — adopt compact tokens
- `frontend/src/pages/MapPage.svelte` — adopt compact tokens
- `frontend/src/pages/SensorsPage.svelte` — adopt compact tokens
- `frontend/src/pages/CalibrationPage.svelte` — adopt airy tokens
- `frontend/src/pages/PolarDiagramPage.svelte` — adopt airy tokens
- `frontend/src/pages/PolarPage.svelte` — adopt airy tokens
- `frontend/src/pages/TrimPage.svelte` — adopt airy tokens
- `frontend/src/pages/TrimGuidePage.svelte` — adopt airy tokens
- `frontend/src/pages/SystemPage.svelte` — adopt airy tokens
