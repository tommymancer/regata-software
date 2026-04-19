<!--
  PageRace — The headline screen at the gun.

  Commits to ONE hero: the TWA gauge with POGGIA/ORZA steering directive.
  Below: 3 KPIs (BSP, VMC, LAY).
  Bottom strip: heel + TWS + HDG.
  Wind-shift bar permanent at top.
-->
<script>
  import { twa, bsp, vmc, tws, twd, heel, hdg, cog,
           targetTwa, targetBsp, targetVmg, targetVmc,
           distToPortLayline, distToStbdLayline,
           btw, dtw, nextMark, connectionStatus }
    from "../stores/boat.js";
  import { history } from "../stores/history.js";
  import { computeWindShift } from "../lib/wind_shift.js";
  import { fmtSpeed } from "../lib/formatting.js";

  // Connection state
  $: isConnected = $connectionStatus === "connected";
  $: isSearching = $connectionStatus === "connecting";
  $: isOffline = $connectionStatus === "disconnected";

  // Wind shift
  $: windShift = computeWindShift($history, $twd, $twa);
  $: shiftDeg = windShift?.shift ?? 0;
  $: shiftType = windShift?.type ?? "LIFT";

  // TWA logic
  $: isPort = $twa != null && $twa < 0;
  $: actualAbs = $twa != null ? Math.abs($twa) : 0;
  $: twaTarget = $targetTwa ?? 40;
  $: twaDelta = actualAbs - twaTarget;
  const tol = 3;
  $: inGroove = Math.abs(twaDelta) <= tol;
  $: tooTight = twaDelta < -tol;

  $: steerHint = $twa == null ? "---" : inGroove ? "IN GROOVE" : tooTight ? "POGGIA" : "ORZA";
  $: steerArrow = inGroove ? "\u25CF" : tooTight ? "\u25BC" : "\u25B2";

  // Laylines
  $: isStbd = $twa != null && $twa > 0;
  $: layDistNm = isStbd ? $distToStbdLayline : $distToPortLayline;
  $: layDistM = layDistNm != null ? Math.round(layDistNm * 1852) : null;
  $: layLabel = isStbd ? "LAY DX" : "LAY SX";

  // Gauge
  const span = 20;
  $: pct = Math.max(-1, Math.min(1, twaDelta / span));
  const ticks = [];
  for (let i = -20; i <= 20; i += 5) ticks.push(i);

  function fmtLay(m, nm) {
    if (m == null) return "---";
    return m < 1000 ? `${m}m` : `${nm.toFixed(2)}nm`;
  }

  // BSP delta
  $: bspTarget = $targetBsp ?? 0;
  $: bspDelta = $bsp != null ? $bsp - bspTarget : 0;

  // VMC delta
  $: vmcTarget = $targetVmc ?? 0;
  $: vmcDelta = $vmc != null ? $vmc - vmcTarget : 0;
</script>

