<!--
  PolarDiagramPage — Polar data table showing BSP values by TWA × TWS.

  Shows base polar, learned polar (if available), with TWS columns
  and TWA rows. Highlights differences between base and learned.
-->
<script>
  import { onMount, onDestroy } from "svelte";
  import { boatState, sailConfig } from "../stores/boat.js";

  let data = null;

  const SAIL_LABELS = {
    "main_1__jib": "R1/F",
    "main_1__genoa": "R1/G",
    "main_1__gennaker": "R1/GK",
    "main_2__jib": "R2/F",
    "main_2__genoa": "R2/G",
    "main_2__gennaker": "R2/GK",
  };
  let showMode = "learned"; // "base", "learned", "diff"

  // Active curves: show learned if available and selected, else base
  $: curves = (showMode === "learned" && data?.has_learned)
    ? data?.learned_curves || {}
    : data?.base_curves || {};

  $: baseCurves = data?.base_curves || {};

  // Build sorted TWS and TWA lists
  $: twsValues = data
    ? [...new Set([
        ...Object.keys(data.base_curves || {}),
        ...Object.keys(data.learned_curves || {}),
      ])].map(Number).sort((a, b) => a - b)
    : [];

  $: twaValues = (() => {
    const all = new Set();
    const src = { ...(data?.base_curves || {}), ...(data?.learned_curves || {}) };
    for (const pts of Object.values(src)) {
      for (const p of pts) all.add(p.twa);
    }
    return [...all].sort((a, b) => a - b);
  })();

  // Build lookup: tws → twa → bsp
  function buildLookup(curves) {
    const map = {};
    for (const [tws, pts] of Object.entries(curves)) {
      map[Number(tws)] = {};
      for (const p of pts) {
        map[Number(tws)][p.twa] = p.bsp;
      }
    }
    return map;
  }

  $: lookup = buildLookup(curves);
  $: baseLookup = buildLookup(baseCurves);

  // Targets: learned if available and not explicitly viewing base
  $: upTargets = (showMode !== "base" && data?.has_learned)
    ? data?.learned_targets?.upwind || {}
    : data?.base_targets?.upwind || {};
  $: downTargets = (showMode !== "base" && data?.has_learned)
    ? data?.learned_targets?.downwind || {}
    : data?.base_targets?.downwind || {};

  // Live state
  $: liveTws = $boatState?.tws_kt;
  $: liveTwa = $boatState?.twa_deg != null ? Math.abs($boatState.twa_deg) : null;

  // Closest TWS column to current wind
  $: closestTws = liveTws != null && twsValues.length > 0
    ? twsValues.reduce((a, b) => Math.abs(b - liveTws) < Math.abs(a - liveTws) ? b : a)
    : null;

  // Closest TWA row
  $: closestTwa = liveTwa != null && twaValues.length > 0
    ? twaValues.reduce((a, b) => Math.abs(b - liveTwa) < Math.abs(a - liveTwa) ? b : a)
    : null;

  function cellDiff(tws, twa) {
    if (!data?.has_learned || showMode === "base") return null;
    const learned = data.learned_curves?.[tws];
    const base = data.base_curves?.[tws];
    if (!learned || !base) return null;
    const lPt = learned.find(p => p.twa === twa);
    const bPt = base.find(p => p.twa === twa);
    if (!lPt || !bPt) return null;
    const diff = lPt.bsp - bPt.bsp;
    if (Math.abs(diff) < 0.05) return null;
    return diff;
  }

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

  let stats = null;
  let resetting = false;

  async function fetchData() {
    try {
      const [dRes, sRes] = await Promise.all([
        fetch("/api/polar/diagram"),
        fetch("/api/polar/stats"),
      ]);
      data = await dRes.json();
      stats = await sRes.json();
    } catch (e) { /* ignore */ }
  }

  async function resetToBase() {
    if (!confirm("Tornare alla polar base?")) return;
    resetting = true;
    try {
      await fetch("/api/polar/reset-to-base", { method: "POST" });
      await fetchData();
    } catch (e) { /* ignore */ }
    resetting = false;
  }

  let interval;
  onMount(() => {
    fetchData();
    interval = setInterval(fetchData, 60000);
  });
  onDestroy(() => clearInterval(interval));

  // Refetch when sail config changes
  $: $sailConfig, fetchData();
</script>

