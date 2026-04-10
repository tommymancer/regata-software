<!--
  SensorsPage — Raw sensor readings in a grid with large numbers.
-->
<script>
  import { boatState } from "../stores/boat.js";
  import { fmt, fmtAngle, fmtSignedAngle, fmtSpeed } from "../lib/formatting.js";

  $: s = $boatState;

  function fmtCoord(val, isLat) {
    if (val == null) return "---";
    const abs = Math.abs(val);
    const deg = Math.floor(abs);
    const min = ((abs - deg) * 60).toFixed(3);
    const dir = isLat ? (val >= 0 ? "N" : "S") : (val >= 0 ? "E" : "W");
    return `${deg}°${min}'${dir}`;
  }
</script>

<div class="page">
  <div class="grid">
    <div class="cell wide">
      <span class="label">HDG</span>
      <span class="val">{fmtAngle(s?.raw_heading_mag)}</span>
      <span class="src">GPS 24xd</span>
    </div>

    <div class="cell">
      <span class="label">AWA</span>
      <span class="val">{fmtSignedAngle(s?.raw_awa_deg)}</span>
      <span class="src">gWind</span>
    </div>
    <div class="cell">
      <span class="label">AWS</span>
      <span class="val">{fmtSpeed(s?.raw_aws_kt)}<span class="unit">kt</span></span>
      <span class="src">gWind</span>
    </div>

    <div class="cell">
      <span class="label">BSP</span>
      <span class="val">{fmtSpeed(s?.raw_bsp_kt)}<span class="unit">kt</span></span>
      <span class="src">Airmar</span>
    </div>
    <div class="cell">
      <span class="label">SOG</span>
      <span class="val">{fmtSpeed(s?.raw_sog_kt)}<span class="unit">kt</span></span>
      <span class="src">GPS 24xd</span>
    </div>

    <div class="cell">
      <span class="label">COG</span>
      <span class="val">{fmtAngle(s?.raw_cog_deg)}</span>
      <span class="src">GPS 24xd</span>
    </div>
    <div class="cell">
      <span class="label">FONDO</span>
      <span class="val">{fmt(s?.raw_depth_m)}<span class="unit">m</span></span>
      <span class="src">Airmar</span>
    </div>

    <div class="cell">
      <span class="label">TEMP ACQUA</span>
      <span class="val">{fmt(s?.raw_water_temp_c)}<span class="unit">°C</span></span>
      <span class="src">Airmar</span>
    </div>
    <div class="cell">
      <span class="label">SBANDAMENTO</span>
      <span class="val">{s?.heel_deg != null ? s.heel_deg.toFixed(1) : "---"}<span class="unit">°</span></span>
      <span class="src">Atlas 2</span>
    </div>

    <div class="cell">
      <span class="label">ASSETTO</span>
      <span class="val">{s?.trim_deg != null ? s.trim_deg.toFixed(1) : "---"}<span class="unit">°</span></span>
      <span class="src">Atlas 2</span>
    </div>
    <div class="cell">
      <span class="label">TRIP</span>
      <span class="val">{s?.trip_log_nm != null ? s.trip_log_nm.toFixed(1) : "---"}<span class="unit">nm</span></span>
      <span class="src">Airmar</span>
    </div>

    <div class="cell">
      <span class="label">POSIZ</span>
      <span class="val coord">{fmtCoord(s?.lat, true)}</span>
      <span class="val coord">{fmtCoord(s?.lon, false)}</span>
    </div>
    <div class="cell">
      <span class="label">ORA</span>
      <span class="val time">{s?.gps_time ?? "---"}</span>
      <span class="src">GPS · {s?.gps_num_sats ?? "?"} sats</span>
    </div>
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: var(--gap-compact);
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--gap-compact);
    flex: 1;
    min-height: 0;
  }
  .cell {
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--gap-compact) var(--pad-compact);
    min-height: 0;
    position: relative;
  }
  .cell.wide {
    grid-column: 1 / -1;
  }
  .label {
    font-size: var(--label-md-size);
    font-weight: var(--label-md-weight);
    text-transform: uppercase;
    letter-spacing: var(--label-md-spacing);
    color: var(--text-dim);
    line-height: 1;
  }
  .val {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: clamp(48px, 15vw, 80px);
    font-weight: 800;
    color: var(--text);
    text-shadow: var(--glow-text);
    line-height: 1.1;
  }
  .cell.wide .val {
    font-size: clamp(60px, 20vw, 108px);
  }
  .val.coord {
    font-size: clamp(20px, 5vw, 28px);
    font-weight: 600;
    color: var(--text-dim);
    line-height: 1.4;
  }
  .val.time {
    font-size: clamp(36px, 10vw, 56px);
  }
  .unit {
    font-size: 0.4em;
    font-weight: 500;
    color: var(--text-dim);
    margin-left: 2px;
  }
  .src {
    font-size: var(--label-xs-size);
    letter-spacing: var(--label-xs-spacing);
    color: var(--accent);
    opacity: 0.6;
    line-height: 1;
    margin-top: 2px;
  }
</style>
