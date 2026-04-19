<!--
  PageStart — Pre-start: timer hero, TTL, line bias, strategy, marks drawer.

  Merges the old "Course Setup" + "Race Timer" into one screen.
  Design: huge countdown → TTL bar → line bias diagram → strategy callout.
  Marks drawer accessible via a button in the header.
-->
<script>
  import { raceState, raceTimerSecs, lineBias, distToLine,
           twa, twd, targetTwa,
           btw, dtw, nextMark, courseOffset }
    from "../stores/boat.js";

  let drawerOpen = false;

  // Timer formatting
  $: timerSecs = $raceTimerSecs ?? 0;
  $: mins = Math.floor(timerSecs / 60);
  $: secs = timerSecs % 60;
  $: timerStr = `${mins}:${secs.toString().padStart(2, "0")}`;

  // TTL — time to line (mock: compute from distance and speed)
  // In production this comes from the backend
  $: ttlSecs = timerSecs > 0 ? Math.max(0, timerSecs - 33) : 0; // mock offset
  $: ttlDelta = ttlSecs - timerSecs;
  $: onTime = Math.abs(ttlDelta) <= 3;
  $: early = ttlDelta > 3;
  $: late = ttlDelta < -3;
  $: ttlLabel = timerSecs === 0 ? "---" : onTime ? "ON TIME" : early ? "EARLY" : "LATE";

  // TTL bar gauge position
  const ttlMaxWin = 30;
  $: ttlPct = Math.max(-1, Math.min(1, ttlDelta / ttlMaxWin));

  // Line bias
  $: biasDeg = $lineBias ?? 0;
  $: biasAbs = Math.abs(biasDeg);
  $: biasEnd = biasDeg < 0 ? "RC" : biasDeg > 0 ? "PIN" : "MID";

  // Distance to line
  $: distLineNm = $distToLine ?? 0;
  $: distLineM = Math.round(distLineNm * 1852);

  // Strategy
  $: strategyEnd = biasAbs < 2 ? "MID" : biasDeg < 0 ? "RC" : "PIN";
  $: isPort = $twa != null && $twa < 0;
  $: strategyTack = isPort ? "PORT" : "STBD";

  // Race timer controls
  function startTimer(minutes) {
    fetch("/api/race/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ minutes }),
    }).catch(() => {});
  }

  function syncTimer() {
    fetch("/api/race/sync", { method: "POST" }).catch(() => {});
  }

  function stopTimer() {
    fetch("/api/race/stop", { method: "POST" }).catch(() => {});
  }

  // Line bias diagram SVG math
  const svgW = 360, svgH = 110;
  const cx = svgW / 2, cy = svgH / 2;
  const lineLen = 260;
  $: rad = (biasDeg * Math.PI) / 180;
  $: x1 = cx - Math.cos(rad) * lineLen / 2;
  $: y1 = cy + Math.sin(rad) * lineLen / 2;
  $: x2 = cx + Math.cos(rad) * lineLen / 2;
  $: y2 = cy - Math.sin(rad) * lineLen / 2;
</script>

