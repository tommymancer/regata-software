<!--
  RegattaPage — Unified racing screen (redesigned from whiteboard).

  Layout (top to bottom, full Pixel 6 screen 412×915):
    0. Wind shift indicator (horizontal bar, green=lift red=header)
    1. TWA boat gauge in its own card — boat + two watch hands
    2. Three KPI boxes: VMC | COG | BSP — target top, actual bottom
    3. TWS + "on target" traffic light indicator
    4. Heel gauge
-->
<script>
  import TwaGauge from "../components/TwaGauge.svelte";
  import HeelGauge from "../components/HeelGauge.svelte";
  import ShiftGauge from "../components/ShiftGauge.svelte";
  import { twa, bsp, vmg, vmc, tws, twd, heel, sog, cog,
           targetTwa, targetBsp, targetVmg, targetVmc,
           perfPct, btw, dtw, nextMark,
           distToPortLayline, distToStbdLayline }
    from "../stores/boat.js";
  import { history } from "../stores/history.js";
  import { computeWindShift } from "../lib/wind_shift.js";
  import { fmtSpeed, fmtAngle, fmt } from "../lib/formatting.js";

  // Wind shift (lift / header)
  $: windShift = computeWindShift($history, $twd, $twa);

  // Traffic light: green ≥ 95%, yellow ≥ 80%, red < 80%
  $: perfLevel = $perfPct == null ? "none"
    : $perfPct >= 95 ? "green"
    : $perfPct >= 80 ? "yellow"
    : "red";

  $: perfLabel = $perfPct == null ? "---"
    : $perfPct >= 95 ? "A TARGET"
    : $perfPct >= 80 ? "VICINO"
    : "FUORI TARGET";

  // Layline: show distance to the layline you're approaching on this tack.
  // On starboard tack (TWA > 0), you're sailing toward the starboard layline.
  // When it reaches 0 you should tack — you're at the layline.
  $: isStbd = $twa != null && $twa > 0;
  $: layDist = isStbd ? $distToStbdLayline : $distToPortLayline;
  $: layLabel = isStbd ? "S LAY" : "P LAY";

  function fmtLayDist(nm) {
    if (nm == null) return "---";
    return Math.round(nm * 1852) + "m";
  }

  // Layline urgency: green when far, orange when close, accent when on it
  function layColor(nm) {
    if (nm == null) return "var(--text-dim)";
    const m = nm * 1852;
    if (m < 30) return "var(--green)";   // on the layline — tack now!
    if (m < 100) return "var(--orange)";  // getting close
    return "var(--text-dim)";
  }
</script>

