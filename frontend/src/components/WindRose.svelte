<!--
  WindRose — Canvas-based wind angle display.

  Draws:
    - Compass ring with tick marks
    - AWA filled needle (cyan)
    - TWA outline needle (green)
    - Target TWA marks (orange) when available
    - TWS readout in center
    - Boat icon at top (heading reference)
-->
<script>
  import { onMount, afterUpdate } from "svelte";
  import { getThemeColors, withAlpha } from "../lib/theme.js";
  import { resizeCanvas } from "../lib/canvas.js";

  export let awa = null;       // apparent wind angle (signed degrees)
  export let twa = null;       // true wind angle (signed degrees)
  export let aws = null;       // apparent wind speed (kt)
  export let tws = null;       // true wind speed (kt)
  export let targetTwa = null; // target TWA from polars (signed degrees)

  let canvas;
  let ctx;
  let w = 0, h = 0;

  onMount(() => {
    ctx = canvas.getContext("2d");
    resize();
    draw();
  });

  afterUpdate(draw);

  function resize() {
    const result = resizeCanvas(canvas);
    w = result.size;
    h = result.size;
  }

  function draw() {
    if (!ctx) return;
    const colors = getThemeColors(canvas.parentElement);
    const dpr = devicePixelRatio;
    const cx = (w * dpr) / 2;
    const cy = (h * dpr) / 2;
    const r = cx * 0.85;

    ctx.clearRect(0, 0, w * dpr, h * dpr);

    // Compass ring
    drawCompassRing(cx, cy, r, dpr, colors);

    // Target TWA marks (orange)
    if (targetTwa != null) {
      drawTargetMark(cx, cy, r, targetTwa, dpr, colors);
      drawTargetMark(cx, cy, r, -targetTwa, dpr, colors);
    }

    // TWA needle (green outline)
    if (twa != null) {
      drawNeedle(cx, cy, r * 0.78, twa, withAlpha(colors.green, 0.6), false, dpr);
    }

    // AWA needle (cyan filled)
    if (awa != null) {
      drawNeedle(cx, cy, r * 0.85, awa, withAlpha(colors.accent, 0.85), true, dpr);
    }

    // Boat icon (top center)
    drawBoat(cx, cy - r * 0.12, dpr, colors);

    // Center readout
    drawCenter(cx, cy, dpr, colors);
  }

  function drawCompassRing(cx, cy, r, dpr, colors) {
    // Outer circle
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = 1 * dpr;
    ctx.stroke();

    // Tick marks every 10°, labels every 30°
    for (let deg = 0; deg < 360; deg += 10) {
      const rad = ((deg - 90) * Math.PI) / 180;
      const isMajor = deg % 30 === 0;
      const inner = isMajor ? r * 0.88 : r * 0.93;
      const outer = r;

      ctx.beginPath();
      ctx.moveTo(cx + inner * Math.cos(rad), cy + inner * Math.sin(rad));
      ctx.lineTo(cx + outer * Math.cos(rad), cy + outer * Math.sin(rad));
      ctx.strokeStyle = isMajor ? colors.textDim : colors.border;
      ctx.lineWidth = (isMajor ? 2 : 1) * dpr;
      ctx.stroke();

      // Labels (only 0-180 range, mirrored)
      if (isMajor && deg <= 180) {
        const labelR = r * 0.82;
        const displayDeg = deg;
        ctx.font = `${10 * dpr}px sans-serif`;
        ctx.fillStyle = colors.textDim;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        // Starboard side (right)
        const radS = ((deg - 90) * Math.PI) / 180;
        ctx.fillText(displayDeg + "°", cx + labelR * Math.cos(radS), cy + labelR * Math.sin(radS));

        // Port side (left, mirror)
        if (deg > 0 && deg < 180) {
          const radP = ((-deg - 90) * Math.PI) / 180;
          ctx.fillText(displayDeg + "°", cx + labelR * Math.cos(radP), cy + labelR * Math.sin(radP));
        }
      }
    }
  }

  function drawNeedle(cx, cy, length, angle, color, filled, dpr) {
    const rad = ((angle - 90) * Math.PI) / 180;
    const tipX = cx + length * Math.cos(rad);
    const tipY = cy + length * Math.sin(rad);

    // Needle triangle
    const halfWidth = 8 * dpr;
    const perpRad = rad + Math.PI / 2;
    const baseX1 = cx + halfWidth * Math.cos(perpRad);
    const baseY1 = cy + halfWidth * Math.sin(perpRad);
    const baseX2 = cx - halfWidth * Math.cos(perpRad);
    const baseY2 = cy - halfWidth * Math.sin(perpRad);

    ctx.beginPath();
    ctx.moveTo(tipX, tipY);
    ctx.lineTo(baseX1, baseY1);
    ctx.lineTo(baseX2, baseY2);
    ctx.closePath();

    if (filled) {
      ctx.fillStyle = color;
      ctx.fill();
    } else {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2 * dpr;
      ctx.stroke();
    }
  }

  function drawTargetMark(cx, cy, r, angle, dpr, colors) {
    const rad = ((angle - 90) * Math.PI) / 180;
    const innerR = r * 0.95;
    const outerR = r * 1.02;

    ctx.beginPath();
    ctx.moveTo(cx + innerR * Math.cos(rad), cy + innerR * Math.sin(rad));
    ctx.lineTo(cx + outerR * Math.cos(rad), cy + outerR * Math.sin(rad));
    ctx.strokeStyle = colors.orange;
    ctx.lineWidth = 3 * dpr;
    ctx.stroke();
  }

  function drawBoat(cx, topY, dpr, colors) {
    const s = 6 * dpr;
    ctx.beginPath();
    ctx.moveTo(cx, topY - s);
    ctx.lineTo(cx - s * 0.6, topY + s);
    ctx.lineTo(cx + s * 0.6, topY + s);
    ctx.closePath();
    ctx.fillStyle = colors.text;
    ctx.fill();
  }

  function drawCenter(cx, cy, dpr, colors) {
    // TWS in center
    ctx.font = `bold ${40 * dpr}px "SF Mono", "Menlo", monospace`;
    ctx.fillStyle = colors.green;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const twsText = tws != null ? tws.toFixed(1) : "---";
    ctx.fillText(twsText, cx, cy - 8 * dpr);

    ctx.font = `${9 * dpr}px sans-serif`;
    ctx.fillStyle = colors.textDim;
    ctx.fillText("TWS kt", cx, cy + 10 * dpr);

    // AWS below
    ctx.font = `bold ${28 * dpr}px "SF Mono", "Menlo", monospace`;
    ctx.fillStyle = colors.accent;
    const awsText = aws != null ? aws.toFixed(1) : "---";
    ctx.fillText(awsText, cx, cy + 28 * dpr);

    ctx.font = `${8 * dpr}px sans-serif`;
    ctx.fillStyle = colors.textDim;
    ctx.fillText("AWS kt", cx, cy + 40 * dpr);
  }
</script>

<svelte:window on:resize={resize} />

<div class="wind-rose-container">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .wind-rose-container {
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
