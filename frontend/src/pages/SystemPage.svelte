<!--
  SystemPage — System status and diagnostics.
-->
<script>
  import { onMount } from "svelte";
  import InstrumentField from "../components/InstrumentField.svelte";
  import { connectionStatus, gpsFix, boatState } from "../stores/boat.js";
  import { fmt } from "../lib/formatting.js";

  $: headingAge = $boatState?.heading_age_ms ?? 9999;
  $: windAge = $boatState?.wind_age_ms ?? 9999;
  $: bspAge = $boatState?.bsp_age_ms ?? 9999;
  $: depthAge = $boatState?.depth_age_ms ?? 9999;

  function ageStatus(ms) {
    if (ms < 2000) return "ok";
    if (ms < 5000) return "stale";
    return "dead";
  }

  function ageColor(ms) {
    if (ms < 2000) return "var(--green)";
    if (ms < 5000) return "var(--orange)";
    return "var(--red)";
  }

  // Data source mode
  let currentSource = "…";
  let switching = false;

  // Session logs
  let logs = [];
  let logsLoading = false;
  let disk = null;

  async function loadLogs() {
    logsLoading = true;
    try {
      const res = await fetch("/api/logs");
      logs = await res.json();
    } catch { /* ignore */ }
    logsLoading = false;
  }

  function fmtSize(kb) {
    if (kb >= 1024) return (kb / 1024).toFixed(1) + " MB";
    return kb.toFixed(0) + " KB";
  }

  function fmtDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" })
      + " " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  }

  onMount(async () => {
    try {
      const res = await fetch("/api/source");
      const data = await res.json();
      currentSource = data.source;
    } catch { /* ignore */ }
    loadLogs();
    try {
      const dr = await fetch("/api/system/disk");
      disk = await dr.json();
    } catch { /* ignore */ }
  });

  $: isBoatMode = currentSource === "can0";

  async function toggleSource() {
    const newSource = isBoatMode ? "interactive" : "can0";
    switching = true;
    try {
      const res = await fetch("/api/source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: newSource }),
      });
      const data = await res.json();
      currentSource = data.source;
    } catch { /* ignore */ }
    switching = false;
  }
</script>

<div class="page">
  <h2 class="title">SYSTEM</h2>

  <div class="section mode-section">
    <div class="section-title">Data Source</div>
    <div class="mode-row">
      <span class="mode-label" class:active={!isBoatMode}>SIM</span>
      <button class="toggle" class:boat={isBoatMode} on:click={toggleSource} disabled={switching}>
        <span class="toggle-knob"></span>
      </button>
      <span class="mode-label" class:active={isBoatMode}>BOAT</span>
    </div>
    <div class="mode-status">
      {#if switching}
        Switching…
      {:else}
        {currentSource === "can0" ? "CAN bus (live sensors)" : currentSource === "interactive" ? "Interactive sim" : "Simulator"}
      {/if}
    </div>
  </div>

  <div class="section">
    <div class="section-title">Connection</div>
    <div class="row">
      <span class="label">WebSocket</span>
      <span class="value" style:color={$connectionStatus === "connected" ? "var(--green)" : "var(--red)"}>
        {$connectionStatus}
      </span>
    </div>
    <div class="row">
      <span class="label">GPS Fix</span>
      <span class="value" style:color={$gpsFix ? "var(--green)" : "var(--red)"}>
        {$gpsFix ? "YES" : "NO"}
      </span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Sensor Health</div>
    <div class="row">
      <span class="label">Compass</span>
      <span class="value" style:color={ageColor(headingAge)}>{ageStatus(headingAge)}</span>
    </div>
    <div class="row">
      <span class="label">Wind</span>
      <span class="value" style:color={ageColor(windAge)}>{ageStatus(windAge)}</span>
    </div>
    <div class="row">
      <span class="label">Speed</span>
      <span class="value" style:color={ageColor(bspAge)}>{ageStatus(bspAge)}</span>
    </div>
    <div class="row">
      <span class="label">Depth</span>
      <span class="value" style:color={ageColor(depthAge)}>{ageStatus(depthAge)}</span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Session Logs</div>
    {#if logsLoading}
      <div class="row"><span class="label">Loading…</span></div>
    {:else if logs.length === 0}
      <div class="row"><span class="label">No sessions yet</span></div>
    {:else}
      {#each logs as log}
        <a class="log-row" href="/api/logs/{log.name}" download={log.name}>
          <span class="log-date">{fmtDate(log.modified)}</span>
          <span class="log-size">{fmtSize(log.size_kb)}</span>
        </a>
      {/each}
    {/if}
  </div>

  {#if disk}
    <div class="section">
      <div class="section-title">Memoria</div>
      <div class="row">
        <span class="label">Disco libero</span>
        <span class="value" style:color={disk.free_pct < 10 ? "var(--red)" : disk.free_pct < 25 ? "var(--orange)" : "var(--green)"}>
          {disk.free_mb} MB ({disk.free_pct}%)
        </span>
      </div>
      <div class="row">
        <span class="label">Sessioni CSV</span>
        <span class="value">{disk.csv_mb} MB</span>
      </div>
      <div class="row">
        <span class="label">Database</span>
        <span class="value">{disk.db_mb} MB</span>
      </div>
    </div>
  {/if}

  <div class="section">
    <div class="section-title">Software</div>
    <div class="row">
      <span class="label">Version</span>
      <span class="value">0.1.0</span>
    </div>
  </div>
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
    padding: 10px 14px;
  }
  .section-title {
    font-size: var(--label-xs-size);
    text-transform: uppercase;
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
    margin-bottom: 8px;
  }
  .row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 13px;
  }
  .label {
    color: var(--text-dim);
  }
  .value {
    font-family: "SF Mono", "Menlo", monospace;
    color: var(--text);
  }

  /* Mode toggle */
  .mode-section {
    text-align: center;
  }
  .mode-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 8px 0;
  }
  .mode-label {
    font-size: var(--label-md-size);
    font-weight: var(--label-md-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
    transition: color 0.2s;
  }
  .mode-label.active {
    color: var(--accent);
  }
  .toggle {
    position: relative;
    width: 52px;
    height: 28px;
    border-radius: 14px;
    border: 2px solid var(--border);
    background: var(--card);
    cursor: pointer;
    padding: 0;
    transition: background 0.2s, border-color 0.2s;
  }
  .toggle:disabled {
    opacity: 0.5;
  }
  .toggle.boat {
    background: var(--green);
    border-color: var(--green);
  }
  .toggle-knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--text);
    transition: transform 0.2s;
  }
  .toggle.boat .toggle-knob {
    transform: translateX(24px);
  }
  .mode-status {
    font-size: 11px;
    color: var(--text-dim);
    padding-bottom: 2px;
  }

  /* Session logs */
  .log-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    text-decoration: none;
    color: var(--text);
    -webkit-tap-highlight-color: rgba(0, 180, 216, 0.15);
  }
  .log-row:last-child {
    border-bottom: none;
  }
  .log-row:active {
    background: rgba(0, 180, 216, 0.1);
  }
  .log-date {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 13px;
  }
  .log-size {
    font-size: 12px;
    color: var(--text-dim);
  }
</style>
