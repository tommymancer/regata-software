<!--
  TrimEntry — Quick trim settings input with 3-level selectors.

  Each sail control has three positions: light / medium / heavy
  (contextual to each control). Tap to cycle. Long labels for phone use.
-->
<script>
  import { createEventDispatcher } from "svelte";
  import { levelColor } from "../lib/formatting.js";

  const dispatch = createEventDispatcher();

  const controls = [
    { key: "cunningham", label: "CUNN" },
    { key: "outhaul",    label: "OUTHL" },
    { key: "vang",       label: "VANG" },
    { key: "jib_lead",   label: "JIB LD" },
    { key: "jib_halyard", label: "JIB HL" },
    { key: "traveller",  label: "TRAV" },
    { key: "forestay",   label: "F.STAY" },
  ];

  const levels = ["light", "medium", "heavy"];

  let values = {};
  controls.forEach((c) => (values[c.key] = ""));

  let notes = "";

  const seaStates = ["flat", "choppy", "rough"];
  let seaState = "";

  function selectSeaState(val) {
    seaState = seaState === val ? "" : val;
  }

  function cycle(key) {
    const cur = values[key];
    const idx = levels.indexOf(cur);
    values[key] = levels[(idx + 1) % levels.length];
  }

  function levelDisplay(val) {
    if (!val) return "—";
    return val.charAt(0).toUpperCase();
  }

  function save() {
    dispatch("save", { ...values, notes, sea_state: seaState });
  }
</script>

<div class="trim-entry">
  <div class="grid">
    {#each controls as ctrl}
      <button
        class="control-btn"
        on:click={() => cycle(ctrl.key)}
        style:border-color={levelColor(values[ctrl.key])}
      >
        <span class="ctrl-label">{ctrl.label}</span>
        <span class="ctrl-value" style:color={levelColor(values[ctrl.key])}>
          {levelDisplay(values[ctrl.key])}
        </span>
      </button>
    {/each}
  </div>

  <div class="sea-state-row">
    <span class="sea-label">SEA</span>
    {#each seaStates as ss}
      <button
        class="sea-btn"
        class:active={seaState === ss}
        on:click={() => selectSeaState(ss)}
      >
        {ss.toUpperCase()}
      </button>
    {/each}
  </div>

  <div class="notes-row">
    <input
      type="text"
      class="notes-input"
      placeholder="Notes..."
      bind:value={notes}
    />
    <button class="save-btn" on:click={save}>SAVE</button>
  </div>
</div>

<style>
  .trim-entry {
    width: 100%;
    padding: 0 8px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 8px;
  }
  .control-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 10px 4px;
    background: var(--card);
    border: 2px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    touch-action: manipulation;
  }
  .ctrl-label {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }
  .ctrl-value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 48px;
    font-weight: 700;
  }
  .sea-state-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    justify-content: center;
  }
  .sea-label {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }
  .sea-btn {
    padding: 6px 14px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-dim);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    cursor: pointer;
    touch-action: manipulation;
  }
  .sea-btn.active {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--bg);
  }
  .notes-row {
    display: flex;
    gap: 8px;
  }
  .notes-input {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    color: var(--text);
    outline: none;
  }
  .notes-input::placeholder {
    color: var(--text-dim);
  }
  .save-btn {
    padding: 8px 20px;
    background: var(--accent);
    border: none;
    border-radius: 6px;
    color: #fff;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    letter-spacing: 0.05em;
  }
</style>
