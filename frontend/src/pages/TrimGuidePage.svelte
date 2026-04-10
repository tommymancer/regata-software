<!--
  TrimGuidePage — Step-by-step guided sail trim procedure.

  Reads current conditions, fetches recommendations, and walks the crew
  through each control one at a time. At the end, saves a trim snapshot.
-->
<script>
  import { onDestroy } from "svelte";
  import { tws, twa, bsp, perfPct, boatState } from "../stores/boat.js";
  import { fmtSpeed, fmtSignedAngle, fmtPct } from "../lib/formatting.js";

  let guide = null;
  let step = -1;         // -1 = conditions screen, 0..N = trim steps, N+1 = review
  let loading = false;
  let error = "";
  let seaState = "";
  let savedMessage = "";

  // Track what the user actually set (may differ from recommendation)
  let userSettings = {};

  const seaStates = [
    { key: "", label: "AUTO" },
    { key: "flat", label: "PIATTA" },
    { key: "choppy", label: "CORTA" },
    { key: "rough", label: "ONDA" },
  ];

  const settingLabels = { light: "L", medium: "M", heavy: "H" };
  const settingNames = { light: "Leggero", medium: "Medio", heavy: "Pesante" };
  const levels = ["light", "medium", "heavy"];

  let showTest = false;

  $: totalSteps = guide?.total_steps ?? 0;
  $: currentStep = guide?.steps?.[step] ?? null;
  $: isReview = step >= totalSteps;
  $: isConditions = step < 0;

  function settingColor(val) {
    if (val === "light") return "var(--green)";
    if (val === "medium") return "var(--orange)";
    if (val === "heavy") return "var(--red)";
    return "var(--text-dim)";
  }

  async function startGuide() {
    loading = true;
    error = "";
    try {
      let url = "/api/trim/guide";
      if (seaState) url += `?sea_state=${seaState}`;
      const res = await fetch(url);
      if (!res.ok) {
        const data = await res.json();
        error = data.detail || "Errore";
        loading = false;
        return;
      }
      guide = await res.json();
      // Initialize user settings with recommendations
      userSettings = {};
      for (const s of guide.steps) {
        userSettings[s.control] = s.setting;
      }
      step = 0;
    } catch {
      error = "Connessione persa";
    }
    loading = false;
  }

  function cycleSetting(control) {
    const cur = userSettings[control];
    const idx = levels.indexOf(cur);
    userSettings[control] = levels[(idx + 1) % levels.length];
    userSettings = userSettings;
  }

  function next() {
    if (step < totalSteps) { step++; showTest = false; }
  }

  function prev() {
    if (step > 0) { step--; showTest = false; }
    else if (step === 0) { step = -1; guide = null; showTest = false; }
  }

  async function saveSnapshot() {
    const params = new URLSearchParams();
    for (const s of guide.steps) {
      params.set(s.control, userSettings[s.control] || "");
    }
    params.set("notes", `Trim Guide: ${guide.wind_range_label} / ${guide.point_of_sail_label}`);
    params.set("sea_state", guide.sea_state || "");
    try {
      const res = await fetch(`/api/trim?${params}`, { method: "POST" });
      if (res.ok) {
        savedMessage = "Salvato nel Trim Book";
        setTimeout(() => (savedMessage = ""), 3000);
      }
    } catch { /* ignore */ }
  }

  function restart() {
    step = -1;
    guide = null;
    savedMessage = "";
    error = "";
  }

  // Live perf% tracking during procedure
  let perfHistory = [];
  let perfTimer;
  $: if (step >= 0 && $perfPct != null) {
    clearTimeout(perfTimer);
    perfTimer = setTimeout(() => {
      perfHistory = [...perfHistory.slice(-29), $perfPct];
    }, 1000);
  }
  onDestroy(() => clearTimeout(perfTimer));
  $: avgPerf = perfHistory.length > 0
    ? (perfHistory.reduce((a, b) => a + b, 0) / perfHistory.length).toFixed(0)
    : null;
</script>

