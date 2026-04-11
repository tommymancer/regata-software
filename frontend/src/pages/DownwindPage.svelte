<!--
  DownwindPage — Downwind sailing display.

  Layout: TWA (large), SOG + VMG flanking, BSP + TWS + COG + PERF, heel gauge.
-->
<script>
  import InstrumentField from "../components/InstrumentField.svelte";
  import HeelGauge from "../components/HeelGauge.svelte";
  import { twa, bsp, vmg, tws, sog, cog, heel, perfPct } from "../stores/boat.js";
  import { fmtSignedAngle, fmtSpeed, fmtAngle, fmtPct, sideColor } from "../lib/formatting.js";
</script>

<div class="page">
  <div class="row main-row">
    <InstrumentField label="SOG" value={fmtSpeed($sog)} unit="kt" size="md" />
    <InstrumentField
      label="TWA"
      value={fmtSignedAngle($twa)}
      size="lg"
      color={sideColor($twa)}
    />
    <InstrumentField label="VMG" value={fmtSpeed($vmg)} unit="kt" size="md" />
  </div>

  <div class="row">
    <InstrumentField label="BSP" value={fmtSpeed($bsp)} unit="kt" size="sm" />
    <InstrumentField label="TWS" value={fmtSpeed($tws)} unit="kt" size="sm" />
    <InstrumentField label="COG" value={fmtAngle($cog)} size="sm" />
    {#if $perfPct != null}
      <InstrumentField label="PERF" value={fmtPct($perfPct)} size="sm" />
    {/if}
  </div>

  <div class="row heel-row">
    <HeelGauge value={$heel} />
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    gap: 12px;
    padding: 8px;
  }
  .row {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    width: 100%;
  }
  .main-row {
    flex: 1;
    align-items: center;
  }
  .heel-row {
    padding: 0 24px;
  }

  @media (max-width: 480px) {
    .page { gap: 8px; padding: 4px; }
    .row { gap: 8px; }
    .heel-row { padding: 0 8px; }
  }
</style>
