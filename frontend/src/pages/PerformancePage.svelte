<!--
  PerformancePage — Polar performance display with strip chart.

  Layout:
    Top:    PERF% gauge + VMG-PERF% gauge
    Middle: Target vs actual numbers
    Bottom: Strip chart (BSP vs Target BSP over time)
-->
<script>
  import { perfPct, vmgPerfPct, targetTwa, bsp, twa, tws, vmg, targetBsp } from "../stores/boat.js";
  import { fmt, fmtSignedAngle, fmtPct } from "../lib/formatting.js";
  import { getThemeColors } from "../lib/theme.js";
  import PerfGauge from "../components/PerfGauge.svelte";
  import InstrumentField from "../components/InstrumentField.svelte";
  import StripChart from "../components/StripChart.svelte";
  import { history } from "../stores/history.js";
  import { onMount } from "svelte";

  import { boatState } from "../stores/boat.js";
  $: targetVmg = $boatState?.target_vmg_kt ?? null;

  let container;
  let bspTraces = [
    { key: "bsp", color: "#00b4d8", label: "BSP" },
    { key: "target_bsp", color: "#f39c12", label: "Target" },
  ];
  let twsTraces = [{ key: "tws", color: "#2ecc71", label: "TWS" }];
  let perfTraces = [{ key: "perf", color: "#f39c12", label: "PERF%" }];

  onMount(() => {
    if (container) {
      const c = getThemeColors(container);
      bspTraces = [
        { key: "bsp", color: c.accent, label: "BSP" },
        { key: "target_bsp", color: c.orange, label: "Target" },
      ];
      twsTraces = [{ key: "tws", color: c.green, label: "TWS" }];
      perfTraces = [{ key: "perf", color: c.orange, label: "PERF%" }];
    }
  });
</script>

<div class="perf-page" bind:this={container}>
  <div class="gauge-row">
    <div class="gauge">
      <PerfGauge value={$perfPct} label="PERF" />
    </div>
    <div class="gauge">
      <PerfGauge value={$vmgPerfPct} label="VMG PERF" />
    </div>
  </div>

  <div class="data-row">
    <div class="data-pair">
      <InstrumentField label="BSP" value={fmt($bsp)} unit="kt" size="md" />
      <InstrumentField label="TARGET" value={fmt($targetBsp)} unit="kt" size="md" color="var(--orange)" />
    </div>
    <div class="data-pair">
      <InstrumentField label="TWA" value={fmtSignedAngle($twa)} size="md" />
      <InstrumentField label="TARGET" value={fmtSignedAngle($targetTwa)} size="md" color="var(--orange)" />
    </div>
  </div>

  <div class="charts-section">
    <div class="chart-item">
      <span class="chart-label">BSP vs Target</span>
      <StripChart data={$history} traces={bspTraces} windowSec={120} height="80px" />
    </div>
    <div class="chart-item">
      <span class="chart-label">TWS</span>
      <StripChart data={$history} traces={twsTraces} windowSec={120} height="80px" />
    </div>
    <div class="chart-item">
      <span class="chart-label">PERF%</span>
      <StripChart data={$history} traces={perfTraces} windowSec={120} height="80px" minY={0} maxY={120} />
    </div>
  </div>
</div>

<style>
  .perf-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 8px;
    gap: 6px;
  }
  .gauge-row {
    flex: 1;
    display: flex;
    gap: 8px;
    min-height: 0;
  }
  .gauge {
    flex: 1;
    min-height: 0;
  }
  .data-row {
    display: flex;
    justify-content: space-around;
    gap: 16px;
  }
  .data-pair {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .charts-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow-y: auto;
    max-height: 40vh;
    padding: 0 4px;
  }
  .chart-item {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .chart-label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    padding-left: 2px;
  }

  @media (max-width: 480px) {
    .perf-page { padding: 4px; gap: 4px; }
    .data-row { gap: 8px; }
    .charts-section { max-height: 35vh; }
  }
</style>
