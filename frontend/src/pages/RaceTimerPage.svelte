<!--
  RaceTimerPage — Race start sequence with countdown/elapsed display,
  start line capture, mark sighting, line bias, TTL bar, and strategy callout.

  Layout: main content left, full-height TTL bar right edge.
  Strategy banner appears once mark is sighted via triangulation.
-->
<script>
  import { onDestroy } from "svelte";
  import RaceTimerDisplay from "../components/RaceTimerDisplay.svelte";
  import {
    raceState, raceTimerSecs, bsp, sog, twa, lineBias, distToLine, courseOffset,
    nextMark,
  } from "../stores/boat.js";
  import { fmtSpeed, fmtSignedAngle, sideColor } from "../lib/formatting.js";
  import { minuteBeep, tenSecBeep, secondBeep, gunBeep } from "../lib/audio.js";

  let prevSecs = null;
  let feedback = "";

  // Audio beep logic: detect threshold crossings
  const unsub = raceTimerSecs.subscribe((secs) => {
    if ($raceState !== "countdown" || secs == null || prevSecs == null) {
      prevSecs = secs;
      return;
    }

    for (const m of [300, 240, 180, 120, 60]) {
      if (prevSecs > m && secs <= m) minuteBeep();
    }

    if (secs < 60) {
      for (const t of [50, 40, 30, 20, 10]) {
        if (prevSecs > t && secs <= t) tenSecBeep();
      }
    }

    if (secs < 10) {
      const prevInt = Math.ceil(prevSecs);
      const curInt = Math.ceil(secs);
      if (curInt < prevInt && curInt > 0) secondBeep();
    }

    if (prevSecs > 0.5 && secs <= 0.5) gunBeep();

    prevSecs = secs;
  });

  onDestroy(unsub);

  async function apiCall(endpoint) {
    try {
      await fetch(`/api/race/${endpoint}`, { method: "POST" });
    } catch (e) { /* ignore */ }
  }

  async function roundMark() {
    try {
      const res = await fetch("/api/marks/next", { method: "POST" });
      const data = await res.json();
      if (data.active) {
        showFeedback(`LEG ${data.leg}/${data.total_legs}: ${data.active}`);
      } else {
        showFeedback(data.error || "No next mark");
      }
    } catch { showFeedback("Error"); }
  }

  function showFeedback(msg) {
    feedback = msg;
    setTimeout(() => (feedback = ""), 2000);
  }

  $: biasText = $lineBias != null
    ? ($lineBias > 1 ? "PIN+" + Math.abs($lineBias).toFixed(0) + "°"
       : $lineBias < -1 ? "RC+" + Math.abs($lineBias).toFixed(0) + "°"
       : "SQUARE")
    : null;

  $: biasColor = $lineBias != null
    ? (Math.abs($lineBias) < 3 ? "var(--green)" : "var(--orange)")
    : "var(--text-dim)";

  function fmtDistLine(val) {
    if (val == null) return null;
    return val < 0.05 ? (val * 1852).toFixed(0) + "m" : val.toFixed(2) + "NM";
  }

  // ── TTL (Time To Line) computation ──────────────────────────
  // Compute from actual closing speed (rate of change of dist_to_line).
  // This naturally handles sim_speed, angle of approach, and current.
  // Uses a short rolling window (3 samples) for fast response when
  // the boat changes direction — much faster than the old EMA approach.
  let prevDist = null;
  let prevDistTime = null;
  let closingSpeedKt = null;  // NM/hr toward the line
  let closingSamples = [];
  const CS_WINDOW = 3;

  const distUnsub = distToLine.subscribe((d) => {
    if (d == null) { prevDist = null; prevDistTime = null; closingSamples = []; closingSpeedKt = null; return; }
    const now = performance.now() / 1000;  // seconds
    if (prevDist != null && prevDistTime != null) {
      const dt = now - prevDistTime;
      if (dt > 0.05 && dt < 5) {
        const dDist = prevDist - d;  // positive = closing
        const rawKt = (dDist / dt) * 3600;  // NM/hr
        closingSamples.push(rawKt);
        if (closingSamples.length > CS_WINDOW) closingSamples.shift();
        // Mean of rolling window — adapts in ~3 updates instead of 10+
        closingSpeedKt = closingSamples.reduce((a, b) => a + b, 0) / closingSamples.length;
      }
    }
    prevDist = d;
    prevDistTime = now;
  });

  onDestroy(() => { distUnsub(); });

  $: ttlSecs = ($distToLine != null && closingSpeedKt != null && closingSpeedKt > 0.1)
    ? ($distToLine / closingSpeedKt) * 3600
    : null;

  $: ttlDelta = (ttlSecs != null && $raceTimerSecs != null && $raceState === "countdown")
    ? $raceTimerSecs - ttlSecs
    : null;

  // Clamp delta for bar display (±120 seconds = full bar)
  const TTL_MAX = 120;
  $: ttlFraction = ttlDelta != null
    ? Math.max(-1, Math.min(1, ttlDelta / TTL_MAX))
    : 0;

  $: ttlLabel = ttlDelta != null
    ? (ttlDelta > 5 ? "ANTICIPO" : ttlDelta < -5 ? "TARDI" : "OK")
    : null;

  $: ttlColor = ttlDelta != null
    ? (ttlDelta > 5 ? "var(--green)" : ttlDelta < -5 ? "var(--red)" : "var(--accent)")
    : "var(--text-dim)";

  function fmtTTL(secs) {
    if (secs == null) return "--";
    const s = Math.abs(Math.round(secs));
    const m = Math.floor(s / 60);
    const sec = s % 60;
    const sign = secs < 0 ? "-" : "+";
    return sign + m + ":" + String(sec).padStart(2, "0");
  }

  // ── Strategy: which end to start, which tack ────────────────
  // courseOffset != null means mark has been sighted and triangulated
  $: markSighted = $courseOffset != null;

  // Line end: lineBias > 0 → pin favored, < 0 → RC favored
  $: strategyEnd = ($lineBias != null && markSighted)
    ? ($lineBias > 3 ? "PIN" : $lineBias < -3 ? "RC" : "MID")
    : null;

  // Tack: courseOffset > 0 → mark right of wind → port tack heads toward mark → port favored
  $: strategyTack = ($courseOffset != null)
    ? ($courseOffset > 3 ? "PORT" : $courseOffset < -3 ? "STBD" : null)
    : null;

  $: strategyColor = strategyEnd === "PIN" || strategyEnd === "RC"
    ? "var(--orange)" : "var(--green)";
