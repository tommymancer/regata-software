<!--
  WindRosePage — Wind rose display with surrounding instrument fields.
-->
<script>
  import WindRose from "../components/WindRose.svelte";
  import InstrumentField from "../components/InstrumentField.svelte";
  import { awa, aws, twa, tws, twd, bsp, targetTwa } from "../stores/boat.js";
  import { fmtSignedAngle, fmtSpeed, fmtAngle } from "../lib/formatting.js";
</script>

<div class="page">
  <div class="side left">
    <InstrumentField label="AWA" value={fmtSignedAngle($awa)} size="sm" />
    <InstrumentField label="AWS" value={fmtSpeed($aws)} unit="kt" size="sm" />
  </div>

  <div class="center">
    <WindRose awa={$awa} twa={$twa} aws={$aws} tws={$tws} targetTwa={$targetTwa} />
  </div>

  <div class="side right">
    <InstrumentField label="TWA" value={fmtSignedAngle($twa)} size="sm" />
    <InstrumentField label="BSP" value={fmtSpeed($bsp)} unit="kt" size="sm" />
  </div>

  <div class="bottom-row">
    <InstrumentField label="TWD" value={fmtAngle($twd)} size="sm" />
    <InstrumentField label="TWS" value={fmtSpeed($tws)} unit="kt" size="md" />
  </div>
</div>

<style>
  .page {
    display: grid;
    grid-template-columns: auto 1fr auto;
    grid-template-rows: 1fr auto;
    height: 100%;
    padding: 4px;
    gap: 4px;
  }
  .side {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 16px;
  }
  .center {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 0;
  }
  .bottom-row {
    grid-column: 1 / -1;
    display: flex;
    justify-content: center;
    gap: 24px;
  }

  @media (max-width: 480px) {
    .page { padding: 2px; gap: 2px; }
    .side { gap: 8px; }
    .bottom-row { gap: 12px; }
  }
</style>
