<!--
  WindShiftIndicator — Shows current wind shift relative to rolling average.

  Props:
    shift : number   — degrees of shift (signed, + = veered)
    type  : string   — "lift" | "header" | null
-->
<script>
  export let shift = 0;
  export let type = null;
</script>

<div class="wind-shift" class:lift={type === "lift"} class:header={type === "header"}>
  {#if type === "lift"}
    <span class="arrow">&#9650;</span>
    <span class="label">BUONO</span>
    <span class="value">+{Math.abs(shift)}&deg;</span>
  {:else if type === "header"}
    <span class="arrow">&#9660;</span>
    <span class="label">SCARSO</span>
    <span class="value">&minus;{Math.abs(shift)}&deg;</span>
  {:else}
    <span class="label steady">STABILE</span>
  {/if}
</div>

<style>
  .wind-shift {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 4px 12px;
    border-radius: 6px;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    width: 100%;
    height: 52px;
  }
  .arrow {
    font-size: 28px;
  }
  .label {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.1em;
  }
  .value {
    font-family: "SF Mono", "Menlo", "Cascadia Mono", monospace;
    font-size: 32px;
    font-weight: 800;
    text-shadow: var(--glow-text);
  }
  .lift {
    border-color: var(--green);
  }
  .lift .arrow, .lift .label, .lift .value {
    color: var(--green);
  }
  .header {
    border-color: var(--red);
  }
  .header .arrow, .header .label, .header .value {
    color: var(--red);
  }
  .steady {
    color: var(--text-dim);
  }

  @media (max-width: 480px) {
    .wind-shift { height: 48px; gap: 6px; padding: 2px 8px; }
    .arrow { font-size: 24px; }
    .label { font-size: 16px; }
    .value { font-size: 28px; }
  }
</style>
