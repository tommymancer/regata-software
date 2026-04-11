<!--
  TwaGauge — stylized boat (always pointing up) with two "watch hand"
  lines radiating outward to show target TWA and actual TWA.

  Boat is centered so hands are visible at any TWA (0°–180°).
  The helmsman sees the gap at a glance and steers to close it.
  Port/starboard coloring.  All text sized for 2m+ reading distance.
-->
<script>
  import { getThemeColors, withAlpha } from "../lib/theme.js";
  import { onMount, afterUpdate } from "svelte";

  export let twa = null;        // current TWA (signed: −port +stbd)
  export let targetTwa = null;   // target TWA from polar

  let canvas;
  let ctx;
  let w = 300, h = 200;

  onMount(() => {
    ctx = canvas.getContext("2d");
    resize();
    draw();
  });

  afterUpdate(draw);

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    w = rect.width;
    h = rect.height;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  function draw() {
    if (!ctx) return;
    const colors = getThemeColors(canvas.parentElement);
    const el = canvas.parentElement;
    const portColor = getComputedStyle(el).getPropertyValue("--port").trim() || "#e74c3c";
    const stbdColor = getComputedStyle(el).getPropertyValue("--stbd").trim() || "#2ecc71";

    ctx.clearRect(0, 0, w, h);

    // ── Layout ─────────────────────────────────────────
    // Boat centered; hands radiate outward.
    // 0° = straight up (dead into wind).
    // 180° = straight down (dead downwind).
    const cx = w / 2;
    const cy = h / 2;
    // Radius must fit labels inside canvas at any angle
    const radius = Math.min(w / 2 - 44, h / 2 - 34);

    // ── Stylized boat (always pointing UP) ─────────────
    const bLen = 18;   // half-length bow to center
    const bW = 7;      // half-beam

    ctx.fillStyle = withAlpha(colors.text, 0.55);
    ctx.beginPath();
    ctx.moveTo(cx, cy - bLen);              // bow
    ctx.lineTo(cx + bW, cy + bLen * 0.5);   // stbd quarter
    ctx.lineTo(cx + bW * 0.3, cy + bLen);   // stbd transom
    ctx.lineTo(cx - bW * 0.3, cy + bLen);   // port transom
    ctx.lineTo(cx - bW, cy + bLen * 0.5);   // port quarter
    ctx.closePath();
    ctx.fill();

    // Centerline
    ctx.strokeStyle = withAlpha(colors.bg, 0.4);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx, cy - bLen + 3);
    ctx.lineTo(cx, cy + bLen - 3);
    ctx.stroke();

    // ── Helper: draw a "watch hand" line at given TWA ──
    function drawHand(angle, color, lineWidth, labelText) {
      if (angle == null) return;
      const absA = Math.abs(angle);
      const sign = angle < 0 ? -1 : 1;

      // 0° = up (-π/2). Positive TWA clockwise (stbd), negative ccw (port).
      const rad = (-Math.PI / 2) + sign * (absA * Math.PI / 180);

      const endX = cx + Math.cos(rad) * radius;
      const endY = cy + Math.sin(rad) * radius;

      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(endX, endY);
      ctx.stroke();
      ctx.restore();

      // Label at the tip
      if (labelText) {
        const labelR = radius + 20;
        const lx = cx + Math.cos(rad) * labelR;
        const ly = cy + Math.sin(rad) * labelR;

        ctx.fillStyle = color;
        ctx.font = "bold 40px monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(labelText, lx, ly);
      }
    }

    // ── Determine side color ───────────────────────────
    const refTwa = twa ?? targetTwa;
    if (refTwa == null) return;
    const isPort = refTwa < 0;
    const sideColor = isPort ? portColor : stbdColor;

    // ── Draw target TWA hand (dimmer, thicker) ─────────
    if (targetTwa != null) {
      const absT = Math.abs(targetTwa);
      const label = "TGT " + absT.toFixed(0) + "°";
      drawHand(targetTwa, withAlpha(sideColor, 0.35), 6, label);
    }

    // ── Draw actual TWA hand (bright, slightly thinner) ─
    if (twa != null) {
      const absA = Math.abs(twa);
      const label = absA.toFixed(0) + "°" + (isPort ? "P" : "S");
      drawHand(twa, sideColor, 4, label);
    }
  }
</script>

<svelte:window on:resize={resize} />

<div class="twa-wrap">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .twa-wrap {
    width: 100%;
    height: 100%;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
</style>
