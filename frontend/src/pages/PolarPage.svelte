<!--
  PolarPage — Polar learning status, coverage heatmap, and actions.

  Shows accumulated sample coverage per TWS/TWA bin, learning statistics,
  and buttons to rebuild, activate, reset, or clear learned data.
-->
<script>
  import { onMount, onDestroy } from "svelte";

  let stats = null;
  let coverage = [];
  let snapshots = [];
  let sessions = [];
  let showSnapshots = false;
  let showSessions = false;
  let showManual = false;
  let loading = false;
  let feedback = "";

  $: sailLabel = stats?.sail_short ?? "";

  $: twsBins = [...new Set(coverage.map((c) => c.tws))].sort((a, b) => a - b);
  $: twaBins = [...new Set(coverage.map((c) => c.twa))].sort((a, b) => a - b);
  $: coverageMap = new Map(coverage.map((c) => [`${c.tws}_${c.twa}`, c]));

  // Determine current step in the workflow
  $: step = !stats ? 0
    : stats.total_samples === 0 ? 1
    : stats.bins_ready === 0 ? 2
    : !stats.has_learned_polar ? 3
    : 4;

  $: stepText = [
    "",
    "Naviga per raccogliere dati",
    `${stats?.total_samples ?? 0} campioni — continua per riempire le caselle`,
    `${stats?.bins_ready ?? 0} caselle pronte — rebuild automatico a fine sessione`,
    `Polar appresa attiva — ${stats?.coverage_pct ?? 0}% copertura`,
  ][step] || "";

  function cellColor(cell) {
    if (!cell || cell.count === 0) return "var(--border)";
    if (cell.ready) return "var(--green)";
    return "var(--orange)";
  }

  function cellText(cell) {
    if (!cell || cell.count === 0) return "";
    return cell.count;
  }

  async function fetchData() {
    try {
      const [sRes, cRes] = await Promise.all([
        fetch("/api/polar/stats"),
        fetch("/api/polar/coverage"),
      ]);
      stats = await sRes.json();
      coverage = await cRes.json();
    } catch (e) {
      // ignore
    }
  }

  async function fetchSnapshots() {
    try {
      const res = await fetch("/api/polar/snapshots");
      snapshots = await res.json();
    } catch (e) {
      snapshots = [];
    }
  }

  async function fetchSessions() {
    try {
      const res = await fetch("/api/sessions?limit=50");
      const all = await res.json();
      // Only show sessions that have polar data
      sessions = all.filter(s => s.polar_samples > 0);
    } catch (e) {
      sessions = [];
    }
  }

  async function toggleSession(session) {
    const newVal = !session.polar_included;
    try {
      await fetch(`/api/sessions/${session.id}/polar-included`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ polar_included: newVal }),
      });
      session.polar_included = newVal;
      sessions = sessions;  // trigger reactivity
    } catch (e) {
      showFeedback("Errore", true);
    }
  }

  function fmtDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "2-digit" })
      + " " + d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  }

  async function apiAction(endpoint, confirmMsg) {
    if (confirmMsg && !confirm(confirmMsg)) return;
    loading = true;
    feedback = "";
    try {
      const res = await fetch(`/api/polar/${endpoint}`, { method: "POST" });
      const data = await res.json();
      if (data.error) {
        showFeedback(data.error, true);
      } else {
        showFeedback(
          endpoint === "rebuild" ? "Polar ricostruita e salvata"
          : endpoint === "activate" ? "Polar appresa attivata"
          : endpoint === "reset-to-base" ? "Polar base ripristinata"
          : endpoint === "clear" ? "Dati cancellati"
          : "OK"
        );
        await fetchData();
      }
    } catch (e) {
      showFeedback("Errore", true);
    }
    loading = false;
  }

  let feedbackError = false;
  function showFeedback(msg, isError = false) {
    feedback = msg;
    feedbackError = isError;
    setTimeout(() => (feedback = ""), 3000);
  }

  function fmtTwa(val) {
    return Math.round(val) + "°";
  }

  function fmtDuration(start, end) {
    if (!start || !end) return "";
    const ms = new Date(end) - new Date(start);
    const mins = Math.round(ms / 60000);
    if (mins < 60) return `${mins}min`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return `${h}h${m > 0 ? m + "min" : ""}`;
  }

  let interval;
  onMount(() => {
    fetchData();
    interval = setInterval(fetchData, 30000);
  });
  onDestroy(() => clearInterval(interval));
