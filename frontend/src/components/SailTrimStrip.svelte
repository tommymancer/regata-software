<!--
  SailTrimStrip — Compact read-only sail trim display for regatta screen.

  Shows 7 controls as single-letter abbreviations with L/M/H values,
  plus sea state tag and TWS range from the matching trim snapshot.

  Props:
    trim : object|null — trim snapshot from best_for_conditions API
-->
<script>
  import { levelColor } from "../lib/formatting.js";

  export let trim = null;

  const controls = [
    { key: "cunningham",   abbr: "C" },
    { key: "outhaul",      abbr: "O" },
    { key: "vang",         abbr: "V" },
    { key: "jib_lead",     abbr: "JL" },
    { key: "jib_halyard",  abbr: "JH" },
    { key: "traveller",    abbr: "T" },
    { key: "forestay",     abbr: "F" },
  ];

  function levelLetter(val) {
    if (!val) return "\u2013";
    return val.charAt(0).toUpperCase();
  }
</script>

{#if trim}
  <div class="trim-strip">
    <div class="controls-row">
      {#each controls as ctrl}
        <span class="ctrl">
          <span class="ctrl-key">{ctrl.abbr}</span>:<span
            class="ctrl-val"
            style:color={levelColor(trim[ctrl.key])}
          >{levelLetter(trim[ctrl.key])}</span>
        </span>
      {/each}
    </div>
    <div class="conditions-row">
      {#if trim.sea_state}
        <span class="tag sea">{trim.sea_state.toUpperCase()}</span>
      {/if}
      {#if trim.tws_kt != null}
        <span class="tag tws">{trim.tws_kt.toFixed(0)} kt</span>
      {/if}
      {#if trim.perf_pct != null}
        <span class="tag perf">{trim.perf_pct.toFixed(0)}%</span>
      {/if}
    </div>
  </div>
{:else}
  <div class="trim-strip empty">
    <span class="no-data">NO TRIM DATA</span>
  </div>
{/if}

<style>
  .trim-strip {
    width: 100%;
    padding: 4px 8px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
  .controls-row {
    display: flex;
    justify-content: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .ctrl {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 12px;
    white-space: nowrap;
  }
  .ctrl-key {
    color: var(--text-dim);
    font-size: 10px;
  }
  .ctrl-val {
    font-weight: 700;
  }
  .conditions-row {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-top: 2px;
  }
  .tag {
    font-size: 10px;
    letter-spacing: 0.05em;
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 600;
  }
  .tag.sea {
    background: var(--border);
    color: var(--text);
  }
  .tag.tws {
    color: var(--accent);
  }
  .tag.perf {
    color: var(--green);
  }
  .empty {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 36px;
  }
  .no-data {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.1em;
  }

  @media (max-width: 480px) {
    .trim-strip { padding: 3px 6px; }
    .controls-row { gap: 4px; }
    .ctrl { font-size: 11px; }
    .ctrl-key { font-size: 9px; }
  }
</style>
