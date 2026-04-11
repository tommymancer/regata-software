<!--
  NavPage — Navigation display: heading, COG, SOG, position, depth,
            plus BTW/DTW to active mark when available.
-->
<script>
  import InstrumentField from "../components/InstrumentField.svelte";
  import { hdg, cog, sog, lat, lon, depth, waterTemp, btw, dtw, nextMark,
           laylinePort, laylineStbd, distToPortLayline, distToStbdLayline,
           vmc } from "../stores/boat.js";
  import { fmtAngle, fmtSpeed, fmt } from "../lib/formatting.js";

  function fmtCoord(val, isLat) {
    if (val == null) return "---";
    const abs = Math.abs(val);
    const deg = Math.floor(abs);
    const min = ((abs - deg) * 60).toFixed(3);
    const dir = isLat ? (val >= 0 ? "N" : "S") : (val >= 0 ? "E" : "W");
    return `${deg}°${min}'${dir}`;
  }

  function fmtDist(val) {
    if (val == null) return "---";
    return val < 1 ? (val * 1852).toFixed(0) : val.toFixed(2);
  }

  $: distUnit = $dtw != null && $dtw < 1 ? "m" : "NM";
</script>

<div class="page">
  <div class="row main-row">
    <InstrumentField label="HDG" value={fmtAngle($hdg)} size="lg" />
    <InstrumentField label="COG" value={fmtAngle($cog)} size="lg" />
  </div>

  <div class="row">
    <InstrumentField label="SOG" value={fmtSpeed($sog)} unit="kt" size="md" />
    <InstrumentField label="FONDO" value={fmt($depth)} unit="m" size="md" />
  </div>

  {#if $btw != null}
    <div class="row">
      <InstrumentField label="BTW" value={fmtAngle($btw)} size="md" color="var(--orange)" />
      <InstrumentField label="DTW" value={fmtDist($dtw)} unit={distUnit} size="md" color="var(--orange)" />
    </div>
    {#if $vmc != null}
      <div class="row">
        <InstrumentField label="VMC" value={fmtSpeed($vmc)} unit="kt" size="md" color="var(--orange)" />
      </div>
    {/if}
    {#if $nextMark}
      <div class="mark-name">{$nextMark}</div>
    {/if}
  {/if}

  {#if $laylinePort != null}
    <div class="row">
      <InstrumentField label="LAY P" value={fmtAngle($laylinePort)} size="sm" color="var(--port)" />
      <InstrumentField label="LAY S" value={fmtAngle($laylineStbd)} size="sm" color="var(--stbd)" />
    </div>
    {#if $distToPortLayline != null}
      <div class="row">
        <InstrumentField label="DIST P" value={fmtDist($distToPortLayline)}
          unit={$distToPortLayline < 1 ? "m" : "NM"} size="sm" color="var(--port)" />
        <InstrumentField label="DIST S" value={fmtDist($distToStbdLayline)}
          unit={$distToStbdLayline < 1 ? "m" : "NM"} size="sm" color="var(--stbd)" />
      </div>
    {/if}
  {/if}

  <div class="row position-row">
    <div class="coord">{fmtCoord($lat, true)}</div>
    <div class="coord">{fmtCoord($lon, false)}</div>
  </div>

  <div class="row">
    <InstrumentField label="TEMP ACQUA" value={fmt($waterTemp)} unit="°C" size="sm" />
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
    gap: 24px;
    width: 100%;
  }
  .main-row {
    flex: 1;
    align-items: center;
  }
  .position-row {
    gap: 16px;
  }
  .coord {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 28px;
    color: var(--text-dim);
  }
  .mark-name {
    font-size: 11px;
    color: var(--orange);
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  @media (max-width: 480px) {
    .page { gap: 8px; padding: 4px; }
    .row { gap: 12px; }
    .coord { font-size: 24px; }
  }
</style>
