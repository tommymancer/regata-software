<!--
  CourseSetupPage — Pre-race buoy mapping.

  Add marks, capture positions via GPS logging or triangulation,
  define the course sequence, and apply to the navigation engine.
-->
<script>
  import { onMount, onDestroy } from "svelte";
  import { lat, lon } from "../stores/boat.js";

  let marks = [];
  let total = 0;
  let resolved = 0;
  let ready = false;
  let feedback = "";
  let pollInterval;

  onMount(() => {
    fetchStatus();
    pollInterval = setInterval(fetchStatus, 2000);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  async function fetchStatus() {
    try {
      const res = await fetch("/api/course-setup/status");
      const data = await res.json();
      marks = data.marks || [];
      total = data.total || 0;
      resolved = data.resolved || 0;
      ready = data.ready || false;
    } catch { /* ignore */ }
  }

  function nextGateNum() {
    const gateNums = marks
      .filter(m => m.mark_type === "gate")
      .map(m => parseInt(m.name.replace(/[^0-9]/g, "")))
      .filter(n => !isNaN(n));
    let n = 1;
    while (gateNums.includes(n)) n++;
    return n;
  }

  async function addTypedMark(markType) {
    const nameMap = { start_rc: "RC", start_pin: "PIN", windward: "WW", leeward: "LW" };
    let name = nameMap[markType];
    // If name already exists, append a number
    if (name && marks.some(m => m.name === name)) {
      let n = 2;
      while (marks.some(m => m.name === name + n)) n++;
      name = name + n;
    }
    if (!name) name = String(nextAvailableNum());
    try {
      await fetch("/api/course-setup/marks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, mark_type: markType }),
      });
      await fetchStatus();
      showFeedback(`${name} added`);
    } catch { showFeedback("Error"); }
  }

  async function addGate() {
    const n = nextGateNum();
    try {
      await fetch("/api/course-setup/marks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `G${n}p`, mark_type: "gate" }),
      });
      await fetch("/api/course-setup/marks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `G${n}s`, mark_type: "gate" }),
      });
      await fetchStatus();
      showFeedback(`Gate G${n} added`);
    } catch { showFeedback("Error"); }
  }

  // Auto-build sequence from non-start marks in order (gates as single entry)
  $: autoSequence = (() => {
    const seq = [];
    const seen = new Set();
    for (const m of marks) {
      if (m.mark_type === "start_rc" || m.mark_type === "start_pin") continue;
      if (m.mark_type === "gate") {
        const base = m.name.replace(/[ps]$/, "");
        if (!seen.has(base)) {
          seen.add(base);
          seq.push(base);
        }
      } else {
        seq.push(m.name);
      }
    }
    return seq;
  })();

  async function removeMark(name) {
    try {
      await fetch(`/api/course-setup/marks/${encodeURIComponent(name)}`, { method: "DELETE" });
      await fetchStatus();
      showFeedback(`${name} removed`);
    } catch { showFeedback("Error"); }
  }

  async function logGps(name) {
    try {
      const res = await fetch(`/api/course-setup/marks/${encodeURIComponent(name)}/gps`, { method: "POST" });
      const data = await res.json();
      if (data.error) {
        showFeedback(data.error);
      } else {
        showFeedback(`${name}: GPS logged`);
      }
      await fetchStatus();
    } catch { showFeedback("Error"); }
  }

  async function sightMark(name) {
    try {
      const res = await fetch(`/api/course-setup/marks/${encodeURIComponent(name)}/sight`, { method: "POST" });
      const data = await res.json();
      if (data.error) {
        showFeedback(data.error);
      } else if (data.computed_mark) {
        showFeedback(`${name}: POSITION FOUND!`);
      } else {
        showFeedback(`${name}: sight ${data.sight_count}`);
      }
      await fetchStatus();
    } catch { showFeedback("Error"); }
  }

  async function resetMark(name) {
    try {
      await fetch(`/api/course-setup/marks/${encodeURIComponent(name)}/reset`, { method: "POST" });
      await fetchStatus();
      showFeedback(`${name}: reset`);
    } catch { showFeedback("Error"); }
  }

  async function applyCourse() {
    try {
      // Auto-set sequence from mark order, then apply
      await fetch("/api/course-setup/sequence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ marks: autoSequence }),
      });
      const res = await fetch("/api/course-setup/apply", { method: "POST" });
      const data = await res.json();
      showFeedback(`APPLIED: ${data.total} marks`);
      await fetchStatus();
    } catch { showFeedback("Error"); }
  }

  function showFeedback(msg) {
    feedback = msg;
    setTimeout(() => (feedback = ""), 2500);
  }

  // ── Mark types ──────────────────────────────────────────
  const MARK_TYPES = ["generic", "start_rc", "start_pin", "windward", "leeward", "gate"];
  const TYPE_LABELS = {
    generic: "",
    start_rc: "RC",
    start_pin: "PIN",
    windward: "WW",
    leeward: "LW",
    gate: "GATE",
  };
  const TYPE_COLORS = {
    generic: "var(--text-dim)",
    start_rc: "var(--accent)",
    start_pin: "var(--accent)",
    windward: "var(--orange)",
    leeward: "var(--green)",
    gate: "var(--text)",
  };

  async function cycleType(name, currentType) {
    const idx = MARK_TYPES.indexOf(currentType);
    const next = MARK_TYPES[(idx + 1) % MARK_TYPES.length];
    try {
      await fetch(`/api/course-setup/marks/${encodeURIComponent(name)}/type`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mark_type: next }),
      });
      await fetchStatus();
    } catch { /* ignore */ }
  }

  function statusColor(m) {
    if (m.resolved) return "var(--green)";
    if (m.sight_count > 0) return "var(--orange)";
    return "var(--text-dim)";
  }

  function statusText(m) {
    if (m.resolved && m.method === "gps") return "GPS";
    if (m.resolved && m.method === "sight") return "TRI";
    if (m.sight_count > 0) return `${m.sight_count}x`;
    return "---";
  }

  function fmtPos(m) {
    if (!m.resolved) return "---";
    return `${m.lat.toFixed(4)} ${m.lon.toFixed(4)}`;
  }

  $: hasGps = $lat != null && $lon != null;

  // Separate start line marks from course marks
  $: startMarks = marks.filter(m => m.mark_type === "start_rc" || m.mark_type === "start_pin");
  $: courseMarks = marks.filter(m => m.mark_type !== "start_rc" && m.mark_type !== "start_pin");
  $: rcMark = startMarks.find(m => m.mark_type === "start_rc");
  $: pinMark = startMarks.find(m => m.mark_type === "start_pin");
  $: lineReady = rcMark?.resolved && pinMark?.resolved;

