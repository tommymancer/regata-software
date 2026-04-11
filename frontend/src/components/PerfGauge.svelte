<!--
  PerfGauge — Circular performance gauge (0–120%).

  Color zones:
    0–60%  : red (poor)
    60–85% : orange (fair)
    85–100%: green (good)
    100–120%: cyan (above polar — surfing / favorable current)

  Props:
    value : number|null  — current PERF% (0–120+)
    label : string       — "PERF" or "VMG PERF"
-->
<script>
  import { onMount, afterUpdate } from "svelte";
  import { getThemeColors, withAlpha } from "../lib/theme.js";
  import { resizeCanvas } from "../lib/canvas.js";

  export let value = null;
  export let label = "PERF";

  let canvas;
  let ctx;
  let size = 0;

  onMount(() => {
    ctx = canvas.getContext("2d");
    resize();
    draw();
  });

  afterUpdate(draw);

  function resize() {
    const result = resizeCanvas(canvas);
    size = result.size;
  }

  function draw() {
    if (!ctx) return;
    const colors = getThemeColors(canvas.parentElement);
    const dpr = devicePixelRatio;
    const cx = (size * dpr) / 2;
    const cy = (size * dpr) / 2;
    const r = cx * 0.82;

    ctx.clearRect(0, 0, size * dpr, size * dpr);

    // Arc angles: sweep from 135° to 405° (270° arc)
    const startAngle = (135 * Math.PI) / 180;
    const endAngle = (405 * Math.PI) / 180;
    const sweep = endAngle - startAngle;

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = 8 * dpr;
    ctx.lineCap = "round";
    ctx.stroke();

    // Color zone arcs
    const zones = [
      { from: 0, to: 60, color: withAlpha(colors.red, 0.4) },
      { from: 60, to: 85, color: withAlpha(colors.orange, 0.4) },
      { from: 85, to: 100, color: withAlpha(colors.green, 0.4) },
      { from: 100, to: 120, color: withAlpha(colors.accent, 0.4) },
    ];

    for (const zone of zones) {
      const a0 = startAngle + (zone.from / 120) * sweep;
      const a1 = startAngle + (zone.to / 120) * sweep;
      ctx.beginPath();
      ctx.arc(cx, cy, r, a0, a1);
      ctx.strokeStyle = zone.color;
      ctx.lineWidth = 8 * dpr;
      ctx.lineCap = "butt";
      ctx.stroke();
    }

    // Tick marks
    for (let pct = 0; pct <= 120; pct += 10) {
      const angle = startAngle + (pct / 120) * sweep;
      const isMajor = pct % 20 === 0;
      const inner = isMajor ? r * 0.88 : r * 0.92;
      const outer = r * 1.0;

      ctx.beginPath();
      ctx.moveTo(cx + inner * Math.cos(angle), cy + inner * Math.sin(angle));
      ctx.lineTo(cx + outer * Math.cos(angle), cy + outer * Math.sin(angle));
      ctx.strokeStyle = isMajor ? colors.textDim : colors.border;
      ctx.lineWidth = (isMajor ? 2 : 1) * dpr;
      ctx.lineCap = "round";
      ctx.stroke();

      // Labels at major ticks
      if (isMajor) {
        const labelR = r * 0.80;
        ctx.font = `${9 * dpr}px sans-serif`;
        ctx.fillStyle = colors.textDim;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(
          pct + "%",
          cx + labelR * Math.cos(angle),
          cy + labelR * Math.sin(angle)
        );
      }
    }

    // 100% marker line
    const mark100 = startAngle + (100 / 120) * sweep;
    ctx.beginPath();
    ctx.moveTo(cx + r * 0.85 * Math.cos(mark100), cy + r * 0.85 * Math.sin(mark100));
    ctx.lineTo(cx + r * 1.05 * Math.cos(mark100), cy + r * 1.05 * Math.sin(mark100));
    ctx.strokeStyle = colors.green;
    ctx.lineWidth = 2 * dpr;
    ctx.stroke();

    // Value needle
    if (value != null) {
      const clamped = Math.max(0, Math.min(120, value));
      const needleAngle = startAngle + (clamped / 120) * sweep;
      const needleLen = r * 0.7;

      // Needle color based on zone
      let needleColor;
      if (clamped >= 100) needleColor = colors.accent;
      else if (clamped >= 85) needleColor = colors.green;
      else if (clamped >= 60) needleColor = colors.orange;
      else needleColor = colors.red;

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(
        cx + needleLen * Math.cos(needleAngle),
        cy + needleLen * Math.sin(needleAngle)
      );
      ctx.strokeStyle = needleColor;
      ctx.lineWidth = 3 * dpr;
      ctx.lineCap = "round";
      ctx.stroke();

      // Center dot
      ctx.beginPath();
      ctx.arc(cx, cy, 4 * dpr, 0, Math.PI * 2);
      ctx.fillStyle = needleColor;
      ctx.fill();
    }

    // Center text
    ctx.font = `bold ${44 * dpr}px "SF Mono", "Menlo", monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    if (value != null) {
      let textColor;
      if (value >= 100) textColor = colors.accent;
      else if (value >= 85) textColor = colors.green;
      else if (value >= 60) textColor = colors.orange;
      else textColor = colors.red;

      ctx.fillStyle = textColor;
      ctx.fillText(value.toFixed(0) + "%", cx, cy + 4 * dpr);
    } else {
      ctx.fillStyle = colors.textDim;
      ctx.fillText("---%", cx, cy + 4 * dpr);
    }

    // Label below
    ctx.font = `${10 * dpr}px sans-serif`;
    ctx.fillStyle = colors.textDim;
    ctx.fillText(label, cx, cy + 24 * dpr);
  }
</script>

<svelte:window on:resize={resize} />

<div class="perf-gauge-container">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .perf-gauge-container {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }
  canvas {
    display: block;
  }
</style>
