<!--
  HeelGauge — horizontal bar indicator for heel angle.

  Centered at 0°, extends left (port/red) or right (stbd/green).
  Scale: ±30°.
-->
<script>
  export let value = null; // heel in degrees: −port +stbd
  export let maxAngle = 30;
  export let expanded = false;

  $: clamped = value != null ? Math.max(-maxAngle, Math.min(maxAngle, value)) : 0;
  $: pct = value != null ? (clamped / maxAngle) * 50 : 0; // % of bar width from center
  $: display = value != null ? Math.abs(value).toFixed(0) + "°" : "---";
  $: side = value == null ? "" : value < -0.5 ? "-" : value > 0.5 ? "+" : "";
  $: barColor = value == null
    ? "var(--border)"
    : value < -0.5
      ? "var(--port)"
      : value > 0.5
        ? "var(--stbd)"
        : "var(--accent)";
</script>

<div class="heel-gauge" class:expanded>
  <span class="label">SBANDAMENTO</span>
  <div class="bar-bg">
    <!-- Center line -->
    <div class="center-line"></div>
    <!-- Tick marks -->
    {#each [-20, -10, 10, 20] as tick}
      <div class="tick" style="left: {50 + (tick / maxAngle) * 50}%"></div>
    {/each}
    <!-- Fill bar -->
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
    <!-- Indicator needle -->
    {#if value != null}
      <div class="needle" style="left: {50 + pct}%; background: {barColor}"></div>
    {/if}
  </div>
  <span class="value" style="color: {barColor}">{display}{side}</span>
</div>

<style>
  .heel-gauge {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    max-width: 360px;
    padding: 4px 0;
  }
  .label {
    font-size: 10px;
    color: var(--text-dim);
    width: 32px;
    text-align: right;
    flex-shrink: 0;
  }
  .bar-bg {
    flex: 1;
    height: 16px;
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
    font-family: "SF Mono", "Menlo", "Cascadia Mono", monospace;
    font-size: 28px;
    font-weight: 800;
    width: 60px;
    text-shadow: var(--glow-text);
    text-align: left;
    flex-shrink: 0;
  }

  @media (max-width: 480px) {
    .heel-gauge { gap: 4px; max-width: 280px; }
    .label { font-size: 12px; width: 32px; }
    .bar-bg { height: 12px; }
    .value { font-size: 24px; width: 52px; }
  }

  .heel-gauge.expanded {
    max-width: 100%;
    gap: 10px;
  }
  .expanded .bar-bg {
    height: 28px;
    border-radius: 6px;
  }
  .expanded .needle {
    width: 4px;
  }
  .expanded .label {
    font-size: 14px;
    width: 40px;
  }
  .expanded .value {
    font-size: 48px;
    font-weight: 800;
    width: 80px;
  }
</style>