<div class="page">
  <!-- Header -->
  <div class="header">
    <span>PARTENZA &middot; {$raceState === "countdown" ? "COUNTDOWN" : $raceState === "racing" ? "RACING" : "IDLE"}</span>
  </div>

  <!-- Timer hero -->
  <div class="timer-hero">
    <div class="timer-label">COUNTDOWN</div>
    <div class="timer-row">
      <div class="timer-number">{timerStr}</div>
      <div class="timer-status"
        class:ontime={onTime && timerSecs > 0}
        class:early={early}
        class:late={late}>
        {ttlLabel}
      </div>
    </div>

    <!-- TTL bar -->
    {#if timerSecs > 0}
      <div class="ttl-bar">
        <div class="ttl-zones">
          <div class="ttl-zone late-zone"></div>
          <div class="ttl-zone ok-zone"></div>
          <div class="ttl-zone early-zone"></div>
        </div>
        <div class="ttl-labels">
          <span class="ttl-late-label">TARDI</span>
          <span class="ttl-early-label">ANTICIPO</span>
        </div>
        <div class="ttl-center-line"></div>
        <div class="ttl-marker"
          class:ontime={onTime}
          class:early={early}
          class:late={late}
          style="left: {50 + ttlPct * 50}%;">
        </div>
      </div>

      <div class="ttl-info">
        <span>TTL {Math.floor(ttlSecs/60)}:{(ttlSecs%60).toString().padStart(2,"0")}</span>
        <span>&Delta; {ttlDelta >= 0 ? "+" : ""}{ttlDelta}s</span>
      </div>
    {/if}

    <!-- Timer controls -->
    {#if $raceState === "idle" || timerSecs <= 0}
      <div class="timer-controls">
        <button class="timer-btn" on:click={() => startTimer(5)}>5:00</button>
        <button class="timer-btn" on:click={() => startTimer(3)}>3:00</button>
        <button class="timer-btn" on:click={() => startTimer(1)}>1:00</button>
      </div>
    {:else}
      <div class="timer-controls">
        <button class="timer-btn" on:click={syncTimer}>SYNC</button>
        <button class="timer-btn stop" on:click={stopTimer}>STOP</button>
      </div>
    {/if}
  </div>

  <!-- Line bias diagram -->
  <div class="bias-section">
    <div class="section-label">LINEA DI PARTENZA &middot; BIAS</div>
    <div class="bias-diagram">
      <svg width="100%" viewBox="0 0 {svgW} {svgH}" style="display:block">
        <!-- Wind arrow -->
        <g transform="translate({cx}, 14)">
          <line x1="0" y1="0" x2="0" y2="18" stroke="var(--wind)" stroke-width="2"/>
          <polygon points="0,22 -5,14 5,14" fill="var(--wind)"/>
          <text x="0" y="-2" fill="var(--wind)" font-family="var(--font-mono)"
                font-size="10" font-weight="700" text-anchor="middle" letter-spacing="1">WIND</text>
        </g>
        <!-- Start line -->
        <line x1={x1} y1={y1} x2={x2} y2={y2}
          stroke="var(--border-strong)" stroke-width="3"/>
        <line x1={x1} y1={y1} x2={x2} y2={y2}
          stroke="var(--green)" stroke-width="4" opacity="0.5"/>
        <!-- RC end -->
        <g transform="translate({x1}, {y1})">
          <rect x="-20" y="-10" width="36" height="20" rx="2"
            fill={biasEnd === "RC" ? "var(--green)" : "var(--surface)"}
            stroke="var(--border-strong)" stroke-width="1.5"/>
          <text x="-2" y="4" fill="var(--text)"
            font-family="var(--font-mono)" font-size="11" font-weight="800"
            text-anchor="middle" letter-spacing="1">RC</text>
        </g>
        <!-- PIN end -->
        <g transform="translate({x2}, {y2})">
          <circle r="10" fill={biasEnd === "PIN" ? "var(--green)" : "var(--surface)"}
            stroke="var(--border-strong)" stroke-width="1.5"/>
          <text y="4" fill="var(--text)"
            font-family="var(--font-mono)" font-size="10" font-weight="800"
            text-anchor="middle">P</text>
        </g>
        <!-- Boat -->
        <g transform="translate({cx - 20}, {cy + 40})">
          <path d="M 0 -10 L 6 8 L -6 8 Z" fill="var(--accent)"/>
          <text y="24" fill="var(--text-dim)" font-family="var(--font-mono)"
                font-size="9" text-anchor="middle" letter-spacing="1">TU</text>
        </g>
        <!-- Distance -->
        <g transform="translate({cx + 110}, {cy + 38})">
          <text fill="var(--text)" font-family="var(--font-numeric)"
                font-size="22" font-weight="800" text-anchor="end"
                letter-spacing="-1">{distLineM}m</text>
          <text y="12" fill="var(--text-faint)" font-family="var(--font-mono)"
                font-size="9" text-anchor="end" letter-spacing="1">ALLA LINEA</text>
        </g>
        <!-- Bias label -->
        {#if biasAbs > 0}
          <g transform="translate(20, 20)">
            <text fill="var(--green)" font-family="var(--font-numeric)"
                  font-size="24" font-weight="800"
                  letter-spacing="-1">{biasAbs}&deg;</text>
            <text y="12" fill="var(--text-faint)" font-family="var(--font-mono)"
                  font-size="9" letter-spacing="1">BIAS &rarr; {biasEnd}</text>
          </g>
        {/if}
      </svg>
    </div>
  </div>

  <!-- Strategy -->
  <div class="strategy-section">
    <div class="section-label">STRATEGIA</div>
    <div class="strategy-chips">
      <div class="strategy-chip">
        <span class="chip-label">ESTREMO</span>
        <span class="chip-value" style="color: var(--orange)">{strategyEnd}</span>
      </div>
      <div class="strategy-chip">
        <span class="chip-label">MURA</span>
        <span class="chip-value"
          style="color: {strategyTack === 'PORT' ? 'var(--port)' : 'var(--stbd)'}">
          {strategyTack === "PORT" ? "DX" : "SX"}
        </span>
      </div>
    </div>
  </div>
</div>

<style>
  .page {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-text);
  }

  .header {
    padding: 10px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 1.5px;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  /* ── Timer hero ──────────────────────────── */
  .timer-hero {
    padding: 16px 16px 14px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .timer-label {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .timer-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-top: 2px;
  }
  .timer-number {
    font-family: var(--font-numeric);
    font-size: min(120px, 28vw);
    font-weight: 800;
    letter-spacing: -7px;
    line-height: 0.88;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    flex: 1;
  }
  .timer-status {
    padding: 4px 10px;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    flex-shrink: 0;
    color: var(--text-dim);
    background: var(--surface-alt);
  }
  .timer-status.ontime { background: var(--green); color: #06120a; }
  .timer-status.early { background: var(--orange); color: #1a1305; }
  .timer-status.late { background: var(--red); color: #fff; }
  :global(.app[data-theme="sun"]) .timer-status.ontime,
  :global(.app[data-theme="sun"]) .timer-status.early { color: #fff; }

  /* ── TTL bar ─────────────────────────────── */
  .ttl-bar {
    margin-top: 12px;
    position: relative;
    height: 36px;
  }
  .ttl-zones {
    position: absolute;
    top: 8px;
    left: 0;
    right: 0;
    height: 20px;
    background: var(--surface-alt);
    border-radius: 3px;
    overflow: hidden;
    display: flex;
  }
  .late-zone { flex: 1; background: var(--red); opacity: 0.15; }
  .ok-zone { width: 40px; background: var(--green); opacity: 0.22; }
  .early-zone { flex: 1; background: var(--orange); opacity: 0.15; }
  .ttl-labels {
    position: absolute;
    top: 12px;
    left: 6px;
    right: 6px;
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    pointer-events: none;
  }
  .ttl-late-label { color: var(--red); }
  .ttl-early-label { color: var(--orange); }
  .ttl-center-line {
    position: absolute;
    left: 50%;
    top: 4px;
    bottom: 4px;
    width: 2px;
    background: var(--text);
    margin-left: -1px;
  }
  .ttl-marker {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    transition: left 0.3s;
  }
  .ttl-marker.ontime { border-top: 10px solid var(--green); filter: drop-shadow(0 0 5px var(--green)); }
  .ttl-marker.early { border-top: 10px solid var(--orange); filter: drop-shadow(0 0 5px var(--orange)); }
  .ttl-marker.late { border-top: 10px solid var(--red); filter: drop-shadow(0 0 5px var(--red)); }

  .ttl-info {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 1px;
    margin-top: 8px;
  }

  /* Timer controls */
  .timer-controls {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  .timer-btn {
    flex: 1;
    padding: 10px;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 1px;
    cursor: pointer;
    touch-action: manipulation;
  }
  .timer-btn:active { opacity: 0.6; }
  .timer-btn.stop {
    background: var(--red);
    color: #fff;
    border-color: var(--red);
  }

  /* ── Line bias ───────────────────────────── */
  .bias-section {
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .section-label {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
    margin-bottom: 8px;
  }
  .bias-diagram {
    width: 100%;
  }

  /* ── Strategy ────────────────────────────── */
  .strategy-section {
    flex: 1;
    min-height: 0;
    padding: 14px 16px;
  }
  .strategy-chips {
    display: flex;
    gap: 10px;
    margin-top: 8px;
  }
  .strategy-chip {
    flex: 1;
    padding: 10px 14px;
    background: var(--surface);
    border-radius: 4px;
    border: 1px solid var(--border);
    border-left: 4px solid var(--orange);
  }
  .chip-label {
    display: block;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .chip-value {
    display: block;
    font-family: var(--font-numeric);
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-top: 2px;
    line-height: 1;
  }
</style>