<div class="page">
  <!-- 0. Wind shift indicator -->
  <div class="shift-section">
    <ShiftGauge shift={windShift.shift} type={windShift.type} />
  </div>

  <!-- 1. TWA gauge in its own card -->
  <div class="twa-card">
    <TwaGauge twa={$twa} targetTwa={$targetTwa} />
  </div>

  {#if $nextMark}
    <div class="next-mark">PROSSIMA: {$nextMark}</div>
  {/if}

  <!-- 2. Three KPI boxes: VMC | LAY | BSP -->
  <div class="kpi-row">
    <div class="kpi-box">
      <div class="kpi-label">VMC</div>
      <div class="kpi-target">{fmtSpeed($targetVmc)}</div>
      <div class="kpi-divider"></div>
      <div class="kpi-actual">{fmtSpeed($vmc)}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">{layLabel}</div>
      <div class="kpi-target">{$dtw != null ? ($dtw < 0.1 ? Math.round($dtw * 1852) + "m" : $dtw.toFixed(1) + "nm") : "---"}</div>
      <div class="kpi-divider"></div>
      <div class="kpi-actual" style:color={layColor(layDist)}>{fmtLayDist(layDist)}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">KT</div>
      <div class="kpi-target">{fmtSpeed($targetBsp)}</div>
      <div class="kpi-divider"></div>
      <div class="kpi-actual">{fmtSpeed($bsp)}</div>
    </div>
  </div>

  <!-- 3. TWS + Performance traffic light -->
  <div class="status-row">
    <div class="tws-box">
      <div class="tws-label">TWS</div>
      <div class="tws-value">{fmtSpeed($tws, 0)}<span class="tws-unit">kt</span></div>
    </div>
    <div class="target-light">
      <div class="light-circle {perfLevel}"></div>
      <div class="light-label">{perfLabel}</div>
      {#if $perfPct != null}
        <div class="light-pct">{$perfPct.toFixed(0)}%</div>
      {/if}
    </div>
  </div>

  <!-- 4. Large heel gauge -->
  <div class="heel-section">
    <HeelGauge value={$heel} expanded={true} />
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: var(--pad-compact) var(--gap-compact);
    gap: var(--gap-compact);
  }

  /* ── 0. Wind Shift Indicator ─────────────────────────── */
  .shift-section {
    width: 100%;
    flex-shrink: 0;
  }

  .next-mark {
    font-size: 13px;
    font-weight: 700;
    color: var(--orange);
    letter-spacing: 1.5px;
    text-align: center;
    flex-shrink: 0;
  }

  /* ── 1. TWA Gauge Card  ~40% ───────────────────────── */
  .twa-card {
    width: 100%;
    flex: 4;
    min-height: 0;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
  }

  /* ── 2. KPI Boxes  (part of ~40% with status-row) ──── */
  .kpi-row {
    display: flex;
    gap: var(--gap-compact);
    width: 100%;
    flex: 2.4;
    min-height: 0;
  }

  .kpi-box {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: var(--pad-compact) 2px;
    overflow: hidden;
  }

  .kpi-label {
    font-size: var(--label-sm-size);
    font-weight: var(--label-sm-weight);
    color: var(--text-dim);
    letter-spacing: var(--label-sm-spacing);
    margin-bottom: 2px;
  }

  .kpi-target {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: clamp(28px, 8vw, 48px);
    font-weight: 700;
    color: var(--text-dim);
    line-height: 1;
    opacity: 0.7;
  }

  .kpi-divider {
    width: 80%;
    height: 1px;
    background: var(--border);
    margin: 2px 0;
  }

  .kpi-actual {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: clamp(36px, 10vw, 64px);
    font-weight: 800;
    color: var(--text);
    text-shadow: var(--glow-text);
    line-height: 1;
  }

  /* ── 3. TWS + Traffic Light (part of ~40% with KPIs) ─ */
  .status-row {
    display: flex;
    gap: var(--gap-compact);
    width: 100%;
    flex: 1.6;
    min-height: 0;
  }

  .tws-box {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 8px;
  }

  .tws-label {
    font-size: var(--label-sm-size);
    font-weight: 600;
    color: var(--text-dim);
    letter-spacing: var(--label-sm-spacing);
  }

  .tws-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 72px;
    font-weight: 800;
    color: var(--text);
    text-shadow: var(--glow-text);
    line-height: 1;
  }

  .tws-unit {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-dim);
    margin-left: 2px;
  }

  .target-light {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px;
    gap: 2px;
  }

  .light-circle {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 2px solid var(--border);
  }

  .light-circle.green {
    background: var(--green);
    border-color: var(--green);
    box-shadow: 0 0 14px var(--green);
  }

  .light-circle.yellow {
    background: var(--orange);
    border-color: var(--orange);
    box-shadow: 0 0 14px var(--orange);
  }

  .light-circle.red {
    background: var(--red);
    border-color: var(--red);
    box-shadow: 0 0 14px var(--red);
  }

  .light-circle.none {
    background: var(--card);
  }

  .light-label {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    color: var(--text-dim);
    letter-spacing: var(--label-xs-spacing);
    text-align: center;
  }

  .light-pct {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 48px;
    font-weight: 700;
    color: var(--text);
  }

  /* ── 4. Heel Gauge (~10% with page dots) ─────────── */
  .heel-section {
    width: 100%;
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

</style>