<div class="page">
  {#if isConditions}
    <!-- Step 0: Conditions -->
    <h2 class="title">TRIM GUIDE</h2>

    <div class="conditions-card">
      <div class="cond-row">
        <div class="cond-item">
          <span class="cond-label">TWS</span>
          <span class="cond-value">{$tws != null ? $tws.toFixed(1) : "---"}</span>
          <span class="cond-unit">kt</span>
        </div>
        <div class="cond-item">
          <span class="cond-label">TWA</span>
          <span class="cond-value">{$twa != null ? Math.abs($twa).toFixed(0) : "---"}</span>
          <span class="cond-unit">&deg;</span>
        </div>
        <div class="cond-item">
          <span class="cond-label">PERF</span>
          <span class="cond-value">{$perfPct != null ? $perfPct.toFixed(0) : "---"}</span>
          <span class="cond-unit">%</span>
        </div>
      </div>
    </div>

    <div class="sea-section">
      <span class="sea-title">STATO MARE</span>
      <div class="sea-row">
        {#each seaStates as ss}
          <button class="sea-btn" class:active={seaState === ss.key}
            on:click={() => (seaState = ss.key)}>
            {ss.label}
          </button>
        {/each}
      </div>
    </div>

    {#if error}
      <div class="error-msg">{error}</div>
    {/if}

    <button class="start-btn" on:click={startGuide} disabled={loading || $tws == null}>
      {loading ? "..." : "INIZIA PROCEDURA"}
    </button>

  {:else if !isReview && currentStep}
    <!-- Trim step -->
    <div class="step-header">
      <button class="nav-btn" on:click={prev}>&larr;</button>
      <div class="step-info">
        <span class="step-count">{step + 1} / {totalSteps}</span>
        <span class="step-context">
          {guide.wind_range_label} &middot; {guide.point_of_sail_label}
        </span>
      </div>
      <button class="nav-btn" on:click={next}>&rarr;</button>
    </div>

    <div class="step-progress">
      {#each guide.steps as s, i}
        <div class="step-dot" class:done={i < step} class:current={i === step}></div>
      {/each}
    </div>

    <div class="step-card">
      <div class="step-label">{currentStep.label}</div>

      <button class="setting-btn" on:click={() => cycleSetting(currentStep.control)}
        style="border-color: {settingColor(userSettings[currentStep.control])}">
        <span class="setting-letter" style="color: {settingColor(userSettings[currentStep.control])}">
          {settingLabels[userSettings[currentStep.control]] || "—"}
        </span>
        <span class="setting-name">
          {settingNames[userSettings[currentStep.control]] || ""}
        </span>
      </button>

      {#if userSettings[currentStep.control] !== currentStep.setting}
        <div class="rec-badge">
          Consigliato: {settingNames[currentStep.setting]}
        </div>
      {/if}

      <div class="instruction">{currentStep.instruction}</div>
      <div class="why">{currentStep.why}</div>

      {#if currentStep.test}
        <button class="test-toggle" class:open={showTest}
          on:click={() => (showTest = !showTest)}>
          <span class="test-toggle-icon">{showTest ? "▾" : "▸"}</span>
          VERIFICA
        </button>
        {#if showTest}
          <div class="test-box">
            {currentStep.test}
          </div>
        {/if}
      {/if}
    </div>

    <!-- Live performance monitor -->
    {#if avgPerf != null}
      <div class="perf-monitor">
        <span class="perf-label">PERF MEDIA</span>
        <span class="perf-value">{avgPerf}%</span>
      </div>
    {/if}

    <div class="step-actions">
      <button class="action-btn secondary" on:click={prev}>INDIETRO</button>
      <button class="action-btn primary" on:click={next}>
        {step < totalSteps - 1 ? "AVANTI" : "RIEPILOGO"}
      </button>
    </div>

  {:else if isReview && guide}
    <!-- Review -->
    <h2 class="title">RIEPILOGO TRIM</h2>

    <div class="review-context">
      {guide.wind_range_label} &middot; {guide.point_of_sail_label}
      &middot; TWS {guide.tws_kt} kt
      {#if guide.sea_state}
        &middot; Mare: {guide.sea_state}
      {/if}
    </div>

    <div class="review-grid">
      {#each guide.steps as s}
        <div class="review-item">
          <span class="review-label">{s.label}</span>
          <span class="review-value"
            style="color: {settingColor(userSettings[s.control])}"
          >
            {settingLabels[userSettings[s.control]] || "—"}
          </span>
          {#if userSettings[s.control] !== s.setting}
            <span class="review-diff">({settingLabels[s.setting]})</span>
          {/if}
        </div>
      {/each}
    </div>

    {#if avgPerf != null}
      <div class="perf-monitor big">
        <span class="perf-label">PERF MEDIA</span>
        <span class="perf-value">{avgPerf}%</span>
      </div>
    {/if}

    {#if savedMessage}
      <div class="saved-msg">{savedMessage}</div>
    {/if}

    <div class="review-actions">
      <button class="action-btn secondary" on:click={() => step--}>MODIFICA</button>
      <button class="action-btn primary" on:click={saveSnapshot}>SALVA</button>
      <button class="action-btn accent" on:click={restart}>NUOVA</button>
    </div>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    align-items: center;
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
  }

  /* Conditions screen */
  .conditions-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    width: 100%;
  }
  .cond-row {
    display: flex;
    justify-content: space-around;
  }
  .cond-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .cond-label {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
  }
  .cond-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 28px;
    font-weight: 700;
    color: var(--text);
    text-shadow: var(--glow-text);
  }
  .cond-unit {
    font-size: 10px;
    color: var(--text-dim);
  }

  .sea-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  .sea-title {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
  }
  .sea-row {
    display: flex;
    gap: 6px;
  }
  .sea-btn {
    padding: 8px 14px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-dim);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    cursor: pointer;
    touch-action: manipulation;
  }
  .sea-btn.active {
    border-color: var(--accent);
    color: var(--accent);
  }

  .error-msg {
    color: var(--red);
    font-size: 12px;
    font-weight: 600;
  }

  .start-btn {
    padding: 14px 32px;
    background: var(--accent);
    border: none;
    border-radius: 10px;
    color: #000;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.1em;
    cursor: pointer;
    touch-action: manipulation;
    margin-top: 8px;
  }
  .start-btn:disabled { opacity: 0.3; }
  .start-btn:active:not(:disabled) { opacity: 0.7; }

  /* Step header + progress */
  .step-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }
  .nav-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 2px solid var(--border);
    background: var(--card);
    color: var(--text);
    font-size: 18px;
    cursor: pointer;
    touch-action: manipulation;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .nav-btn:active { opacity: 0.6; }
  .step-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .step-count {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 14px;
    font-weight: 700;
    color: var(--accent);
  }
  .step-context {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }

  .step-progress {
    display: flex;
    gap: 4px;
    justify-content: center;
  }
  .step-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--border);
    transition: all 0.2s;
  }
  .step-dot.done { background: var(--green); }
  .step-dot.current { background: var(--accent); box-shadow: 0 0 8px var(--accent); }

  /* Step card */
  .step-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 16px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .step-label {
    font-size: var(--label-sm-size);
    font-weight: var(--label-md-weight);
    letter-spacing: var(--label-md-spacing);
    color: var(--accent);
    text-transform: uppercase;
  }

  .setting-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 16px 32px;
    background: var(--bg);
    border: 3px solid var(--border);
    border-radius: 12px;
    cursor: pointer;
    touch-action: manipulation;
    transition: border-color 0.2s;
  }
  .setting-btn:active { opacity: 0.6; }
  .setting-letter {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 56px;
    font-weight: 700;
    line-height: 1;
  }
  .setting-name {
    font-size: 11px;
    color: var(--text-dim);
    font-weight: 600;
  }

  .rec-badge {
    font-size: 10px;
    color: var(--orange);
    font-weight: 600;
    padding: 3px 10px;
    border: 1px solid var(--orange);
    border-radius: 4px;
  }

  .instruction {
    font-size: 14px;
    color: var(--text);
    text-align: center;
    font-weight: 600;
    line-height: 1.4;
  }
  .why {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
    line-height: 1.3;
    font-style: italic;
  }

  .test-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    touch-action: manipulation;
  }
  .test-toggle.open {
    border-color: var(--accent);
  }
  .test-toggle:active { opacity: 0.6; }
  .test-toggle-icon {
    font-size: 12px;
  }

  .test-box {
    width: 100%;
    padding: 12px;
    background: rgba(0, 212, 255, 0.06);
    border: 1px solid var(--accent);
    border-radius: 8px;
    font-size: 12px;
    color: var(--text);
    line-height: 1.5;
    text-align: left;
  }

  /* Performance monitor */
  .perf-monitor {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
  .perf-monitor.big {
    padding: 10px 20px;
  }
  .perf-label {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
  }
  .perf-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 18px;
    font-weight: 700;
    color: var(--green);
    text-shadow: var(--glow-green);
  }
  .perf-monitor.big .perf-value {
    font-size: 28px;
  }

  /* Actions */
  .step-actions, .review-actions {
    display: flex;
    gap: 8px;
    width: 100%;
    justify-content: center;
  }
  .action-btn {
    padding: 12px 20px;
    border: 2px solid;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.05em;
    cursor: pointer;
    touch-action: manipulation;
    background: var(--bg);
  }
  .action-btn:active { opacity: 0.6; }
  .action-btn.primary {
    color: var(--accent);
    border-color: var(--accent);
  }
  .action-btn.secondary {
    color: var(--text-dim);
    border-color: var(--border);
  }
  .action-btn.accent {
    color: var(--green);
    border-color: var(--green);
  }

  /* Review */
  .review-context {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
  }
  .review-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    width: 100%;
  }
  .review-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 8px 4px;
    background: var(--card);
    border-radius: 8px;
  }
  .review-label {
    font-size: var(--label-xs-size);
    color: var(--text-dim);
    letter-spacing: var(--label-xs-spacing);
  }
  .review-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 32px;
    font-weight: 700;
  }
  .review-diff {
    font-size: 9px;
    color: var(--orange);
    font-weight: 600;
  }
  .saved-msg {
    font-size: 13px;
    color: var(--green);
    font-weight: 600;
  }

  @media (max-width: 480px) {
    .cond-value { font-size: 22px; }
    .setting-letter { font-size: 44px; }
    .review-value { font-size: 24px; }
    .action-btn { padding: 10px 14px; font-size: 11px; }
  }
</style>
