<!--
  UpwindPage — Primary upwind sailing display.

  Layout: TWA (large center), BSP + VMG flanking, HDG + SOG + TWS + PERF,
          heel gauge, target TWA.
-->
<script>
  import InstrumentField from "../components/InstrumentField.svelte";
  import HeelGauge from "../components/HeelGauge.svelte";
  import { twa, bsp, vmg, tws, hdg, sog, heel, perfPct, targetTwa, vmc, targetTwaVmc } from "../stores/boat.js";
  import { fmtSignedAngle, fmtSpeed, fmtAngle, fmtPct, sideColor } from "../lib/formatting.js";

  // Use VMC-adjusted target when course offset is active, else polar VMG target
  $: activeTarget = $targetTwaVmc != null ? $targetTwaVmc : $targetTwa;
  $: targetLabel = $targetTwaVmc != null ? "TGT VMC" : "TGT TWA";
</script>

<div class="page">
  <div class="row main-row">
    <InstrumentField label="BSP" value={fmtSpeed($bsp)} unit="kt" size="md" />
    <InstrumentField
      label="TWA"
      value={fmtSignedAngle($twa)}
      size="lg"
      color={sideColor($twa)}
    />
    <InstrumentField label="VMG" value={fmtSpeed($vmg)} unit="kt" size="md" />
  </div>

  <div class="row">
    <InstrumentField label="HDG" value={fmtAngle($hdg)} size="sm" />
    <InstrumentField label="TWS" value={fmtSpeed($tws)} unit="kt" size="sm" />
    <InstrumentField label="SOG" value={fmtSpeed($sog)} unit="kt" size="sm" />
    {#if $perfPct != null}
      <InstrumentField label="PERF" value={fmtPct($perfPct)} size="sm" />
    {/if}
  </div>

  <div class="row heel-row">
    <HeelGauge value={$heel} />
  </div>

  {#if activeTarget != null}
    <div class="row target-row">
      <InstrumentField label={targetLabel} value={fmtSignedAngle(activeTarget)} size="sm"
        color="var(--orange)" />
      {#if $vmc != null}
        <InstrumentField label="VMC" value={fmtSpeed($vmc)} unit="kt" size="sm"
          color="var(--accent)" />
      {/if}
    </div>
  {/if}
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
  .target-row {
    opacity: 0.8;
  }

  @media (max-width: 480px) {
    .page { gap: 8px; padding: 4px; }
    .row { gap: 8px; }
    .heel-row { padding: 0 8px; }
  }
</style>
