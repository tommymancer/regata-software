<!--
  StripChart — Canvas time-series chart with ring buffer data.

  Props:
    data       — array of samples from history store [{t, bsp, tws, ...}]
    traces     — [{key, color, label}]  which fields to plot
    windowSec  — visible time window in seconds (default 120)
    minY / maxY — manual Y range (auto-scale if null)
    height     — CSS height (default "140px")
-->
<script>
  import { onMount, afterUpdate } from "svelte";
  import { getThemeColors, withAlpha } from "../lib/theme.js";

  export let data = [];
  export let traces = [];
  export let windowSec = 120;
  export let minY = null;
  export let maxY = null;
  export let height = "140px";

  let canvas;
  let ctx;
  let w = 0, h = 0;

  onMount(() => {
    ctx = canvas.getContext("2d");
    resize();
  });

  afterUpdate(() => {
    if (ctx) draw();
  });

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    w = rect.width;
    h = rect.height;
    const dpr = devicePixelRatio;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    if (ctx) draw();
  }

  function draw() {
    if (!ctx || w === 0 || h === 0) return;
    const dpr = devicePixelRatio;
    const cw = w * dpr;
    const ch = h * dpr;
    const pad = { top: 4 * dpr, bottom: 18 * dpr, left: 36 * dpr, right: 8 * dpr };
    const plotW = cw - pad.left - pad.right;
    const plotH = ch - pad.top - pad.bottom;

    ctx.clearRect(0, 0, cw, ch);

    const colors = getThemeColors(canvas.parentElement);

    if (!data || data.length < 2 || !traces.length) {
      ctx.font = `${11 * dpr}px sans-serif`;
      ctx.fillStyle = colors.textDim;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("waiting for data…", cw / 2, ch / 2);
      return;
    }

    // Time range: last windowSec seconds
    const now = data[data.length - 1].t;
    const tMin = now - windowSec * 1000;

    // Filter visible samples
    const visible = data.filter((s) => s.t >= tMin);
    if (visible.length < 2) return;

    // Y range — auto or manual
    let yMin = minY, yMax = maxY;
    if (yMin == null || yMax == null) {
      let lo = Infinity, hi = -Infinity;
      for (const s of visible) {
        for (const tr of traces) {
          const v = s[tr.key];
          if (v != null && isFinite(v)) {
            if (v < lo) lo = v;
            if (v > hi) hi = v;
          }
        }
      }
      if (!isFinite(lo)) { lo = 0; hi = 10; }
      const margin = (hi - lo) * 0.1 || 1;
      if (yMin == null) yMin = lo - margin;
      if (yMax == null) yMax = hi + margin;
    }

    // Helper: map value to canvas coords
    const xOf = (t) => pad.left + ((t - tMin) / (windowSec * 1000)) * plotW;
    const yOf = (v) => pad.top + (1 - (v - yMin) / (yMax - yMin)) * plotH;

    // Grid lines
    ctx.strokeStyle = withAlpha(colors.border, 0.5);
    ctx.lineWidth = 1 * dpr;
    const nGridY = 4;
    for (let i = 0; i <= nGridY; i++) {
      const y = pad.top + (i / nGridY) * plotH;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + plotW, y);
      ctx.stroke();

      // Y labels
      const val = yMax - (i / nGridY) * (yMax - yMin);
      ctx.font = `${9 * dpr}px sans-serif`;
      ctx.fillStyle = colors.textDim;
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(val.toFixed(1), pad.left - 4 * dpr, y);
    }

    // Time labels
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const intervals = [30, 60, 120];
    const secInterval = intervals.find((i) => windowSec / i <= 6) || 60;
    for (let s = secInterval; s <= windowSec; s += secInterval) {
      const t = now - s * 1000;
      if (t < tMin) break;
      const x = xOf(t);
      ctx.fillStyle = colors.textDim;
      ctx.font = `${8 * dpr}px sans-serif`;
      ctx.fillText(`-${s}s`, x, ch - pad.bottom + 4 * dpr);
    }

    // Draw traces
    for (const tr of traces) {
      ctx.beginPath();
      ctx.strokeStyle = tr.color;
      ctx.lineWidth = 1.5 * dpr;
      let started = false;
      for (const s of visible) {
        const v = s[tr.key];
        if (v == null || !isFinite(v)) { started = false; continue; }
        const x = xOf(s.t);
        const y = yOf(v);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    // Legend
    let lx = pad.left + 4 * dpr;
    const ly = pad.top + 2 * dpr;
    ctx.font = `${9 * dpr}px sans-serif`;
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    for (const tr of traces) {
      ctx.fillStyle = tr.color;
      ctx.fillRect(lx, ly + 2 * dpr, 10 * dpr, 3 * dpr);
      lx += 14 * dpr;
      ctx.fillText(tr.label, lx, ly);
      lx += ctx.measureText(tr.label).width + 10 * dpr;
    }
  }
</script>

<svelte:window on:resize={resize} />

<div class="chart-container" style="height: {height}">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .chart-container {
    width: 100%;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  @media (max-width: 480px) {
    .chart-container { max-height: 100px; }
  }
</style>