</script>

<div class="page">
  <div class="header">
    <h1 class="title">COURSE SETUP</h1>
    <span class="gps-status" class:gps-ok={hasGps}>
      {hasGps ? "GPS OK" : "NO GPS"}
    </span>
  </div>

  {#if feedback}
    <div class="feedback">{feedback}</div>
  {/if}

  <div class="summary">
    {resolved}/{total} marks resolved
    {#if ready}
      <span class="ready-badge">READY</span>
    {/if}
  </div>

  <!-- Start line status banner -->
  <div class="line-banner">
    {#if lineReady}
      <span class="line-status ready">LINE SET — {rcMark.name} (RC) + {pinMark.name} (PIN)</span>
    {:else if rcMark || pinMark}
      <span class="line-status pending">
        {rcMark ? `RC: ${rcMark.name}` : "RC: —"}  ·  {pinMark ? `PIN: ${pinMark.name}` : "PIN: —"}
      </span>
    {:else}
      <span class="line-hint">Set 2 marks as RC and PIN for start line</span>
    {/if}
  </div>

  <!-- All marks in one list -->
  <div class="mark-list">
    {#each marks as m (m.name)}
      <div class="mark-row" class:start-mark={m.mark_type === "start_rc" || m.mark_type === "start_pin"}>
        <div class="mark-info">
          <span class="mark-name">{m.name}</span>
          <button
            class="type-badge"
            style:color={TYPE_COLORS[m.mark_type] || "var(--text-dim)"}
            style:border-color={TYPE_COLORS[m.mark_type] || "var(--border)"}
            on:click={() => cycleType(m.name, m.mark_type)}
          >{TYPE_LABELS[m.mark_type] || "—"}</button>
          <span class="mark-status" style:color={statusColor(m)}>{statusText(m)}</span>
          <span class="mark-pos">{fmtPos(m)}</span>
        </div>
        <div class="mark-actions">
          <button class="btn btn-gps" on:click={() => logGps(m.name)} disabled={!hasGps}>
            LOG
          </button>
          <button class="btn btn-sight" on:click={() => sightMark(m.name)} disabled={!hasGps}>
            SIGHT
          </button>
          <button class="btn btn-rst" on:click={() => resetMark(m.name)}>
            RST
          </button>
          <button class="btn btn-del" on:click={() => removeMark(m.name)}>
            X
          </button>
        </div>
      </div>
    {/each}
  </div>

  <div class="add-buttons">
    <button class="btn btn-add-rc" on:click={() => addTypedMark("start_rc")}>+ RC</button>
    <button class="btn btn-add-pin" on:click={() => addTypedMark("start_pin")}>+ PIN</button>
    <button class="btn btn-add-ww" on:click={() => addTypedMark("windward")}>+ WW</button>
    <button class="btn btn-add-lw" on:click={() => addTypedMark("leeward")}>+ LW</button>
    <button class="btn btn-add-gate" on:click={addGate}>+ GATE</button>
  </div>

  <!-- Sequence preview + Apply -->
  {#if autoSequence.length > 0}
    <div class="seq-preview">
      {autoSequence.join(" > ")}
    </div>
  {/if}

  <button
    class="btn btn-apply"
    on:click={applyCourse}
    disabled={!ready}
  >
    APPLY COURSE
  </button>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: var(--gap-airy);
    padding: var(--pad-airy);
    height: 100%;
    overflow-y: auto;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .title {
    font-size: 16px;
    font-weight: 900;
    letter-spacing: 2px;
    color: var(--text);
  }

  .gps-status {
    font-size: 11px;
    font-weight: 700;
    color: var(--red);
    letter-spacing: 1px;
  }

  .gps-ok {
    color: var(--green);
  }

  .feedback {
    font-size: 12px;
    color: var(--green);
    font-weight: 600;
    letter-spacing: 0.5px;
    text-align: center;
  }

  .summary {
    font-size: 12px;
    color: var(--text-dim);
    font-family: "SF Mono", "Menlo", monospace;
    text-align: center;
  }

  .ready-badge {
    color: var(--green);
    font-weight: 700;
    margin-left: 8px;
  }

  /* ── Section headers ────────────────────────────────── */

  .section-header {
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: 1.5px;
    color: var(--text-dim);
    margin-top: 4px;
  }

  .line-banner {
    text-align: center;
    padding: 6px 10px;
    background: var(--card);
    border-radius: 6px;
    border: 1px solid var(--border);
  }

  .line-hint {
    font-size: 11px;
    color: var(--text-dim);
  }

  .line-status {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .line-status.ready {
    color: var(--green);
  }

  .line-status.pending {
    color: var(--orange);
  }

  .mark-row.start-mark {
    border-color: var(--accent);
    border-style: dashed;
  }

  /* ── Mark list ──────────────────────────────────────── */

  .mark-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .mark-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 10px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    gap: 8px;
  }

  .mark-info {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .mark-name {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 18px;
    font-weight: 900;
    color: var(--text);
    min-width: 30px;
  }

  .type-badge {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: var(--label-xs-size);
    font-weight: var(--label-xs-weight);
    letter-spacing: 0.5px;
    padding: 2px 6px;
    border: 1px solid;
    border-radius: 4px;
    background: transparent;
    cursor: pointer;
    min-width: 32px;
    text-align: center;
    touch-action: manipulation;
  }
  .type-badge:active {
    opacity: 0.7;
  }

  .mark-status {
    font-size: var(--label-sm-size);
    font-weight: var(--label-sm-weight);
    letter-spacing: 0.5px;
    min-width: 28px;
  }

  .mark-pos {
    font-size: 10px;
    color: var(--text-dim);
    font-family: "SF Mono", "Menlo", monospace;
  }

  .mark-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  /* ── Buttons ────────────────────────────────────────── */

  .btn {
    font-family: inherit;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 12px;
    border: 2px solid;
    border-radius: 6px;
    cursor: pointer;
    background: var(--card);
    letter-spacing: 0.5px;
    touch-action: manipulation;
  }

  .btn:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .btn:active:not(:disabled) {
    opacity: 0.7;
  }

  .btn-gps {
    color: var(--accent);
    border-color: var(--accent);
  }

  .btn-sight {
    color: var(--orange);
    border-color: var(--orange);
  }

  .btn-rst {
    color: var(--text-dim);
    border-color: var(--border);
    padding: 8px 8px;
    font-size: 10px;
  }

  .btn-del {
    color: var(--red);
    border-color: var(--border);
    padding: 8px 8px;
    font-size: 10px;
  }

  .add-buttons {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .add-buttons .btn {
    flex: 1;
    min-width: 50px;
    font-size: 12px;
    padding: 10px 6px;
    text-align: center;
  }

  .btn-add-rc, .btn-add-pin {
    color: var(--accent);
    border-color: var(--accent);
  }

  .btn-add-ww {
    color: var(--orange);
    border-color: var(--orange);
  }

  .btn-add-lw {
    color: var(--green);
    border-color: var(--green);
  }

  .btn-add-gate {
    color: var(--text);
    border-color: var(--text);
  }

  .btn-apply {
    color: var(--green);
    border-color: var(--green);
    width: 100%;
    font-size: 16px;
    font-weight: 900;
    padding: 14px;
    letter-spacing: 2px;
  }

  /* ── Sequence preview ──────────────────────────────── */

  .seq-preview {
    font-size: 13px;
    font-family: "SF Mono", "Menlo", monospace;
    color: var(--accent);
    font-weight: 600;
    text-align: center;
    letter-spacing: 1px;
  }

  @media (max-width: 480px) {
    .page { padding: 8px; gap: 8px; }
    .btn { font-size: 11px; padding: 6px 8px; }
    .mark-name { font-size: 16px; }
    .mark-pos { display: none; }
  }
</style>