{#if isSearching}
<!-- Searching state -->
<div class="state-screen">
  <div class="pulse-container">
    <div class="pulse-ring" style="animation-delay: 0s;"></div>
    <div class="pulse-ring" style="animation-delay: 0.6s;"></div>
    <div class="pulse-ring" style="animation-delay: 1.2s;"></div>
    <div class="pulse-core">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 9a15 15 0 0 1 20 0M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0" />
        <circle cx="12" cy="20" r="1" fill="currentColor"/>
      </svg>
    </div>
  </div>
  <div class="state-section-label">In ricerca</div>
  <div class="state-title">Cerco Aquarela</div>
  <div class="state-subtitle">
    Collegati alla rete Wi-Fi <b>Aquarela</b> per vedere i dati della barca.
  </div>
  <div class="state-steps">
    <div class="step-dot done"></div>
    <span class="step-label done">WIFI</span>
    <div class="step-line"></div>
    <div class="step-dot active"></div>
    <span class="step-label active">PI</span>
    <div class="step-line"></div>
    <div class="step-dot"></div>
    <span class="step-label">DATI</span>
  </div>
</div>

{:else if isOffline}
<!-- Offline state -->
<div class="state-screen">
  <div class="offline-icon">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2 9a15 15 0 0 1 20 0M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0" />
      <circle cx="12" cy="20" r="1" fill="currentColor"/>
    </svg>
  </div>
  <div class="state-title">Fuori portata</div>
  <div class="state-subtitle">
    Aquarela non &egrave; raggiungibile. Le sessioni passate restano disponibili offline.
  </div>
  <button class="retry-btn" on:click={() => window.location.reload()}>Riprova</button>
</div>

{:else}
<div class="page">
  <!-- Wind-shift bar — permanent, top -->
  <div class="shift-bar">
    <div class="shift-center"></div>
    {#if shiftDeg !== 0}
      <div class="shift-fill"
        class:lift={shiftType === "LIFT"}
        class:header={shiftType === "HEADER"}
        style="left: {shiftDeg >= 0 ? 50 : 50 + (shiftDeg / 15) * 50}%;
               width: {Math.abs(shiftDeg / 15) * 50}%;">
      </div>
    {/if}
    <span class="shift-label"
      class:lift={shiftType === "LIFT"}
      class:header={shiftType === "HEADER"}>
      {shiftType} {Math.abs(shiftDeg)}&deg;
    </span>
  </div>

  <!-- Header strip -->
  <div class="header-strip">
    <span>BOLINA &middot; MURA {isPort ? "DRITTA" : "SINISTRA"}</span>
    <span>{$nextMark ? `PROSSIMA: ${$nextMark}` : ""}</span>
  </div>

  <!-- HERO: TWA gauge -->
  <div class="twa-hero">
    <!-- Top row: label, huge number, target, steering pill -->
    <div class="twa-top">
      <div class="twa-label-col">
        <span class="twa-label">TWA</span>
        <span class="twa-side" class:port={isPort} class:stbd={!isPort}>
          {isPort ? "DX" : "SX"}
        </span>
      </div>

      <div class="twa-number">
        {$twa != null ? Math.round(actualAbs) : "---"}<span class="twa-deg">&deg;</span>
      </div>

      <div class="twa-target-col">
        <span class="target-label">TARGET</span>
        <span class="target-value">{twaTarget}&deg;</span>
      </div>
    </div>

    <!-- Big steering directive -->
    <div class="steer-pill"
      class:groove={inGroove}
      class:warn={!inGroove}>
      <span class="steer-arrow">{steerArrow}</span>
      <span>{steerHint}</span>
      {#if !inGroove && $twa != null}
        <span class="steer-delta">{Math.abs(Math.round(twaDelta))}&deg;</span>
      {/if}
    </div>

    <!-- Gauge scale -->
    <div class="gauge">
      <!-- Groove zone -->
      <div class="gauge-groove"
        style="left: {50 - (tol / span) * 50}%;
               width: {(tol / span) * 100}%;">
      </div>
      <!-- Main scale line -->
      <div class="gauge-line"></div>
      <!-- Ticks -->
      {#each ticks as offset}
        {@const x = 50 + (offset / span) * 50}
        {@const major = offset % 10 === 0}
        {@const isTarget = offset === 0}
        <div class="gauge-tick"
          class:major
          class:target={isTarget}
          style="left: {x}%; top: {isTarget ? 18 : 25}px;
                 height: {isTarget ? 26 : major ? 14 : 8}px;
                 width: {isTarget ? 2 : 1}px;">
        </div>
        {#if major && !isTarget}
          <span class="gauge-tick-label"
            style="left: {x}%;">
            {offset > 0 ? `+${offset}` : offset}
          </span>
        {/if}
        {#if isTarget}
          <span class="gauge-target-label" style="left: {x}%;">TGT</span>
        {/if}
      {/each}
      <!-- Edge labels -->
      <span class="gauge-edge-left">&laquo; POGGIA</span>
      <span class="gauge-edge-right">ORZA &raquo;</span>
      <!-- Needle -->
      <div class="gauge-needle-tri"
        class:groove={inGroove}
        class:warn={!inGroove}
        style="left: {50 + pct * 50}%;">
      </div>
      <div class="gauge-needle-bar"
        class:groove={inGroove}
        class:warn={!inGroove}
        style="left: {50 + pct * 50}%;">
      </div>
    </div>
  </div>

  <!-- 3 KPIs: BSP, VMC, LAY -->
  <div class="kpi-row">
    <div class="kpi-cell">
      <div class="kpi-header">
        <span class="kpi-label">BSP</span>
        <span class="kpi-target-val">{fmtSpeed(bspTarget)}</span>
      </div>
      <div class="kpi-body">
        <span class="kpi-actual" class:good={bspDelta >= -0.1} class:warn={bspDelta < -0.1}>
          {fmtSpeed($bsp)}
        </span>
        <span class="kpi-unit">kt</span>
      </div>
      <span class="kpi-delta" class:good={bspDelta >= -0.1} class:warn={bspDelta < -0.1}>
        {$bsp != null ? (bspDelta >= 0 ? "+" : "") + bspDelta.toFixed(1) : ""}
      </span>
    </div>

    <div class="kpi-cell border-l">
      <div class="kpi-header">
        <span class="kpi-label">VMC</span>
        <span class="kpi-target-val">{fmtSpeed(vmcTarget)}</span>
      </div>
      <div class="kpi-body">
        <span class="kpi-actual" class:good={vmcDelta >= -0.2} class:warn={vmcDelta < -0.2}>
          {fmtSpeed($vmc)}
        </span>
        <span class="kpi-unit">kt</span>
      </div>
      <span class="kpi-delta" class:good={vmcDelta >= -0.2} class:warn={vmcDelta < -0.2}>
        {$vmc != null ? (vmcDelta >= 0 ? "+" : "") + vmcDelta.toFixed(1) : ""}
      </span>
    </div>

    <div class="kpi-cell border-l">
      <div class="kpi-header">
        <span class="kpi-label">{layLabel}</span>
      </div>
      <div class="kpi-body">
        <span class="kpi-actual kpi-lay"
          class:good={layDistM != null && layDistM < 40}
          class:warn={layDistM != null && layDistM >= 40 && layDistM < 120}>
          {fmtLay(layDistM, layDistNm)}
        </span>
      </div>
      <span class="kpi-delta-plain"
        class:good={layDistM != null && layDistM < 40}>
        TACK
      </span>
    </div>
  </div>

  <!-- Bottom strip: TWS | HDG | HEEL -->
  <div class="bottom-row">
    <div class="bottom-cell">
      <span class="bottom-label">TWS</span>
      <div class="bottom-body">
        <span class="bottom-value">{$tws != null ? Math.round($tws) : "---"}</span>
        <span class="bottom-unit">kt</span>
      </div>
      <span class="bottom-sub">TWD {$twd != null ? Math.round($twd) : "---"}&deg;</span>
    </div>
    <div class="bottom-cell border-l">
      <span class="bottom-label">HDG</span>
      <div class="bottom-body">
        <span class="bottom-value">{$hdg != null ? Math.round($hdg) : "---"}&deg;</span>
      </div>
      <span class="bottom-sub">COG {$cog != null ? Math.round($cog) : "---"}&deg;</span>
    </div>
    <div class="bottom-cell border-l">
      <span class="bottom-label">HEEL</span>
      <div class="bottom-body">
        <span class="bottom-value"
          class:danger={$heel != null && Math.abs($heel) > 25}
          class:warn={$heel != null && Math.abs($heel) > 20 && Math.abs($heel) <= 25}>
          {$heel != null ? Math.abs(Math.round($heel)) : "---"}&deg;
        </span>
      </div>
      <span class="bottom-sub">{$heel != null ? ($heel > 0 ? "DX" : "SX") : ""}</span>
    </div>
  </div>
</div>
{/if}

<style>
  /* ── Connection state screens ────────────── */
  .state-screen {
    height: 100%;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px;
    text-align: center;
    font-family: var(--font-text);
    gap: 20px;
  }
  .pulse-container {
    position: relative;
    width: 120px;
    height: 120px;
  }
  .pulse-ring {
    position: absolute;
    inset: 0;
    border: 2px solid var(--accent);
    border-radius: 50%;
    opacity: 0.4;
    animation: aqpulse 2.2s ease-out infinite;
  }
  .pulse-core {
    position: absolute;
    inset: 40px;
    border-radius: 50%;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--bg);
  }
  .state-section-label {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 2px;
    color: var(--text-dim);
    text-transform: uppercase;
  }
  .state-title {
    font-size: 24px;
    font-weight: 600;
    letter-spacing: -0.5px;
  }
  .state-subtitle {
    font-size: 14px;
    color: var(--text-dim);
    max-width: 280px;
  }
  .state-subtitle b { color: var(--text); }
  .state-steps {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-faint);
    letter-spacing: 1.5px;
    margin-top: 4px;
  }
  .step-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 1.5px solid var(--text-faint);
    background: transparent;
  }
  .step-dot.active { background: var(--accent); border-color: var(--accent); }
  .step-dot.done { background: var(--green); border-color: var(--green); }
  .step-label { color: var(--text-faint); }
  .step-label.active { color: var(--accent); }
  .step-label.done { color: var(--green); }
  .step-line {
    width: 28px;
    height: 1px;
    background: var(--border-strong);
  }
  .offline-icon {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    border: 2px solid var(--border-strong);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
  }
  .retry-btn {
    background: var(--text);
    color: var(--bg);
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    font-family: var(--font-text);
    letter-spacing: 0.2px;
    min-height: 48px;
    cursor: pointer;
    touch-action: manipulation;
  }

  .page {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-text);
  }

  /* ── Wind shift bar ──────────────────────── */
  .shift-bar {
    height: 32px;
    background: var(--surface);
    position: relative;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .shift-center {
    position: absolute;
    left: 50%;
    top: 8px;
    bottom: 8px;
    width: 1px;
    background: var(--border-strong);
    opacity: 0.6;
  }
  .shift-fill {
    position: absolute;
    top: 10px;
    bottom: 10px;
    border-radius: 2px;
    opacity: 0.85;
  }
  .shift-fill.lift { background: var(--green); }
  .shift-fill.header { background: var(--red); }
  .shift-label {
    position: relative;
    z-index: 1;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
  }
  .shift-label.lift { color: var(--green); }
  .shift-label.header { color: var(--red); }

  /* ── Header strip ────────────────────────── */
  .header-strip {
    padding: 6px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.2px;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  /* ── TWA Hero ────────────────────────────── */
  .twa-hero {
    padding: 12px 14px 16px;
    background: var(--surface);
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex-shrink: 0;
  }
  .twa-top {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .twa-label-col {
    width: 56px;
    flex-shrink: 0;
  }
  .twa-label {
    display: block;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .twa-side {
    display: inline-block;
    margin-top: 4px;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: #fff;
  }
  .twa-side.port { background: var(--port); }
  .twa-side.stbd { background: var(--stbd); }

  .twa-number {
    font-family: var(--font-numeric);
    font-size: min(104px, 22vw);
    font-weight: 700;
    letter-spacing: -5px;
    line-height: 0.9;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    flex: 1;
  }
  .twa-deg {
    font-size: 0.4em;
    letter-spacing: normal;
  }

  .twa-target-col {
    flex-shrink: 0;
    text-align: right;
  }
  .target-label {
    display: block;
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-faint);
    letter-spacing: 1.5px;
  }
  .target-value {
    display: block;
    font-family: var(--font-numeric);
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -1px;
    color: var(--text-dim);
    font-variant-numeric: tabular-nums;
    line-height: 1;
    margin-top: 2px;
  }

  /* ── Steering pill ───────────────────────── */
  .steer-pill {
    padding: 10px 14px;
    border-radius: 8px;
    font-family: var(--font-numeric);
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    line-height: 1;
  }
  .steer-pill.groove {
    background: var(--green);
    color: #06120a;
  }
  .steer-pill.warn {
    background: var(--orange);
    color: #1a1305;
  }
  .steer-arrow { font-size: 16px; }
  .steer-delta {
    font-size: 18px;
    font-weight: 700;
    margin-left: 4px;
    opacity: 0.85;
  }

  /* Sole theme: white text on colored pills */
  :global(.app[data-theme="sun"]) .steer-pill { color: #fff; }

  /* ── Gauge ───────────────────────────────── */
  .gauge {
    position: relative;
    height: 52px;
  }
  .gauge-groove {
    position: absolute;
    top: 22px;
    height: 20px;
    background: var(--green);
    opacity: 0.22;
    border-radius: 3px;
  }
  .gauge-line {
    position: absolute;
    left: 0;
    right: 0;
    top: 31px;
    height: 2px;
    background: var(--border-strong);
    opacity: 0.5;
  }
  .gauge-tick {
    position: absolute;
    background: var(--border-strong);
    transform: translateX(-50%);
  }
  .gauge-tick.target {
    background: var(--text);
  }
  .gauge-tick-label {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
  }
  .gauge-target-label {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text);
    font-weight: 700;
    letter-spacing: 1px;
  }
  .gauge-edge-left {
    position: absolute;
    left: 0;
    bottom: 0;
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-faint);
    letter-spacing: 1px;
  }
  .gauge-edge-right {
    position: absolute;
    right: 0;
    bottom: 0;
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-faint);
    letter-spacing: 1px;
  }
  .gauge-needle-tri {
    position: absolute;
    top: 14px;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 9px solid transparent;
    border-right: 9px solid transparent;
    transition: left 0.3s ease;
  }
  .gauge-needle-tri.groove { border-top: 13px solid var(--green); filter: drop-shadow(0 0 6px var(--green)); }
  .gauge-needle-tri.warn { border-top: 13px solid var(--orange); filter: drop-shadow(0 0 6px var(--orange)); }

  .gauge-needle-bar {
    position: absolute;
    top: 25px;
    transform: translateX(-50%);
    width: 4px;
    height: 18px;
    transition: left 0.3s ease;
  }
  .gauge-needle-bar.groove { background: var(--green); }
  .gauge-needle-bar.warn { background: var(--orange); }

  /* ── KPI Row ─────────────────────────────── */
  .kpi-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .kpi-cell {
    padding: 12px 10px 10px;
    background: var(--surface);
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .kpi-cell.border-l { border-left: 1px solid var(--border); }
  .kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  .kpi-label {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .kpi-target-val {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-faint);
    letter-spacing: 1px;
  }
  .kpi-body {
    display: flex;
    align-items: baseline;
    gap: 3px;
    margin-top: 2px;
  }
  .kpi-actual {
    font-family: var(--font-numeric);
    font-size: min(40px, 10vw);
    font-weight: 800;
    letter-spacing: -2px;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    color: var(--text);
  }
  .kpi-actual.good { color: var(--green); }
  .kpi-actual.warn { color: var(--orange); }
  .kpi-unit {
    font-size: 14px;
    color: var(--text-dim);
    font-weight: 500;
  }
  .kpi-delta {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }
  .kpi-delta.good { color: var(--green); }
  .kpi-delta.warn { color: var(--orange); }
  .kpi-delta-plain {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--text-dim);
  }
  .kpi-delta-plain.good { color: var(--green); }
  .kpi-lay { color: var(--text-dim); }

  /* ── Bottom Row ──────────────────────────── */
  .bottom-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    flex: 1;
    min-height: 0;
  }
  .bottom-cell {
    padding: 10px 12px;
    background: var(--surface);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 3px;
  }
  .bottom-cell.border-l { border-left: 1px solid var(--border); }
  .bottom-label {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .bottom-body {
    display: flex;
    align-items: baseline;
    gap: 3px;
  }
  .bottom-value {
    font-family: var(--font-numeric);
    font-size: min(44px, 11vw);
    font-weight: 800;
    letter-spacing: -2px;
    line-height: 1;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }
  .bottom-value.danger { color: var(--red); }
  .bottom-value.warn { color: var(--orange); }
  .bottom-unit {
    font-size: 13px;
    color: var(--text-dim);
    font-weight: 500;
  }
  .bottom-sub {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