</script>

<div class="page">
  <h2 class="title">POLAR LEARNING {sailLabel ? `— ${sailLabel}` : ""}</h2>

  <!-- Step indicator -->
  <div class="step-bar">
    <div class="step-dots">
      {#each [1, 2, 3, 4] as s}
        <div class="step-dot" class:done={step >= s} class:current={step === s}></div>
        {#if s < 4}<div class="step-line" class:done={step > s}></div>{/if}
      {/each}
    </div>
    <div class="step-labels">
      <span class:dim={step !== 1}>NAVIGA</span>
      <span class:dim={step !== 2}>RACCOGLI</span>
      <span class:dim={step !== 3}>ELABORA</span>
      <span class:dim={step !== 4}>ATTIVA</span>
    </div>
    <div class="step-text">{stepText}</div>
  </div>

  <!-- Stats bar -->
  {#if stats}
    <div class="section stats-bar">
      <div class="stat">
        <span class="stat-value">{stats.total_samples}</span>
        <span class="stat-label">campioni</span>
      </div>
      <div class="stat">
        <span class="stat-value">{stats.coverage_pct}%</span>
        <span class="stat-label">copertura</span>
      </div>
      <div class="stat">
        <span class="stat-value">{stats.bins_ready}</span>
        <span class="stat-label">pronte</span>
      </div>
      <div class="stat">
        <span class="stat-value status" class:active={stats.has_learned_polar}>
          {stats.has_learned_polar ? "APPRESA" : "BASE"}
        </span>
        <span class="stat-label">polar</span>
      </div>
    </div>
  {/if}

  {#if stats?.last_rebuild}
    <div class="last-rebuild">
      Ultimo rebuild: {new Date(stats.last_rebuild).toLocaleString("it-IT", {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
      })}
    </div>
  {/if}

  <!-- Coverage matrix -->
  {#if twsBins.length > 0 && twaBins.length > 0}
    <div class="section matrix-section">
      <div class="section-header">
        <span class="section-title">Matrice copertura (TWA x TWS)</span>
        <span class="legend">
          <span class="legend-dot" style="background:var(--green)"></span> ≥50
          <span class="legend-dot" style="background:var(--orange)"></span> &lt;50
          <span class="legend-dot" style="background:var(--border)"></span> vuoto
        </span>
      </div>
      <div class="matrix-scroll">
        <div class="matrix" style="grid-template-columns: 36px repeat({twsBins.length}, 1fr)">
          <!-- Header row: TWS labels -->
          <div class="cell header corner">kt</div>
          {#each twsBins as tws}
            <div class="cell header">{tws}</div>
          {/each}
          <!-- Data rows: one per TWA -->
          {#each twaBins as twa}
            <div class="cell header row-header">{fmtTwa(twa)}</div>
            {#each twsBins as tws}
              {@const cell = coverageMap.get(`${tws}_${twa}`)}
              <div class="cell data" style="background: {cellColor(cell)}">
                {cellText(cell)}
              </div>
            {/each}
          {/each}
        </div>
      </div>
    </div>
  {:else}
    <div class="section empty-section">
      <div class="empty-icon">⚓</div>
      <div class="empty-text">Nessun dato ancora</div>
      <div class="empty-hint">Naviga in condizioni stabili per raccogliere campioni automaticamente</div>
    </div>
  {/if}

  <!-- Manual controls (collapsible) -->
  <button class="btn btn-secondary manual-toggle"
    on:click={() => showManual = !showManual}>
    {showManual ? "NASCONDI MANUALE" : "CONTROLLI MANUALI"}
  </button>

  {#if showManual}
    <div class="actions">
      <button class="btn btn-primary" on:click={() => apiAction("rebuild")}
        disabled={loading || !stats || stats.bins_ready === 0}
        title="Ricostruisci la polar dai dati raccolti">
        REBUILD
      </button>
      <button class="btn btn-accent" on:click={() => apiAction("activate")}
        disabled={loading || !stats || !stats.has_learned_polar}
        title="Usa la polar appresa per target e performance">
        ATTIVA
      </button>
      <button class="btn btn-secondary" on:click={() => apiAction("reset-to-base")}
        disabled={loading}>
        POLAR BASE
      </button>
      <button class="btn btn-danger"
        on:click={() => apiAction("clear", "Cancellare tutti i campioni raccolti?")}
        disabled={loading}>
        CANCELLA
      </button>
    </div>
  {/if}

  {#if feedback}
    <div class="feedback" class:error={feedbackError}>{feedback}</div>
  {/if}

  <!-- Sessions -->
  <button class="btn btn-secondary sessions-toggle"
    on:click={() => { showSessions = !showSessions; if (showSessions) fetchSessions(); }}>
    {showSessions ? "NASCONDI SESSIONI" : "SESSIONI"}
  </button>

  {#if showSessions}
    <div class="section sessions-section">
      {#if sessions.length === 0}
        <div class="empty-text">Nessuna sessione con dati polari</div>
      {:else}
        <div class="sessions-hint">Seleziona le sessioni da usare per il calcolo della polar</div>
        {#each sessions as session}
          <button class="session-row" on:click={() => toggleSession(session)}>
            <div class="session-toggle" class:included={session.polar_included}>
              {session.polar_included ? "✓" : ""}
            </div>
            <div class="session-info">
              <span class="session-date">{fmtDate(session.start_time)}</span>
              <span class="session-meta">
                {session.polar_samples} campioni
                {#if session.end_time}
                  · {fmtDuration(session.start_time, session.end_time)}
                {/if}
              </span>
            </div>
          </button>
        {/each}
      {/if}
    </div>
  {/if}

  <!-- Snapshots -->
  <button class="btn btn-secondary snapshots-toggle"
    on:click={() => { showSnapshots = !showSnapshots; if (showSnapshots) fetchSnapshots(); }}>
    {showSnapshots ? "NASCONDI" : "POLARI SALVATE"}
  </button>

  {#if showSnapshots}
    <div class="section snapshots-section">
      {#if snapshots.length === 0}
        <div class="empty-text">Nessun salvataggio — fai REBUILD per salvarne una</div>
      {:else}
        {#each snapshots as snap}
          <a class="snapshot-row" href="/api/polar/snapshots/{snap.filename}" download>
            <span class="snap-name">{fmtDate(snap.created)}</span>
            <span class="snap-info">{snap.total_samples} campioni, {snap.bins_ready} caselle</span>
          </a>
        {/each}
      {/if}
    </div>
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

  /* ── Step indicator ──────────────────────────── */
  .step-bar {
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }
  .step-dots {
    display: flex;
    align-items: center;
    gap: 0;
    width: 100%;
    max-width: 280px;
  }
  .step-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--border);
    background: transparent;
    flex-shrink: 0;
    transition: all 0.3s;
  }
  .step-dot.done {
    background: var(--green);
    border-color: var(--green);
    box-shadow: 0 0 6px var(--green);
  }
  .step-dot.current {
    border-color: var(--accent);
    box-shadow: 0 0 8px var(--accent);
  }
  .step-dot.current:not(.done) {
    background: var(--accent);
    border-color: var(--accent);
  }
  .step-line {
    flex: 1;
    height: 2px;
    background: var(--border);
    transition: background 0.3s;
  }
  .step-line.done {
    background: var(--green);
  }
  .step-labels {
    display: flex;
    justify-content: space-between;
    width: 100%;
    max-width: 300px;
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: var(--label-xs-spacing);
    color: var(--text);
  }
  .step-labels .dim {
    color: var(--text-dim);
  }
  .step-text {
    font-size: 11px;
    color: var(--accent);
    text-align: center;
    font-weight: 600;
  }

  /* ── Stats bar ───────────────────────────────── */
  .section {
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
  }
  .stats-bar {
    display: flex;
    justify-content: space-around;
  }
  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .stat-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 36px;
    font-weight: 700;
    color: var(--text);
    text-shadow: var(--glow-text);
  }
  .stat-label {
    font-size: var(--label-xs-size);
    text-transform: uppercase;
    letter-spacing: var(--label-xs-spacing);
    color: var(--text-dim);
  }
  .status {
    font-size: 12px;
  }
  .status.active {
    color: var(--green);
    text-shadow: var(--glow-green);
  }

  /* ── Coverage matrix ─────────────────────────── */
  .matrix-section {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .section-header {
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
  }
  .legend {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 8px;
    color: var(--text-dim);
  }
  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 2px;
    display: inline-block;
    margin-left: 4px;
  }
  .matrix-scroll {
    overflow: auto;
    flex: 1;
    min-height: 0;
  }
  .matrix {
    display: grid;
    gap: 1px;
  }
  .cell {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-family: "SF Mono", "Menlo", monospace;
    min-height: 28px;
    min-width: 0;
  }
  .cell.header {
    color: var(--text-dim);
    font-size: 10px;
    font-weight: 600;
  }
  .cell.corner {
    font-size: 8px;
    color: var(--text-dim);
  }
  .cell.row-header {
    font-size: 11px;
  }
  .cell.data {
    color: var(--bg);
    font-weight: 700;
    border-radius: 3px;
    padding: 2px;
  }

  /* ── Empty state ─────────────────────────────── */
  .empty-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px 20px;
    gap: 6px;
  }
  .empty-icon {
    font-size: 32px;
    opacity: 0.5;
  }
  .empty-text {
    text-align: center;
    color: var(--text-dim);
    font-size: 13px;
    font-weight: 600;
  }
  .empty-hint {
    text-align: center;
    color: var(--text-dim);
    font-size: 11px;
    opacity: 0.7;
  }

  .last-rebuild {
    text-align: center;
    font-size: var(--label-xs-size);
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }
  .manual-toggle {
    width: 100%;
  }

  /* ── Actions ─────────────────────────────────── */
  .actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: center;
  }
  .btn {
    font-family: inherit;
    font-size: 11px;
    font-weight: 700;
    padding: 8px 12px;
    border: 2px solid;
    border-radius: 6px;
    cursor: pointer;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    letter-spacing: 0.5px;
    touch-action: manipulation;
    transition: opacity 0.15s;
  }
  .btn:disabled {
    opacity: 0.25;
    cursor: default;
  }
  .btn:active:not(:disabled) {
    opacity: 0.7;
  }
  .btn-primary {
    color: var(--green);
    border-color: var(--green);
  }
  .btn-accent {
    color: var(--accent);
    border-color: var(--accent);
  }
  .btn-secondary {
    color: var(--text-dim);
    border-color: var(--border);
  }
  .btn-danger {
    color: var(--red);
    border-color: var(--red);
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

  /* ── Sessions ────────────────────────────────── */
  .sessions-toggle {
    width: 100%;
  }
  .sessions-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .sessions-hint {
    font-size: 10px;
    color: var(--text-dim);
    text-align: center;
    margin-bottom: 4px;
  }
  .session-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 8px;
    background: var(--bg);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    touch-action: manipulation;
    text-align: left;
    color: var(--text);
  }
  .session-row:active { opacity: 0.7; }
  .session-toggle {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: 2px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
    color: var(--bg);
  }
  .session-toggle.included {
    background: var(--green);
    border-color: var(--green);
    box-shadow: 0 0 6px var(--green);
  }
  .session-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .session-date {
    font-size: 13px;
    font-weight: 600;
  }
  .session-meta {
    font-size: 10px;
    color: var(--text-dim);
  }

  /* ── Snapshots ───────────────────────────────── */
  .snapshots-toggle {
    width: 100%;
  }
  .snapshots-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .snapshot-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px;
    background: var(--bg);
    border-radius: 4px;
    text-decoration: none;
    color: var(--text);
  }
  .snapshot-row:active {
    opacity: 0.7;
  }
  .snap-name {
    font-size: 12px;
    font-weight: 600;
  }
  .snap-info {
    font-size: 10px;
    color: var(--text-dim);
  }

  @media (max-width: 480px) {
    .page { padding: 6px; gap: 6px; }
    .stat-value { font-size: 14px; }
    .btn { font-size: 10px; padding: 6px 10px; }
  }
</style>
