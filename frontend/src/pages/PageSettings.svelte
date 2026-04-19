<!--
  PageSettings — "Impostazioni" — Technical settings tab.

  Hierarchy by frequency of use:
    1. Pi status hero (checked often)
    2. Preferences (theme, units, language, boat profile)
    3. Software update
    4. Diagnostics (share to Telegram for remote support)
    5. About (version footer)
-->
<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { connectionStatus } from "../stores/boat.js";

  export let theme = "dark";
  const dispatch = createEventDispatcher();

  // Pi status state
  let piStatus = null;
  let piLoading = true;
  let version = null;
  let latestVersion = null;
  let updateSteps = null;
  let updateRunning = false;

  // Preferences
  let speedUnit = "kt";
  let distUnit = "nm";
  let lang = "IT";

  const themeOptions = [
    { key: "dark", label: "Notte" },
    { key: "light", label: "Giorno" },
    { key: "sun", label: "Sole" },
  ];

  function selectTheme(t) {
    dispatch("theme", t);
  }

  // Fetch Pi health
  async function fetchHealth() {
    try {
      const r = await fetch("/api/system/health");
      if (r.ok) piStatus = await r.json();
    } catch (e) {
      piStatus = null;
    }
    piLoading = false;
  }

  // Fetch version info
  async function fetchVersion() {
    try {
      const r = await fetch("/api/system/version");
      if (r.ok) {
        const v = await r.json();
        version = v;
      }
    } catch (e) { /* ignore */ }
    try {
      const r = await fetch("/api/system/latest-version");
      if (r.ok) latestVersion = await r.json();
    } catch (e) { /* ignore */ }
  }

  // Run OTA update
  async function runUpdate() {
    updateRunning = true;
    updateSteps = [];
    try {
      const r = await fetch("/api/system/update", { method: "POST" });
      if (r.ok) {
        const result = await r.json();
        updateSteps = result.steps || [];
        await fetchVersion();
        await fetchHealth();
      }
    } catch (e) {
      updateSteps = [{ step: "error", output: e.message, ok: false }];
    }
    updateRunning = false;
  }

  // Diagnostics
  let diagResult = null;
  let diagRunning = false;

  async function runDiag(type) {
    diagRunning = true;
    diagResult = null;
    try {
      let r;
      if (type === "health") {
        r = await fetch("/api/system/health");
      } else if (type === "can") {
        r = await fetch("/api/system/can-dump", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ seconds: 30 }),
        });
      } else if (type === "ble") {
        r = await fetch("/api/system/ble-scan");
      }
      if (r && r.ok) diagResult = { type, data: await r.json() };
    } catch (e) {
      diagResult = { type, error: e.message };
    }
    diagRunning = false;
  }

  // Sensor status helper
  function sensorColor(status) {
    if (status === "ok") return "var(--green)";
    if (status === "slow") return "var(--orange)";
    return "var(--red)";
  }

  // Pi connection state
  $: piConnected = $connectionStatus === "connected";
  $: piState = piConnected ? "connected" : $connectionStatus === "connecting" ? "searching" : "offline";
  $: piLabel = piState === "connected" ? "CONNESSO" : piState === "searching" ? "IN RICERCA" : "NON RAGGIUNGIBILE";
  $: piColor = piState === "connected" ? "var(--green)" : piState === "searching" ? "var(--orange)" : "var(--red)";

  function fmtUptime(s) {
    if (s == null) return "---";
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`;
    return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
  }

  function fmtDisk(mb) {
    if (mb == null) return "---";
    return `${(mb / 1024).toFixed(1)} GB`;
  }

  onMount(() => {
    fetchHealth();
    fetchVersion();
  });
</script>

<div class="settings-page">
  <!-- Title bar -->
  <div class="title-bar">
    <div class="title-section">MENU</div>
    <div class="title-text">Impostazioni</div>
  </div>

  <!-- 1. Pi status hero -->
  <div class="pi-card" style="border-left-color: {piColor}">
    <div class="pi-header">
      <div class="pi-info">
        <span class="pi-section-label">STATO PI</span>
        <span class="pi-status" style="color: {piColor}">{piLabel}</span>
        <span class="pi-url">{piStatus?.base_url || "---"}</span>
      </div>
      <div class="pi-dot-container">
        <div class="pi-dot-bg" style="background: {piColor}"></div>
        <div class="pi-dot" style="background: {piColor}"></div>
        {#if piState === "connected"}
          <div class="pi-dot-pulse" style="border-color: {piColor}"></div>
        {/if}
      </div>
    </div>

    {#if piStatus}
      <div class="pi-grid">
        <div class="info-row">
          <span class="info-label">Sorgente</span>
          <span class="info-value">{piStatus.source || "---"}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Uptime</span>
          <span class="info-value">{fmtUptime(piStatus.uptime_s)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Pipeline</span>
          <span class="info-value">{piStatus.pipeline_hz?.toFixed(1) ?? "---"} Hz</span>
        </div>
        <div class="info-row">
          <span class="info-label">CPU</span>
          <span class="info-value"
            class:warn={piStatus.cpu_temp_c > 70}>
            {piStatus.cpu_temp_c?.toFixed(0) ?? "---"}&deg;C
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">Disco</span>
          <span class="info-value">{fmtDisk(piStatus.disk_free_mb)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Errori 1h</span>
          <span class="info-value"
            class:warn={piStatus.errors_last_hour > 0}>
            {piStatus.errors_last_hour ?? "---"}
          </span>
        </div>
      </div>

      <!-- Sensor chips -->
      {#if piStatus.sensor_ages_ms}
        <div class="sensor-section">
          <div class="sensor-header">
            <span>SENSORI</span>
          </div>
          <div class="sensor-chips">
            {#each Object.entries(piStatus.sensor_ages_ms) as [key, ageMs]}
              {@const status = ageMs < 500 ? "ok" : ageMs < 2000 ? "slow" : "stale"}
              <div class="sensor-chip">
                <div class="sensor-dot" style="background: {sensorColor(status)}"></div>
                <span>{key.toUpperCase()}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}
  </div>

  <!-- 2. Preferences -->
  <div class="section-header">
    <span class="section-label">PREFERENZE</span>
  </div>
  <div class="pref-row">
    <span class="pref-label">Tema</span>
    <div class="pref-options">
      {#each themeOptions as opt}
        <button class="pref-option" class:active={theme === opt.key}
          on:click={() => selectTheme(opt.key)}>
          {opt.label}
        </button>
      {/each}
    </div>
  </div>
  <div class="pref-row">
    <span class="pref-label">Velocit&agrave;</span>
    <div class="pref-options">
      {#each ["kt", "m/s", "km/h"] as u}
        <button class="pref-option" class:active={speedUnit === u}
          on:click={() => speedUnit = u}>
          {u}
        </button>
      {/each}
    </div>
  </div>
  <div class="pref-row">
    <span class="pref-label">Distanza</span>
    <div class="pref-options">
      {#each ["nm", "m"] as u}
        <button class="pref-option" class:active={distUnit === u}
          on:click={() => distUnit = u}>
          {u}
        </button>
      {/each}
    </div>
  </div>
  <div class="pref-row">
    <span class="pref-label">Lingua</span>
    <div class="pref-options">
      {#each ["IT", "EN"] as l}
        <button class="pref-option" class:active={lang === l}
          on:click={() => lang = l}>
          {l}
        </button>
      {/each}
    </div>
  </div>

  <!-- 3. Software update -->
  <div class="section-header">
    <span class="section-label">AGGIORNAMENTO SOFTWARE</span>
  </div>
  <div class="update-card">
    <div class="update-versions">
      <div class="update-col">
        <span class="update-label">INSTALLATO</span>
        <span class="update-sha">{version?.sha ?? "---"}</span>
        <span class="update-msg">{version?.message ?? ""}</span>
      </div>
      <span class="update-arrow"
        class:has-update={latestVersion && version && latestVersion.sha !== version.sha}>
        &rarr;
      </span>
      <div class="update-col">
        <span class="update-label"
          class:has-update={latestVersion && version && latestVersion.sha !== version.sha}>
          ULTIMO{latestVersion && version && latestVersion.sha !== version.sha ? " · NUOVO" : ""}
        </span>
        <span class="update-sha"
          class:has-update={latestVersion && version && latestVersion.sha !== version.sha}>
          {latestVersion?.sha ?? "---"}
        </span>
        <span class="update-msg">{latestVersion?.message ?? ""}</span>
      </div>
    </div>

    {#if updateSteps}
      <div class="update-steps">
        {#each updateSteps as step}
          <div class="update-step">
            <div class="step-dot" class:ok={step.ok} class:fail={!step.ok}>
              {step.ok ? "\u2713" : "\u00D7"}
            </div>
            <div class="step-info">
              <span class="step-name">{step.step}</span>
              {#if step.output}
                <span class="step-output">{step.output}</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}

    <button class="update-btn"
      class:has-update={latestVersion && version && latestVersion.sha !== version.sha}
      disabled={updateRunning}
      on:click={runUpdate}>
      {updateRunning ? "AGGIORNAMENTO..." :
       latestVersion && version && latestVersion.sha !== version.sha ? "AGGIORNA PI" : "GI\u00C0 AGGIORNATO"}
    </button>
  </div>

  <!-- 4. Diagnostics -->
  <div class="section-header">
    <span class="section-label">DIAGNOSTICA</span>
    <span class="section-sub">Report condivisi su Telegram per assistenza remota</span>
  </div>
  <button class="diag-row" on:click={() => runDiag("health")} disabled={diagRunning}>
    <div class="diag-icon">&zwnj;&#9889;</div>
    <div class="diag-info">
      <span class="diag-title">Diagnostica rapida</span>
      <span class="diag-sub">health + ultimi 20 log</span>
    </div>
    <span class="diag-duration">~2s</span>
    <span class="diag-chevron">&rsaquo;</span>
  </button>
  <button class="diag-row" on:click={() => runDiag("can")} disabled={diagRunning}>
    <div class="diag-icon">&#9636;</div>
    <div class="diag-info">
      <span class="diag-title">CAN Dump</span>
      <span class="diag-sub">dump NMEA2000 / PGN sconosciuti</span>
    </div>
    <span class="diag-duration">30s</span>
    <span class="diag-chevron">&rsaquo;</span>
  </button>
  <button class="diag-row" on:click={() => runDiag("ble")} disabled={diagRunning}>
    <div class="diag-icon">&#9121;</div>
    <div class="diag-info">
      <span class="diag-title">BLE Scan</span>
      <span class="diag-sub">dispositivi Bluetooth vicini</span>
    </div>
    <span class="diag-duration">10s</span>
    <span class="diag-chevron">&rsaquo;</span>
  </button>

  <!-- 5. About footer -->
  <div class="about-footer">
    <div>aquarela &middot; v{version?.sha ?? "---"}</div>
    <div>&copy; 2026 tommymancer</div>
  </div>
</div>

<style>
  .settings-page {
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-text);
    overflow-y: auto;
  }

  /* ── Title bar ───────────────────────────── */
  .title-bar {
    padding: 18px 18px 12px;
    border-bottom: 1px solid var(--border);
  }
  .title-section {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .title-text {
    font-family: var(--font-text);
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.5px;
    margin-top: 2px;
  }

  /* ── Pi status card ──────────────────────── */
  .pi-card {
    margin: 12px 12px 4px;
    padding: 14px 14px 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    border-left: 4px solid var(--green);
  }
  .pi-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }
  .pi-info { flex: 1; min-width: 0; }
  .pi-section-label {
    display: block;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .pi-status {
    display: block;
    font-family: var(--font-numeric);
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1.1;
    margin-top: 2px;
  }
  .pi-url {
    display: block;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pi-dot-container {
    position: relative;
    width: 36px;
    height: 36px;
    flex-shrink: 0;
  }
  .pi-dot-bg {
    position: absolute;
    inset: 0;
    border-radius: 18px;
    opacity: 0.2;
  }
  .pi-dot {
    position: absolute;
    inset: 10px;
    border-radius: 8px;
  }
  .pi-dot-pulse {
    position: absolute;
    inset: 6px;
    border-radius: 12px;
    border: 2px solid;
    opacity: 0.5;
    animation: aqpulse 2s infinite;
  }

  .pi-grid {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 16px;
  }
  .info-row {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .info-label {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-faint);
    letter-spacing: 1.5px;
  }
  .info-value {
    font-family: var(--font-numeric);
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .info-value.warn { color: var(--orange); }

  .sensor-section {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .sensor-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .sensor-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .sensor-chip {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 7px;
    border-radius: 3px;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.5px;
    color: var(--text);
    font-weight: 700;
  }
  .sensor-dot {
    width: 5px;
    height: 5px;
    border-radius: 3px;
  }

  /* ── Section headers ─────────────────────── */
  .section-header {
    padding: 18px 18px 6px;
  }
  .section-label {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
    text-transform: uppercase;
  }
  .section-sub {
    display: block;
    font-family: var(--font-text);
    font-size: 11px;
    color: var(--text-faint);
    margin-top: 3px;
    line-height: 1.4;
  }

  /* ── Preference rows ─────────────────────── */
  .pref-row {
    margin: 0 12px;
    padding: 12px 14px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .pref-row:first-of-type {
    border-top: 1px solid var(--border);
  }
  .pref-label {
    font-family: var(--font-text);
    font-size: 14px;
    color: var(--text);
    font-weight: 500;
    flex: 1;
  }
  .pref-options {
    display: flex;
    gap: 2px;
  }
  .pref-option {
    padding: 4px 10px;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    white-space: nowrap;
    background: transparent;
    color: var(--text-dim);
    border: 1px solid var(--border);
    cursor: pointer;
    touch-action: manipulation;
  }
  .pref-option.active {
    background: var(--accent);
    border-color: var(--accent);
  }
  :global(.app[data-theme="dark"]) .pref-option.active { color: #06120a; }
  :global(.app[data-theme="light"]) .pref-option.active { color: #fff; }
  :global(.app[data-theme="sun"]) .pref-option.active { color: #fff; }

  /* ── Update card ─────────────────────────── */
  .update-card {
    margin: 0 12px 4px;
    padding: 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
  .update-versions {
    display: grid;
    grid-template-columns: 1fr 12px 1fr;
    gap: 12px;
    align-items: center;
  }
  .update-col { min-width: 0; }
  .update-label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 1.5px;
    color: var(--text-faint);
    font-weight: 700;
  }
  .update-label.has-update { color: var(--accent); }
  .update-sha {
    display: block;
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: 0.5px;
    margin-top: 2px;
  }
  .update-sha.has-update { color: var(--accent); }
  .update-msg {
    display: block;
    font-family: var(--font-text);
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .update-arrow {
    font-family: var(--font-mono);
    font-size: 16px;
    color: var(--text-faint);
    text-align: center;
    font-weight: 800;
  }
  .update-arrow.has-update { color: var(--accent); }

  .update-steps {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .update-step {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text);
  }
  .step-dot {
    width: 14px;
    height: 14px;
    border-radius: 7px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 9px;
    font-weight: 900;
    line-height: 1;
  }
  .step-dot.ok { background: var(--green); }
  .step-dot.fail { background: var(--red); }
  .step-info { flex: 1; min-width: 0; }
  .step-name { font-weight: 700; }
  .step-output {
    display: block;
    color: var(--text-dim);
    font-size: 10px;
    margin-top: 1px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .update-btn {
    width: 100%;
    margin-top: 12px;
    padding: 12px;
    background: transparent;
    color: var(--text-dim);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1.5px;
    cursor: default;
    touch-action: manipulation;
  }
  .update-btn.has-update {
    background: var(--accent);
    border: none;
    cursor: pointer;
  }
  :global(.app[data-theme="dark"]) .update-btn.has-update { color: #06120a; }
  :global(.app[data-theme="light"]) .update-btn.has-update { color: #fff; }
  :global(.app[data-theme="sun"]) .update-btn.has-update { color: #fff; }

  /* ── Diagnostics rows ────────────────────── */
  .diag-row {
    margin: 0 12px;
    padding: 12px 14px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    touch-action: manipulation;
    width: calc(100% - 24px);
    text-align: left;
  }
  .diag-row:first-of-type {
    border-top: 1px solid var(--border);
  }
  .diag-row:active { opacity: 0.6; }
  .diag-icon {
    width: 36px;
    height: 36px;
    border-radius: 4px;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 800;
    color: var(--text);
    flex-shrink: 0;
  }
  .diag-info { flex: 1; min-width: 0; }
  .diag-title {
    display: block;
    font-family: var(--font-text);
    font-size: 14px;
    color: var(--text);
    font-weight: 600;
  }
  .diag-sub {
    display: block;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.5px;
    margin-top: 2px;
  }
  .diag-duration {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 1px;
    font-weight: 700;
  }
  .diag-chevron {
    font-size: 16px;
    color: var(--text-dim);
    flex-shrink: 0;
  }

  /* ── About footer ────────────────────────── */
  .about-footer {
    padding: 18px 18px 26px;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 0.5px;
    line-height: 1.6;
  }
</style>
