<!--
  ShiftGauge — horizontal bar indicator for wind shift.

  Centered at 0°, extends left (backed) or right (veered).
  Color: green = lift (good for current tack), red = header (bad).
  Scale: ±15°.
-->
<script>
  export let shift = 0;       // degrees of shift (signed, + = veered right)
  export let type = null;      // "lift" | "header" | null

  const maxShift = 15;

  $: clamped = Math.max(-maxShift, Math.min(maxShift, shift));
  $: pct = (clamped / maxShift) * 50;
  $: display = Math.abs(shift).toFixed(0) + "°";
  $: barColor = type === "lift"
    ? "var(--green)"
    : type === "header"
      ? "var(--red)"
      : "var(--border)";
  $: label = type === "lift" ? "BUONO" : type === "header" ? "SCARSO" : "—";
</script>

<div class="shift-gauge">
  <span class="lbl">SALTO</span>
  <div class="bar-bg">
    <div class="center-line"></div>
    {#each [-10, -5, 5, 10] as tick}
      <div class="tick" style="left: {50 + (tick / maxShift) * 50}%"></div>
    {/each}
    {#if pct !== 0}
      <div
        class="bar-fill"
        style="
          left: {pct < 0 ? 50 + pct : 50}%;
          width: {Math.abs(pct)}%;
          background: {barColor};
        "
      ></div>
    {/if}
    {#if shift !== 0}
      <div class="needle" style="left: {50 + pct}%; background: {barColor}"></div>
    {/if}
  </div>
  <span class="value" style="color: {barColor}">{display}</span>
  <span class="type-label" style="color: {barColor}">{label}</span>
</div>

<style>
  .shift-gauge {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    max-width: 100%;
    padding: 4px 0;
  }
  .lbl {
    font-size: 10px;
    color: var(--text-dim);
    width: 34px;
    text-align: right;
    flex-shrink: 0;
    letter-spacing: 0.05em;
  }
  .bar-bg {
    flex: 1;
    height: 24px;
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 4px;
    position: relative;
    overflow: hidden;
  }
  .center-line {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--text-dim);
    opacity: 0.5;
  }
  .tick {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border);
  }
  .bar-fill {
    position: absolute;
    top: 2px;
    bottom: 2px;
    border-radius: 2px;
    opacity: 0.4;
  }
  .needle {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 3px;
    border-radius: 1px;
    transform: translateX(-1px);
  }
  .value {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 40px;
    font-weight: 800;
    width: 60px;
    text-shadow: var(--glow-text);
    text-align: left;
    flex-shrink: 0;
  }
  .type-label {
    font-size: 18px;
    font-weight: 700;
    width: 42px;
    text-align: left;
    flex-shrink: 0;
    letter-spacing: 0.05em;
  }
</style>
