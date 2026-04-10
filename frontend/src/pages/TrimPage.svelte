<!--
  TrimPage — Trim book: save current trim settings, view best trim for conditions.

  Top: current conditions (TWS, TWA, BSP, PERF%)
  Middle: trim entry grid
  Bottom: best trim recommendation for current conditions
-->
<script>
  import { onDestroy } from "svelte";
  import InstrumentField from "../components/InstrumentField.svelte";
  import TrimEntry from "../components/TrimEntry.svelte";
  import { tws, twa, bsp, perfPct } from "../stores/boat.js";
  import { fmtSpeed, fmtSignedAngle, fmtPct, levelColor } from "../lib/formatting.js";

  let bestTrim = null;
  let saveMessage = "";
  let lastSeaState = "";

  async function handleSave(event) {
    const params = new URLSearchParams(event.detail);
    lastSeaState = event.detail.sea_state || "";
    try {
      const res = await fetch(`/api/trim?${params}`, { method: "POST" });
      if (res.ok) {
        saveMessage = "Saved!";
        setTimeout(() => (saveMessage = ""), 2000);
        fetchBest();
      }
    } catch (e) {
      saveMessage = "Error";
    }
  }

  async function fetchBest() {
    if ($tws == null || $twa == null) return;
    try {
      let url = `/api/trim/best?tws=${$tws.toFixed(1)}&twa=${$twa.toFixed(1)}`;
      if (lastSeaState) url += `&sea_state=${lastSeaState}`;
      const res = await fetch(url);
      const data = await res.json();
      bestTrim = data.match !== null ? data : null;
      if (data.cunningham !== undefined) bestTrim = data;
    } catch (e) {
      bestTrim = null;
    }
  }

  // Fetch best trim when conditions change (debounced)
  let fetchTimer;
  $: if ($tws != null && $twa != null) {
    clearTimeout(fetchTimer);
    fetchTimer = setTimeout(fetchBest, 3000);
  }

  onDestroy(() => { clearTimeout(fetchTimer); });

  function levelLabel(val) {
    if (!val) return "—";
    if (val === "light") return "L";
    if (val === "medium") return "M";
    if (val === "heavy") return "H";
    return val;
  }

</script>

<div class="page">
  <div class="row conditions">
    <InstrumentField label="TWS" value={fmtSpeed($tws)} unit="kt" size="sm" />
    <InstrumentField label="TWA" value={fmtSignedAngle($twa)} size="sm" />
    <InstrumentField label="BSP" value={fmtSpeed($bsp)} unit="kt" size="sm" />
    {#if $perfPct != null}
      <InstrumentField label="PERF" value={fmtPct($perfPct)} size="sm" />
    {/if}
  </div>

  <TrimEntry on:save={handleSave} />

  {#if saveMessage}
    <div class="save-msg">{saveMessage}</div>
  {/if}

  {#if bestTrim && bestTrim.cunningham !== undefined}
    <div class="best-section">
      <div class="best-header">BEST TRIM — {bestTrim.perf_pct?.toFixed(0)}%</div>
      <div class="best-grid">
        {#each [
          ["CUNN", bestTrim.cunningham],
          ["OUTHL", bestTrim.outhaul],
          ["VANG", bestTrim.vang],
          ["JIB LD", bestTrim.jib_lead],
          ["JIB HL", bestTrim.jib_halyard],
          ["TRAV", bestTrim.traveller],
          ["F.STAY", bestTrim.forestay],
        ] as [label, val]}
          <div class="best-item">
            <span class="best-label">{label}</span>
            <span class="best-value" style:color={levelColor(val)}>{levelLabel(val)}</span>
          </div>
        {/each}
      </div>
      {#if bestTrim.notes}
        <div class="best-notes">{bestTrim.notes}</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    gap: var(--gap-airy);
    padding: var(--pad-airy);
    overflow-y: auto;
  }
  .row {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    width: 100%;
  }
  .conditions {
    flex-shrink: 0;
  }
  .save-msg {
    font-size: 14px;
    color: var(--green);
    font-weight: 600;
  }
  .best-section {
    width: 100%;
    padding: 8px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .best-header {
    font-size: var(--label-sm-size);
    color: var(--accent);
    letter-spacing: var(--label-sm-spacing);
    text-align: center;
    margin-bottom: 8px;
    font-weight: var(--label-sm-weight);
  }
  .best-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
  }
  .best-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .best-label {
    font-size: var(--label-xs-size);
    color: var(--text-dim);
    letter-spacing: var(--label-xs-spacing);
  }
  .best-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 36px;
    font-weight: 700;
  }
  .best-notes {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
    margin-top: 6px;
    font-style: italic;
  }

  @media (max-width: 480px) {
    .page { padding: 6px; gap: 6px; }
    .row { gap: 8px; }
    .best-grid { gap: 4px; }
    .best-value { font-size: 28px; }
  }
</style>