<div class="page">
  <h2 class="title">TABELLA POLARE — {SAIL_LABELS[$sailConfig] || $sailConfig}</h2>

  <!-- Mode toggle (only when learned polar exists) -->
  <div class="toggles">
    {#if data?.has_learned}
      <button class="toggle-btn" class:active={showMode === "learned"}
        on:click={() => showMode = "learned"}>APPRESA</button>
      <button class="toggle-btn" class:active={showMode === "base"}
        on:click={() => showMode = "base"}>BASE</button>
      <button class="toggle-btn" class:active={showMode === "diff"}
        on:click={() => showMode = "diff"}>DIFF</button>
    {/if}
    {#if liveTws != null}
      <span class="live-wind">TWS {liveTws.toFixed(0)} kt</span>
    {/if}
  </div>

  <!-- Learning stats -->
  {#if stats}
    <div class="stats-line">
      <span>{stats.total_samples.toLocaleString("it")} campioni</span>
      <span>·</span>
      <span>{stats.bins_ready} bin pronti</span>
      <span>·</span>
      <span>{stats.coverage_pct}% copertura</span>
      {#if stats.has_learned_polar}
        <span class="learned-badge">APPRESA</span>
      {/if}
    </div>
  {/if}

  <!-- Targets row -->
  {#if closestTws != null}
    {@const ut = upTargets[closestTws]}
    {@const dt = downTargets[closestTws]}
    <div class="targets-row">
      {#if ut}
        <div class="target-card">
          <span class="target-label">BOLINA</span>
          <span class="target-val">{ut.twa.toFixed(0)}° — {ut.bsp.toFixed(1)} kt — VMG {ut.vmg.toFixed(1)}</span>
        </div>
      {/if}
      {#if dt}
        <div class="target-card">
          <span class="target-label">POPPA</span>
          <span class="target-val">{dt.twa.toFixed(0)}° — {dt.bsp.toFixed(1)} kt — VMG {dt.vmg.toFixed(1)}</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Table -->
  {#if twsValues.length > 0 && twaValues.length > 0}
    <div class="table-scroll">
      <table class="polar-table">
        <thead>
          <tr>
            <th class="corner">TWA\TWS</th>
            {#each twsValues as tws}
              <th class:highlight-col={tws === closestTws}>{tws}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
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
        </tbody>
      </table>
    </div>
  {:else}
    <div class="empty-state">
      <div class="empty-text">Nessun dato polare disponibile</div>
    </div>
  {/if}

  <!-- Reset to base -->
  {#if data?.has_learned}
    <button class="reset-btn" on:click={resetToBase} disabled={resetting}>
      {resetting ? "..." : "RESET POLAR BASE"}
    </button>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    padding: var(--pad-airy);
    gap: var(--pad-airy);
    height: 100%;
    overflow: hidden;
  }
  .title {
    font-size: 13px;
    letter-spacing: 0.15em;
    color: var(--accent);
    margin: 0;
    text-align: center;
    flex-shrink: 0;
  }

  /* ── Toggles ──────────────────────────────────── */
  .toggles {
    display: flex;
    gap: 6px;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
  }
  .toggle-btn {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-xs-spacing);
    padding: 4px 10px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    touch-action: manipulation;
  }
  .toggle-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--bg);
  }
  .live-wind {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    margin-left: 6px;
  }

  /* ── Targets ──────────────────────────────────── */
  .targets-row {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }
  .target-card {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .target-label {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
  }
  .target-val {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
  }

  /* ── Table ────────────────────────────────────── */
  .table-scroll {
    flex: 1;
    overflow: auto;
    min-height: 0;
    border: 1px solid var(--border);
    border-radius: 6px;
  }
  .polar-table {
    border-collapse: collapse;
    width: max-content;
    min-width: 100%;
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
  }
  .polar-table th,
  .polar-table td {
    padding: 5px 6px;
    text-align: center;
    white-space: nowrap;
    border-bottom: 1px solid var(--border);
    border-right: 1px solid var(--border);
  }
  .polar-table thead {
    position: sticky;
    top: 0;
    z-index: 2;
  }
  .polar-table th {
    background: var(--card);
    color: var(--text-dim);
    font-size: 10px;
    font-weight: 700;
  }
  .polar-table th.corner {
    position: sticky;
    left: 0;
    z-index: 3;
    background: var(--card);
    font-size: 8px;
  }
  .polar-table th.highlight-col {
    color: var(--accent);
    text-shadow: var(--glow-accent);
  }
  .polar-table td {
    background: var(--bg);
    color: var(--text);
  }
  .polar-table td.row-header {
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--card);
    color: var(--text-dim);
    font-weight: 700;
    font-size: 10px;
  }
  .polar-table tr.highlight-row td.row-header {
    color: var(--accent);
    text-shadow: var(--glow-accent);
  }
  .polar-table td.highlight-cell {
    background: rgba(0, 212, 255, 0.1);
    box-shadow: inset 0 0 0 1px var(--accent);
  }

  .bsp-val {
    font-weight: 600;
  }
  .diff-val {
    display: block;
    font-size: 9px;
    font-weight: 600;
  }
  .diff-val.positive { color: var(--green); }
  .diff-val.negative { color: var(--red); }
  .has-diff {
    line-height: 1.2;
  }
  .empty { color: var(--border); }

  .diff-only {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
    font-weight: 700;
    color: #fff;
  }

  /* ── Stats line ───────────────────────────────── */
  .stats-line {
    display: flex;
    gap: 6px;
    justify-content: center;
    align-items: center;
    font-size: var(--label-xs-size);
    color: var(--text-dim);
    letter-spacing: 0.03em;
    flex-shrink: 0;
  }
  .learned-badge {
    font-weight: 800;
    color: var(--green);
    letter-spacing: 0.08em;
  }

  /* ── Reset button ────────────────────────────── */
  .reset-btn {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-xs-spacing);
    padding: 6px 12px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    touch-action: manipulation;
    align-self: center;
    flex-shrink: 0;
  }
  .reset-btn:active { opacity: 0.6; }

  .empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .empty-text {
    color: var(--text-dim);
    font-size: 13px;
  }

  @media (max-width: 480px) {
    .polar-table { font-size: 11px; }
    .polar-table th, .polar-table td { padding: 4px 5px; }
    .target-val { font-size: 11px; }
  }
</style>