</script>

<div class="layout">
  <!-- Main content -->
  <div class="main">
    <!-- Strategy banner — appears once mark is sighted -->
    {#if markSighted && strategyEnd}
      <div class="strategy" style:border-color={strategyColor}>
        <span class="strategy-end" style:color={strategyColor}>
          {strategyEnd === "MID" ? "ALLINEATA" : "PARTENZA " + (strategyEnd === "PIN" ? "BOA" : "BARCA")}
        </span>
        {#if strategyTack}
          <span class="strategy-tack">
            {strategyTack} TACK
          </span>
        {/if}
      </div>
    {/if}

    {#if feedback}
      <div class="feedback">{feedback}</div>
    {/if}

    <!-- Line info -->
    {#if biasText || $courseOffset != null}
      <div class="line-info">
        {#if biasText}
          <span class="info-item" style:color={biasColor}>{biasText}</span>
        {/if}
        {#if $courseOffset != null}
          <span class="info-item" style:color="var(--accent)">
            OFFSET {$courseOffset > 0 ? "+" : ""}{$courseOffset.toFixed(0)}°
          </span>
        {/if}
        {#if fmtDistLine($distToLine)}
          <span class="info-item">{fmtDistLine($distToLine)}</span>
        {/if}
      </div>
    {/if}

    <RaceTimerDisplay state={$raceState} secs={$raceTimerSecs} />

    <div class="controls">
      {#if $raceState === "idle"}
        <button class="btn btn-start" on:click={() => apiCall("start?minutes=5")}>START 5</button>
        <button class="btn btn-start" on:click={() => apiCall("start?minutes=3")}>START 3</button>
        <button class="btn btn-start" on:click={() => apiCall("start?minutes=1")}>START 1</button>
      {:else if $raceState === "countdown"}
        <button class="btn btn-sync" on:click={() => apiCall("sync/up")}>SYNC +1m</button>
        <button class="btn btn-sync" on:click={() => apiCall("sync/down")}>SYNC −1m</button>
        <button class="btn btn-stop" on:click={() => apiCall("stop")}>STOP</button>
      {:else}
        <button class="btn btn-next" on:click={roundMark}>PROSSIMA BOA</button>
        <button class="btn btn-stop" on:click={() => apiCall("stop")}>STOP</button>
        <button class="btn btn-reset" on:click={() => apiCall("reset")}>RESET</button>
      {/if}
    </div>

    {#if $nextMark}
      <div class="next-mark">PROSSIMA: {$nextMark}</div>
    {/if}

    <div class="data-row">
      <div class="field">
        <span class="field-label">BSP</span>
        <span class="field-value">{fmtSpeed($bsp)}</span>
        <span class="field-unit">kt</span>
      </div>
      <div class="field">
        <span class="field-label">TWA</span>
        <span class="field-value" style="color: {sideColor($twa)}">{fmtSignedAngle($twa)}</span>
      </div>
    </div>
  </div>

  <!-- TTL bar — right edge, full height -->
  {#if $raceState === "countdown" && ttlDelta != null}
    <div class="ttl-strip">
      <span class="ttl-label" style:color={ttlColor}>{ttlLabel}</span>
      <div class="ttl-bar">
        <div class="ttl-center-line"></div>
        {#if ttlFraction > 0}
          <div
            class="ttl-fill ttl-burn"
            style="height: {Math.abs(ttlFraction) * 50}%; bottom: 50%;"
          ></div>
        {:else if ttlFraction < 0}
          <div
            class="ttl-fill ttl-late"
            style="height: {Math.abs(ttlFraction) * 50}%; top: 50%;"
          ></div>
        {/if}
      </div>
      <span class="ttl-delta" style:color={ttlColor}>{fmtTTL(ttlDelta)}</span>
    </div>
  {/if}
</div>

<style>
  .layout {
    display: flex;
    height: 100%;
    overflow: hidden;
  }

  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: var(--gap-airy);
    padding: var(--pad-airy);
    min-width: 0;
  }

  /* ── Strategy banner ─────────────────────────────────── */
  .strategy {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 8px 24px;
    border: 2px solid;
    border-radius: 8px;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
  }
  .strategy-end {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 52px;
    font-weight: 900;
    letter-spacing: 2px;
  }
  .strategy-tack {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-dim);
    letter-spacing: 1px;
  }

  .btn {
    font-family: inherit;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 16px;
    border: 2px solid;
    border-radius: 6px;
    cursor: pointer;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    letter-spacing: 0.5px;
    touch-action: manipulation;
    transition: opacity 0.15s;
  }
  .feedback {
    font-size: 12px;
    color: var(--green);
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  .line-info {
    display: flex;
    gap: 16px;
    font-size: 12px;
    font-family: "SF Mono", "Menlo", monospace;
    font-weight: 600;
  }
  .info-item {
    color: var(--text-dim);
  }

  /* ── Controls ────────────────────────────────────────── */
  .controls {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: center;
  }
  .btn-start {
    color: var(--green);
    border-color: var(--green);
    min-width: 85px;
  }
  .btn-sync {
    color: var(--orange);
    border-color: var(--orange);
  }
  .btn-next {
    color: var(--green);
    border-color: var(--green);
    min-width: 110px;
  }
  .btn-stop {
    color: var(--red);
    border-color: var(--red);
  }
  .btn-reset {
    color: var(--text-dim);
    border-color: var(--border);
  }
  .btn:active {
    opacity: 0.7;
  }

  .next-mark {
    font-size: 13px;
    font-weight: 700;
    color: var(--orange);
    letter-spacing: 1.5px;
  }

  /* ── Data row ────────────────────────────────────────── */
  .data-row {
    display: flex;
    gap: 32px;
    justify-content: center;
  }
  .field {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .field-label {
    font-size: var(--label-xs-size);
    color: var(--text-dim);
    letter-spacing: 1px;
  }
  .field-value {
    font-family: "SF Mono", "Menlo", "Cascadia Mono", monospace;
    font-size: 48px;
    font-weight: 800;
    color: var(--text);
    text-shadow: var(--glow-text);
  }
  .field-unit {
    font-size: var(--label-xs-size);
    color: var(--text-dim);
  }

  /* ── TTL strip — right edge, full height ─────────────── */
  .ttl-strip {
    width: 52px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 12px 4px;
    border-left: 1px solid var(--border);
    background: var(--card);
    flex-shrink: 0;
  }
  .ttl-label {
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 1.5px;
    writing-mode: horizontal-tb;
  }
  .ttl-bar {
    position: relative;
    width: 28px;
    flex: 1;
    max-height: 400px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .ttl-center-line {
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--text-dim);
    transform: translateY(-1px);
    z-index: 2;
  }
  .ttl-fill {
    position: absolute;
    left: 3px;
    right: 3px;
    border-radius: 3px;
    transition: height 0.3s ease;
    z-index: 1;
  }
  .ttl-burn {
    background: var(--green);
    opacity: 0.85;
  }
  .ttl-late {
    background: var(--red);
    opacity: 0.85;
  }
  .ttl-delta {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 11px;
    font-weight: 700;
  }

  @media (max-width: 480px) {
    .main { gap: 6px; padding: 6px; }
    .btn { font-size: 12px; padding: 8px 12px; }
    .field-value { font-size: 40px; }
    .data-row { gap: 20px; }
    .strategy-end { font-size: 44px; }
    .ttl-strip { width: 44px; }
    .ttl-bar { width: 22px; }
  }
</style>
