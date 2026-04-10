<!--
  CalibrationPage — Live instrument calibration with raw vs calibrated comparison.

  Shows each sensor's raw and calibrated value side by side, with
  +/- buttons to adjust offsets in real time. Auto-calibration for
  compass and speed: sail straight for 30s and the system computes
  the correction from GPS.
-->
<script>
  import { onMount, onDestroy } from "svelte";
  import { boatState } from "../stores/boat.js";

  let cal = {
    compass_offset: 0,
    speed_factor: 1,
    awa_offset: 0,
    depth_offset: -1.85,
    tws_downwind_factor: 1,
    magnetic_variation: 2.5,
  };
  let calTimestamps = {};
  let saving = false;
  let feedback = "";

  // Auto-calibration state
  let autoStatus = null;   // null | {status, mode, progress, value, quality, ...}
  let autoPollTimer = null;

  // Live raw/calibrated from WebSocket
  $: raw_hdg = $boatState?.raw_heading_mag;
  $: cal_hdg = $boatState?.heading_mag;
  $: raw_bsp = $boatState?.raw_bsp_kt;
  $: cal_bsp = $boatState?.bsp_kt;
  $: raw_awa = $boatState?.raw_awa_deg;
  $: cal_awa = $boatState?.awa_deg;
  $: raw_depth = $boatState?.raw_depth_m;
  $: cal_depth = $boatState?.depth_m;
  $: raw_aws = $boatState?.raw_aws_kt;
  $: tws = $boatState?.tws_kt;
  $: sog = $boatState?.sog_kt;

  onMount(async () => {
    try {
      const res = await fetch("/api/config");
      const cfg = await res.json();
      cal.compass_offset = cfg.compass_offset ?? 0;
      cal.speed_factor = cfg.speed_factor ?? 1;
      cal.awa_offset = cfg.awa_offset ?? 0;
      cal.depth_offset = cfg.depth_offset ?? -1.85;
      cal.tws_downwind_factor = cfg.tws_downwind_factor ?? 1;
      cal.magnetic_variation = cfg.magnetic_variation ?? 2.5;
      calTimestamps = cfg.cal_timestamps ?? {};
      cal = cal;
    } catch { /* ignore */ }

    // Resume polling if auto-calibration is already running on the backend
    try {
      const res = await fetch("/api/calibration/auto");
      const status = await res.json();
      if (status.status === "collecting" || status.status === "done") {
        autoStatus = status;
        if (status.status === "collecting") {
          autoPollTimer = setInterval(pollAuto, 500);
        }
      }
    } catch { /* ignore */ }
  });

  onDestroy(() => {
    if (autoPollTimer) clearInterval(autoPollTimer);
  });

  async function save(key, value) {
    saving = true;
    try {
      const res = await fetch("/api/calibration", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value }),
      });
      const data = await res.json();
      for (const k of Object.keys(cal)) {
        if (data[k] !== undefined) cal[k] = data[k];
      }
      cal = cal;
      // Refresh timestamps
      try {
        const cfgRes = await fetch("/api/config");
        const cfg = await cfgRes.json();
        calTimestamps = cfg.cal_timestamps ?? {};
      } catch { /* ignore */ }
      showFeedback("Salvato");
    } catch {
      showFeedback("Errore", true);
    }
    saving = false;
  }

  function adjust(key, delta) {
    cal[key] = Math.round((cal[key] + delta) * 1000) / 1000;
    cal = cal;
    save(key, cal[key]);
  }

  // ── Auto-calibration ──────────────────────────────────────
  async function startAuto(mode) {
    try {
      await fetch("/api/calibration/auto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      autoStatus = { status: "collecting", mode, progress: 0 };
      // Poll every 500ms
      if (autoPollTimer) clearInterval(autoPollTimer);
      autoPollTimer = setInterval(pollAuto, 500);
    } catch {
      showFeedback("Errore avvio auto-cal", true);
    }
  }

  async function pollAuto() {
    try {
      const res = await fetch("/api/calibration/auto");
      autoStatus = await res.json();
      if (autoStatus.status === "done" || autoStatus.status === "idle") {
        clearInterval(autoPollTimer);
        autoPollTimer = null;
      }
    } catch { /* ignore */ }
  }

  async function applyAuto() {
    try {
      const res = await fetch("/api/calibration/auto/apply", { method: "POST" });
      const data = await res.json();
      if (data.applied) {
        if (data.mode === "compass") cal.compass_offset = data.value;
        if (data.mode === "speed") cal.speed_factor = data.value;
        cal = cal;
        showFeedback(`Auto-cal applicata: ${data.value}`);
        autoStatus = null;
      }
    } catch (e) {
      showFeedback("Errore applicazione", true);
    }
  }

  async function cancelAuto() {
    try {
      await fetch("/api/calibration/auto/cancel", { method: "POST" });
    } catch { /* ignore */ }
    if (autoPollTimer) clearInterval(autoPollTimer);
    autoPollTimer = null;
    autoStatus = null;
  }

  function fmtCalDate(key) {
    const iso = calTimestamps[key];
    if (!iso) return "mai calibrato";
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return "oggi";
    if (diffDays === 1) return "ieri";
    if (diffDays < 7) return `${diffDays} giorni fa`;
    return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short" });
  }

  function fmtVal(v, decimals = 1) {
    if (v == null) return "---";
    return Number(v).toFixed(decimals);
  }

  function fmtDeg(v) {
    if (v == null) return "---";
    return Number(v).toFixed(1) + "\u00B0";
  }

  let feedbackError = false;
  function showFeedback(msg, isError = false) {
    feedback = msg;
    feedbackError = isError;
    setTimeout(() => (feedback = ""), 3000);
  }

  $: autoCollecting = autoStatus?.status === "collecting";
  $: autoDone = autoStatus?.status === "done";
  $: autoMode = autoStatus?.mode;
  $: autoProgress = autoStatus?.progress ?? 0;
  $: awaInfo = autoStatus?.awa ?? null;

  function modeLabel(m) {
    if (m === "compass") return "BUSSOLA";
    if (m === "speed") return "VELOCITA";
    if (m === "awa") return "AWA";
    return m;
  }

  function qualityColor(q) {
    if (q === "good") return "var(--green)";
    if (q === "fair") return "var(--orange)";
    return "var(--red)";
  }

  function qualityLabel(q) {
    if (q === "good") return "OTTIMA";
    if (q === "fair") return "DISCRETA";
    return "SCARSA";
  }
</script>

<div class="page">
  <h2 class="title">CALIBRAZIONE</h2>

  <!-- Auto-calibration banner -->
  {#if autoCollecting && autoMode !== "awa"}
    <div class="auto-banner collecting">
      <div class="auto-title">AUTO-CAL {modeLabel(autoMode)}</div>
      <div class="auto-hint">Naviga dritto a velocita costante...</div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: {autoProgress * 100}%"></div>
      </div>
      <div class="auto-pct">{Math.round(autoProgress * 100)}%</div>
      <button class="auto-btn cancel" on:click={cancelAuto}>ANNULLA</button>
    </div>
  {:else if autoCollecting && autoMode === "awa"}
    <div class="auto-banner collecting awa">
      <div class="auto-title">AUTO-CAL AWA</div>
      <div class="auto-hint">Naviga di bolina — fai 2+ bordi per lato</div>
      {#if awaInfo}
        <div class="awa-legs-row">
          <div class="awa-leg-box" class:ok={awaInfo.port_legs >= awaInfo.target_per_side}>
            <span class="awa-leg-label">SINISTRA</span>
            <span class="awa-leg-count">{awaInfo.port_legs}/{awaInfo.target_per_side}</span>
          </div>
          <div class="awa-leg-box" class:ok={awaInfo.stbd_legs >= awaInfo.target_per_side}>
            <span class="awa-leg-label">DRITTA</span>
            <span class="awa-leg-count">{awaInfo.stbd_legs}/{awaInfo.target_per_side}</span>
          </div>
        </div>
        {#if awaInfo.current_tack}
          <div class="awa-current">
            Bordo attuale: {awaInfo.current_tack === "port" ? "SINISTRA" : "DRITTA"}
            — {awaInfo.current_leg_s}s / {awaInfo.min_leg_s}s
          </div>
        {/if}
      {/if}
      <div class="progress-bar">
        <div class="progress-fill" style="width: {autoProgress * 100}%"></div>
      </div>
      <button class="auto-btn cancel" on:click={cancelAuto}>ANNULLA</button>
    </div>
  {:else if autoDone}
    <div class="auto-banner done">
      <div class="auto-title">RISULTATO {modeLabel(autoMode)}</div>
      <div class="auto-result-row">
        <span class="auto-result-value">
          {autoStatus.value}{autoMode !== "speed" ? "\u00B0" : ""}
        </span>
        <span class="auto-result-quality" style="color: {qualityColor(autoStatus.quality)}">
          {qualityLabel(autoStatus.quality)}
        </span>
      </div>
      {#if autoMode === "awa" && autoStatus.detail}
        <div class="auto-detail">
          Media SX: {autoStatus.detail.avg_port_awa}&deg; | Media DX: {autoStatus.detail.avg_stbd_awa}&deg;
        </div>
        <div class="auto-detail">
          {autoStatus.detail.port_legs} bordi SX, {autoStatus.detail.stbd_legs} bordi DX, {autoStatus.samples} campioni
        </div>
      {:else}
        <div class="auto-detail">
          {autoStatus.samples} campioni, dev. std. {autoStatus.std_dev}{autoMode === "compass" ? "\u00B0" : ""}
        </div>
      {/if}
      <div class="auto-actions">
        <button class="auto-btn apply" on:click={applyAuto}
          disabled={autoStatus.quality === "poor"}>
          APPLICA
        </button>
        <button class="auto-btn cancel" on:click={() => autoStatus = null}>IGNORA</button>
      </div>
    </div>
  {/if}

  <!-- Compass offset -->
  <div class="section">
    <div class="section-header-row">
      <span class="section-title">Bussola <span class="cal-date">{fmtCalDate("compass")}</span></span>
      <button class="auto-start-btn" on:click={() => startAuto("compass")}
        disabled={autoCollecting}>CALIBRA</button>
    </div>
    <div class="live-row">
      <div class="live-pair">
        <span class="live-label">RAW</span>
        <span class="live-value">{fmtDeg(raw_hdg)}</span>
      </div>
      <div class="live-pair">
        <span class="live-label">COG</span>
        <span class="live-value">{fmtDeg($boatState?.raw_cog_deg)}</span>
      </div>
      <div class="live-pair">
        <span class="live-label">CAL</span>
        <span class="live-value accent">{fmtDeg(cal_hdg)}</span>
      </div>
    </div>
    <div class="cal-row">
      <span class="cal-label">Offset</span>
      <button class="adj-btn" on:click={() => adjust("compass_offset", -1)} disabled={saving}>-1</button>
      <button class="adj-btn small" on:click={() => adjust("compass_offset", -0.1)} disabled={saving}>-.1</button>
      <span class="cal-value">{cal.compass_offset.toFixed(1)}&deg;</span>
      <button class="adj-btn small" on:click={() => adjust("compass_offset", 0.1)} disabled={saving}>+.1</button>
      <button class="adj-btn" on:click={() => adjust("compass_offset", 1)} disabled={saving}>+1</button>
    </div>
  </div>

  <!-- Speed factor -->
  <div class="section">
    <div class="section-header-row">
      <span class="section-title">Velocita (BSP) <span class="cal-date">{fmtCalDate("speed")}</span></span>
      <button class="auto-start-btn" on:click={() => startAuto("speed")}
        disabled={autoCollecting}>CALIBRA</button>
    </div>
    <div class="live-row">
      <div class="live-pair">
        <span class="live-label">RAW</span>
        <span class="live-value">{fmtVal(raw_bsp)} kt</span>
      </div>
      <div class="live-pair">
        <span class="live-label">SOG</span>
        <span class="live-value">{fmtVal(sog)} kt</span>
      </div>
      <div class="live-pair">
        <span class="live-label">CAL</span>
        <span class="live-value accent">{fmtVal(cal_bsp)} kt</span>
      </div>
    </div>
    <div class="cal-row">
      <span class="cal-label">Fattore</span>
      <button class="adj-btn" on:click={() => adjust("speed_factor", -0.05)} disabled={saving}>-.05</button>
      <button class="adj-btn small" on:click={() => adjust("speed_factor", -0.01)} disabled={saving}>-.01</button>
      <span class="cal-value">{cal.speed_factor.toFixed(3)}</span>
      <button class="adj-btn small" on:click={() => adjust("speed_factor", 0.01)} disabled={saving}>+.01</button>
      <button class="adj-btn" on:click={() => adjust("speed_factor", 0.05)} disabled={saving}>+.05</button>
    </div>
  </div>

  <!-- AWA offset -->
  <div class="section">
    <div class="section-header-row">
      <span class="section-title">Angolo Vento Apparente (AWA) <span class="cal-date">{fmtCalDate("awa")}</span></span>
      <button class="auto-start-btn" on:click={() => startAuto("awa")}
        disabled={autoCollecting}>CALIBRA</button>
    </div>
    <div class="live-row">
      <div class="live-pair">
        <span class="live-label">RAW</span>
        <span class="live-value">{fmtDeg(raw_awa)}</span>
      </div>
      <div class="live-pair">
        <span class="live-label">CAL</span>
        <span class="live-value accent">{fmtDeg(cal_awa)}</span>
      </div>
    </div>
    <div class="cal-row">
      <span class="cal-label">Offset</span>
      <button class="adj-btn" on:click={() => adjust("awa_offset", -1)} disabled={saving}>-1</button>
      <button class="adj-btn small" on:click={() => adjust("awa_offset", -0.5)} disabled={saving}>-.5</button>
      <span class="cal-value">{cal.awa_offset.toFixed(1)}&deg;</span>
      <button class="adj-btn small" on:click={() => adjust("awa_offset", 0.5)} disabled={saving}>+.5</button>
      <button class="adj-btn" on:click={() => adjust("awa_offset", 1)} disabled={saving}>+1</button>
    </div>
  </div>

  <!-- Depth offset -->
  <div class="section">
    <div class="section-title">Profondita <span class="cal-date">{fmtCalDate("depth")}</span></div>
    <div class="live-row">
      <div class="live-pair">
        <span class="live-label">RAW</span>
        <span class="live-value">{fmtVal(raw_depth)} m</span>
      </div>
      <div class="live-pair">
        <span class="live-label">CAL</span>
        <span class="live-value accent">{fmtVal(cal_depth)} m</span>
      </div>
    </div>
    <div class="cal-row">
      <span class="cal-label">Offset</span>
      <button class="adj-btn" on:click={() => adjust("depth_offset", -0.1)} disabled={saving}>-.10</button>
      <button class="adj-btn small" on:click={() => adjust("depth_offset", -0.05)} disabled={saving}>-.05</button>
      <span class="cal-value">{cal.depth_offset.toFixed(2)} m</span>
      <button class="adj-btn small" on:click={() => adjust("depth_offset", 0.05)} disabled={saving}>+.05</button>
      <button class="adj-btn" on:click={() => adjust("depth_offset", 0.1)} disabled={saving}>+.10</button>
    </div>
  </div>

  <!-- Magnetic variation -->
  <div class="section">
    <div class="section-title">Variazione Magnetica <span class="cal-date">{fmtCalDate("mag_var")}</span></div>
    <div class="cal-row">
      <span class="cal-label">Declinazione</span>
      <button class="adj-btn" on:click={() => adjust("magnetic_variation", -0.5)} disabled={saving}>-.5</button>
      <button class="adj-btn small" on:click={() => adjust("magnetic_variation", -0.1)} disabled={saving}>-.1</button>
      <span class="cal-value">{cal.magnetic_variation.toFixed(1)}&deg; E</span>
      <button class="adj-btn small" on:click={() => adjust("magnetic_variation", 0.1)} disabled={saving}>+.1</button>
      <button class="adj-btn" on:click={() => adjust("magnetic_variation", 0.5)} disabled={saving}>+.5</button>
    </div>
  </div>

  {#if feedback}
    <div class="feedback" class:error={feedbackError}>{feedback}</div>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    padding: var(--pad-airy);
    gap: var(--gap-airy);
    height: 100%;
    overflow-y: auto;
  }
  .title {
    font-size: 14px;
    letter-spacing: 0.15em;
    color: var(--accent);
    margin: 0;
    text-align: center;
  }
  .section {
    background: var(--card);
    border-radius: 8px;
    padding: 10px 12px;
  }
  .section-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .section-title {
    font-size: var(--label-xs-size);
    text-transform: uppercase;
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
    margin-bottom: 6px;
  }
  .section-header-row .section-title {
    margin-bottom: 0;
  }
  .cal-date {
    font-style: italic;
    opacity: 0.7;
    font-size: 9px;
    letter-spacing: 0.02em;
  }

  /* Auto-cal start button (inline with section title) */
  .auto-start-btn {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 0.1em;
    color: var(--green);
    background: transparent;
    border: 1px solid var(--green);
    border-radius: 4px;
    padding: 3px 8px;
    cursor: pointer;
    touch-action: manipulation;
  }
  .auto-start-btn:active:not(:disabled) { opacity: 0.6; }
  .auto-start-btn:disabled { opacity: 0.3; }

  /* Auto-calibration banner */
  .auto-banner {
    background: var(--card);
    border: 2px solid var(--accent);
    border-radius: 10px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  .auto-banner.done {
    border-color: var(--green);
  }
  .auto-title {
    font-size: var(--label-sm-size);
    font-weight: var(--label-md-weight);
    letter-spacing: var(--label-md-spacing);
    color: var(--accent);
  }
  .auto-banner.done .auto-title {
    color: var(--green);
  }
  .auto-hint {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
  }
  .progress-bar {
    width: 100%;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.4s ease;
  }
  .auto-pct {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 14px;
    font-weight: 700;
    color: var(--accent);
  }
  .auto-result-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }
  .auto-result-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 28px;
    font-weight: 700;
    color: var(--text);
    text-shadow: var(--glow-text);
  }
  .auto-result-quality {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.1em;
  }
  .auto-detail {
    font-size: 10px;
    color: var(--text-dim);
  }
  .auto-actions {
    display: flex;
    gap: 10px;
    margin-top: 4px;
  }
  .auto-btn {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 8px 16px;
    border: 2px solid;
    border-radius: 6px;
    cursor: pointer;
    background: var(--bg);
    touch-action: manipulation;
  }
  .auto-btn:active:not(:disabled) { opacity: 0.6; }
  .auto-btn:disabled { opacity: 0.25; }
  .auto-btn.apply {
    color: var(--green);
    border-color: var(--green);
  }
  .auto-btn.cancel {
    color: var(--text-dim);
    border-color: var(--border);
  }

  /* AWA tack-symmetry display */
  .awa-legs-row {
    display: flex;
    gap: 16px;
    justify-content: center;
  }
  .awa-leg-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 8px 16px;
    border: 2px solid var(--border);
    border-radius: 8px;
    min-width: 80px;
  }
  .awa-leg-box.ok {
    border-color: var(--green);
  }
  .awa-leg-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-dim);
  }
  .awa-leg-count {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
  }
  .awa-leg-box.ok .awa-leg-count {
    color: var(--green);
    text-shadow: var(--glow-green);
  }
  .awa-current {
    font-size: 11px;
    color: var(--accent);
    font-weight: 600;
    text-align: center;
  }

  /* Live raw/cal comparison */
  .live-row {
    display: flex;
    justify-content: space-around;
    margin-bottom: 8px;
  }
  .live-pair {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .live-label {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
  }
  .live-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
    text-shadow: var(--glow-text);
  }
  .live-value.accent {
    color: var(--accent);
    text-shadow: var(--glow-accent);
  }

  /* Calibration adjustment row */
  .cal-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .cal-label {
    font-size: var(--label-sm-size);
    color: var(--text-dim);
    min-width: 60px;
  }
  .cal-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    min-width: 64px;
    text-align: center;
  }
  .adj-btn {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
    font-weight: 700;
    color: var(--accent);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 8px;
    min-width: 38px;
    cursor: pointer;
    touch-action: manipulation;
    transition: opacity 0.15s;
  }
  .adj-btn.small {
    font-size: 10px;
    padding: 6px 5px;
    min-width: 32px;
    color: var(--text-dim);
  }
  .adj-btn:active:not(:disabled) {
    opacity: 0.6;
    background: var(--border);
  }
  .adj-btn:disabled {
    opacity: 0.3;
  }

  .feedback {
    font-size: 12px;
    color: var(--green);
    font-weight: 600;
    text-align: center;
    letter-spacing: 0.5px;
  }
  .feedback.error {
    color: var(--red);
  }

  @media (max-width: 480px) {
    .live-value { font-size: 16px; }
    .adj-btn { padding: 6px 5px; min-width: 32px; font-size: 11px; }
    .adj-btn.small { font-size: 9px; min-width: 28px; }
    .cal-label { min-width: 50px; font-size: 10px; }
    .cal-value { font-size: 13px; min-width: 56px; }
    .auto-result-value { font-size: 22px; }
  }
</style>
