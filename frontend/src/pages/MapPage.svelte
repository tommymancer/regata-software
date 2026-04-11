<!--
  MapPage — Canvas-based map showing boat position, track trail,
  wind arrow, racing marks, course overlay, and sight bearing lines.

  Boat-centered view: the boat stays at center, the world scrolls around it.
  Auto-scales to fit the visible track + marks.
-->
<script>
  import { onMount, afterUpdate, onDestroy } from "svelte";
  import { lat, lon, hdg, twd, tws, laylinePort, laylineStbd, nextMark, btw, dtw } from "../stores/boat.js";
  import { history } from "../stores/history.js";
  import { getThemeColors, withAlpha } from "../lib/theme.js";
  import { LAKE_LUGANO_SHORE, MELIDE_BRIDGE } from "../lib/lake-lugano.js";

  let canvas;
  let ctx;
  let w = 300, h = 300;
  let marks = [];
  let courseData = null;
  let sightData = null;
  let showHelm = false;

  function helm(delta) {
    fetch("/api/sim/helm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delta }),
    }).catch(() => {});
  }

  function tack() {
    // Tack: flip heading across the wind by ~100° (quick shortcut)
    fetch("/api/sim/helm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delta: $twd != null ? 100 : 90 }),
    }).catch(() => {});
  }

  let sightInterval;
  let redrawInterval;

  let setupMarks = [];  // marks from course-setup (pre-apply)

  // Fetch marks + course on mount
  onMount(() => {
    ctx = canvas.getContext("2d");
    resize();
    draw();
    fetchMarks();
    fetchCourse();
    fetchSightBearings();
    fetchSetupMarks();
    // Poll sight bearings and setup marks every 2s
    sightInterval = setInterval(() => { fetchSightBearings(); fetchSetupMarks(); }, 2000);
    // Redraw at ~4 Hz to keep boat position live
    redrawInterval = setInterval(draw, 250);
  });

  onDestroy(() => {
    if (sightInterval) clearInterval(sightInterval);
    if (redrawInterval) clearInterval(redrawInterval);
  });

  async function fetchMarks() {
    try {
      const res = await fetch("/api/marks");
      marks = await res.json();
      draw();
    } catch { /* ignore */ }
  }

  async function fetchSetupMarks() {
    try {
      const res = await fetch("/api/course-setup/status");
      const data = await res.json();
      setupMarks = (data.marks || []).filter(m => m.resolved);
      draw();
    } catch { /* ignore */ }
  }

  async function fetchCourse() {
    try {
      const res = await fetch("/api/course");
      const data = await res.json();
      if (data && data.rc) courseData = data;
      draw();
    } catch { /* ignore */ }
  }

  async function fetchSightBearings() {
    try {
      const res = await fetch("/api/sight/bearings");
      sightData = await res.json();
      draw();
    } catch { /* ignore */ }
  }

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

  // ── Coordinate conversion ────────────────────────────────────
  // Convert lat/lon to local meters relative to boat position.

  function toLocal(latVal, lonVal, boatLat, boatLon) {
    const dLat = (latVal - boatLat) * 111320;
    const dLon = (lonVal - boatLon) * 111320 * Math.cos(boatLat * Math.PI / 180);
    return { x: dLon, y: -dLat }; // screen: y-down, north is up
  }

  function draw() {
    if (!ctx) return;
    const colors = getThemeColors(canvas.parentElement);

    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = colors.bg;
    ctx.fillRect(0, 0, w, h);

    const boatLat = $lat;
    const boatLon = $lon;

    if (boatLat == null || boatLon == null) {
      ctx.fillStyle = colors.textDim;
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Waiting for position…", w / 2, h / 2);
      return;
    }

    // ── Determine scale ──────────────────────────────────────
    let points = [];
    const hist = $history;
    for (const s of hist) {
      if (s.lat != null && s.lon != null) {
        points.push(toLocal(s.lat, s.lon, boatLat, boatLon));
      }
    }
    // Marks from mark store are NOT included in bounding box;
    // only the generated course points matter for zoom level.
    // Include course points in bounding box
    if (courseData) {
      points.push(toLocal(courseData.rc.lat, courseData.rc.lon, boatLat, boatLon));
      points.push(toLocal(courseData.pin.lat, courseData.pin.lon, boatLat, boatLon));
      points.push(toLocal(courseData.windward.lat, courseData.windward.lon, boatLat, boatLon));
    }
    // Include setup marks in bounding box
    for (const m of setupMarks) {
      points.push(toLocal(m.lat, m.lon, boatLat, boatLon));
    }
    // Include computed mark
    if (sightData && sightData.computed_mark) {
      points.push(toLocal(sightData.computed_mark.lat, sightData.computed_mark.lon, boatLat, boatLon));
    }
    points.push({ x: 0, y: 0 }); // boat itself

    // Include nearby shore points so the lake outline is visible
    for (const [lt, ln] of LAKE_LUGANO_SHORE) {
      const sp = toLocal(lt, ln, boatLat, boatLon);
      const d = Math.sqrt(sp.x * sp.x + sp.y * sp.y);
      if (d < 5000) points.push(sp); // only within 5 km
    }

    let maxDist = 200; // minimum 200m view radius
    for (const p of points) {
      const d = Math.max(Math.abs(p.x), Math.abs(p.y));
      if (d > maxDist) maxDist = d;
    }
    maxDist *= 1.2; // 20% padding

    const viewSize = Math.min(w, h) * 0.9;
    const scale = viewSize / (2 * maxDist); // pixels per meter
    const cx = w / 2;
    const cy = h / 2;

    function toScreen(local) {
      return {
        sx: cx + local.x * scale,
        sy: cy + local.y * scale,
      };
    }

    // ── Lake shoreline (background layer) ──────────────────
    drawLakeShoreline(ctx, colors, boatLat, boatLon, toScreen);

    // ── Grid / scale bar ─────────────────────────────────────
    drawScaleBar(ctx, colors, maxDist, scale, w, h);

    // ── Start line (from course data) ────────────────────────
    if (courseData) {
      drawStartLine(ctx, colors, courseData, boatLat, boatLon, toScreen, scale);
      drawGhostMark(ctx, colors, courseData.windward, boatLat, boatLon, toScreen);
    }

    // ── Sight bearing lines ──────────────────────────────────
    if (sightData && sightData.sightings && sightData.sightings.length > 0) {
      drawSightBearings(ctx, colors, sightData, boatLat, boatLon, toScreen, maxDist);
    }

    // ── Computed mark ────────────────────────────────────────
    if (sightData && sightData.computed_mark) {
      drawComputedMark(ctx, colors, sightData.computed_mark, boatLat, boatLon, toScreen);
    }

    // ── Track trail ──────────────────────────────────────────
    if (hist.length > 1) {
      ctx.beginPath();
      let started = false;
      for (const s of hist) {
        if (s.lat == null || s.lon == null) continue;
        const local = toLocal(s.lat, s.lon, boatLat, boatLon);
        const { sx, sy } = toScreen(local);
        if (!started) {
          ctx.moveTo(sx, sy);
          started = true;
        } else {
          ctx.lineTo(sx, sy);
        }
      }
      ctx.strokeStyle = withAlpha(colors.accent, 0.4);
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // ── Laylines from active mark ─────────────────────────
    if ($laylinePort != null && $laylineStbd != null && $nextMark) {
      const activeMark = marks.find(m => m.name === $nextMark) ||
                         setupMarks.find(m => m.name === $nextMark);
      if (activeMark) {
        drawLaylines(ctx, colors, activeMark, boatLat, boatLon, toScreen, maxDist,
                     $laylinePort, $laylineStbd);
      }
    }

    // ── Marks ────────────────────────────────────────────────
    for (const m of marks) {
      const local = toLocal(m.lat, m.lon, boatLat, boatLon);
      const { sx, sy } = toScreen(local);

      ctx.beginPath();
      const r = m.mark_type === "reference" ? 3 : 5;
      ctx.arc(sx, sy, r, 0, Math.PI * 2);
      const markColor = markTypeColor(m.mark_type, colors);
      ctx.fillStyle = markColor;
      ctx.fill();

      ctx.fillStyle = colors.textDim;
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(m.name, sx, sy - r - 3);
    }

    // ── Boat ─────────────────────────────────────────────────
    // ── Setup marks (pre-apply, dashed outline) ────────
    for (const m of setupMarks) {
      const local = toLocal(m.lat, m.lon, boatLat, boatLon);
      const { sx, sy } = toScreen(local);

      ctx.save();
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.arc(sx, sy, 6, 0, Math.PI * 2);
      const mc = markTypeColor(m.mark_type, colors);
      ctx.strokeStyle = mc;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();

      ctx.fillStyle = mc;
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(m.name, sx, sy - 10);

      const typeLabel = { start_rc: "RC", start_pin: "PIN", windward: "WW", leeward: "LW", gate: "GATE" }[m.mark_type];
      if (typeLabel) {
        ctx.fillStyle = colors.textDim;
        ctx.font = "8px sans-serif";
        ctx.fillText(typeLabel, sx, sy + 14);
      }
    }

    drawBoat(ctx, cx, cy, $hdg, colors);

    // ── Wind arrow (top-right corner) ────────────────────────
    if ($twd != null) {
      drawWindArrow(ctx, w - 35, 45, $twd, $tws, colors);
    }

    // ── Position text (bottom-left) ──────────────────────────
    ctx.fillStyle = colors.textDim;
    ctx.font = "10px monospace";
    ctx.textAlign = "left";
    ctx.fillText(
      `${boatLat.toFixed(5)}°N  ${boatLon.toFixed(5)}°E`,
      8, h - 8
    );
  }

  // ── Start line drawing ──────────────────────────────────────
  function drawStartLine(ctx, colors, course, boatLat, boatLon, toScreen, scale) {
    const rcLocal = toLocal(course.rc.lat, course.rc.lon, boatLat, boatLon);
    const pinLocal = toLocal(course.pin.lat, course.pin.lon, boatLat, boatLon);
    const rcScr = toScreen(rcLocal);
    const pinScr = toScreen(pinLocal);

    // Line between RC and Pin
    ctx.beginPath();
    ctx.moveTo(rcScr.sx, rcScr.sy);
    ctx.lineTo(pinScr.sx, pinScr.sy);
    ctx.strokeStyle = colors.red;
    ctx.lineWidth = 2;
    ctx.stroke();

    // RC dot + label
    ctx.beginPath();
    ctx.arc(rcScr.sx, rcScr.sy, 4, 0, Math.PI * 2);
    ctx.fillStyle = colors.red;
    ctx.fill();
    ctx.fillStyle = colors.textDim;
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("RC", rcScr.sx, rcScr.sy - 7);

    // Pin dot + label
    ctx.beginPath();
    ctx.arc(pinScr.sx, pinScr.sy, 4, 0, Math.PI * 2);
    ctx.fillStyle = colors.red;
    ctx.fill();
    ctx.fillStyle = colors.textDim;
    ctx.fillText("PIN", pinScr.sx, pinScr.sy - 7);
  }

  // ── Ghost windward mark (visible to user, not to nav engine) ──
  function drawGhostMark(ctx, colors, wm, boatLat, boatLon, toScreen) {
    const local = toLocal(wm.lat, wm.lon, boatLat, boatLon);
    const { sx, sy } = toScreen(local);

    // Dashed hollow circle
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.arc(sx, sy, 8, 0, Math.PI * 2);
    ctx.strokeStyle = withAlpha(colors.orange, 0.6);
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.setLineDash([]);

    // X mark inside
    const s = 4;
    ctx.beginPath();
    ctx.moveTo(sx - s, sy - s);
    ctx.lineTo(sx + s, sy + s);
    ctx.moveTo(sx + s, sy - s);
    ctx.lineTo(sx - s, sy + s);
    ctx.strokeStyle = withAlpha(colors.orange, 0.6);
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();

    // Label
    ctx.fillStyle = withAlpha(colors.textDim, 0.6);
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("GHOST", sx, sy - 12);
  }

  // ── Sight bearing lines ────────────────────────────────────
  function drawSightBearings(ctx, colors, data, boatLat, boatLon, toScreen, maxDist) {
    ctx.save();
    ctx.setLineDash([6, 4]);

    for (const s of data.sightings) {
      const originLocal = toLocal(s.lat, s.lon, boatLat, boatLon);
      const originScr = toScreen(originLocal);

      // Extend bearing line ~2x maxDist in the bearing direction
      const extendM = maxDist * 2;
      const brRad = (s.bearing * Math.PI) / 180;
      const endLocal = {
        x: originLocal.x + Math.sin(brRad) * extendM,
        y: originLocal.y - Math.cos(brRad) * extendM,  // y-down: north is negative
      };
      const endScr = toScreen(endLocal);

      ctx.beginPath();
      ctx.moveTo(originScr.sx, originScr.sy);
      ctx.lineTo(endScr.sx, endScr.sy);
      ctx.strokeStyle = withAlpha(colors.accent, 0.5);
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Small dot at sighting origin
      ctx.beginPath();
      ctx.arc(originScr.sx, originScr.sy, 3, 0, Math.PI * 2);
      ctx.fillStyle = colors.accent;
      ctx.fill();
    }

    ctx.restore();
  }

  // ── Computed mark (triangulated) ──────────────────────────
  function drawComputedMark(ctx, colors, cm, boatLat, boatLon, toScreen) {
    const local = toLocal(cm.lat, cm.lon, boatLat, boatLon);
    const { sx, sy } = toScreen(local);

    // Solid green dot
    ctx.beginPath();
    ctx.arc(sx, sy, 6, 0, Math.PI * 2);
    ctx.fillStyle = colors.green;
    ctx.fill();

    // Bright ring
    ctx.beginPath();
    ctx.arc(sx, sy, 9, 0, Math.PI * 2);
    ctx.strokeStyle = withAlpha(colors.green, 0.5);
    ctx.lineWidth = 2;
    ctx.stroke();

    // Label
    ctx.fillStyle = colors.green;
    ctx.font = "bold 10px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("MARK", sx, sy - 13);
  }

  function drawBoat(ctx, x, y, heading, colors) {
    const size = 12;
    ctx.save();
    ctx.translate(x, y);
    if (heading != null) {
      ctx.rotate(((heading - 90) * Math.PI) / 180);
    }

    ctx.beginPath();
    ctx.moveTo(size, 0);
    ctx.lineTo(-size * 0.6, -size * 0.5);
    ctx.lineTo(-size * 0.4, 0);
    ctx.lineTo(-size * 0.6, size * 0.5);
    ctx.closePath();

    ctx.fillStyle = colors.accent;
    ctx.fill();
    ctx.strokeStyle = colors.text;
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.restore();
  }

  function drawWindArrow(ctx, x, y, twdDeg, twsKt, colors) {
    const len = 25;
    ctx.save();
    ctx.translate(x, y);

    // Rotate so arrow points in the direction wind BLOWS (FROM→TO).
    // Arrow default = down (+y = south). TWD=0 (from north) → no rotation.
    ctx.rotate((twdDeg * Math.PI) / 180);

    ctx.beginPath();
    ctx.moveTo(0, -len);
    ctx.lineTo(0, len);
    ctx.strokeStyle = withAlpha(colors.text, 0.6);
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, len);
    ctx.lineTo(-5, len - 8);
    ctx.moveTo(0, len);
    ctx.lineTo(5, len - 8);
    ctx.stroke();

    ctx.restore();

    ctx.fillStyle = colors.textDim;
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("WIND", x, y - len - 6);
    if (twsKt != null) {
      ctx.fillText(`${twsKt.toFixed(0)}kt`, x, y + len + 12);
    }
  }

  function drawScaleBar(ctx, colors, maxDist, scale, w, h) {
    const niceDistances = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000];
    let barDist = niceDistances[0];
    for (const d of niceDistances) {
      if (d * scale > 30 && d * scale < w * 0.3) {
        barDist = d;
        break;
      }
    }
    const barPx = barDist * scale;

    ctx.strokeStyle = withAlpha(colors.textDim, 0.5);
    ctx.lineWidth = 1;
    const bx = 10;
    const by = h - 25;

    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx + barPx, by);
    ctx.moveTo(bx, by - 4);
    ctx.lineTo(bx, by + 4);
    ctx.moveTo(bx + barPx, by - 4);
    ctx.lineTo(bx + barPx, by + 4);
    ctx.stroke();

    ctx.fillStyle = colors.textDim;
    ctx.font = "9px sans-serif";
    ctx.textAlign = "center";
    const label = barDist >= 1000 ? `${(barDist / 1000).toFixed(1)} km` : `${barDist} m`;
    ctx.fillText(label, bx + barPx / 2, by - 6);
  }

  function drawLaylines(ctx, colors, mark, boatLat, boatLon, toScreen, maxDist, portBrg, stbdBrg) {
    const markLocal = toLocal(mark.lat, mark.lon, boatLat, boatLon);
    const markScr = toScreen(markLocal);
    const extendM = maxDist * 2.5;

    // Port layline (red/port color)
    const portColor = getComputedStyle(ctx.canvas.parentElement).getPropertyValue("--port").trim() || "#e74c3c";
    const stbdColor = getComputedStyle(ctx.canvas.parentElement).getPropertyValue("--stbd").trim() || "#2ecc71";

    for (const [brg, color] of [[portBrg, portColor], [stbdBrg, stbdColor]]) {
      // Layline goes FROM the mark TOWARD the boat side (opposite of bearing)
      // The bearing is the heading the boat sails TO reach the mark,
      // so the line from the mark extends in the opposite direction (brg + 180)
      const awayRad = ((brg + 180) * Math.PI) / 180;
      const endLocal = {
        x: markLocal.x + Math.sin(awayRad) * extendM,
        y: markLocal.y - Math.cos(awayRad) * extendM,
      };
      const endScr = toScreen(endLocal);

      ctx.save();
      ctx.setLineDash([8, 6]);
      ctx.beginPath();
      ctx.moveTo(markScr.sx, markScr.sy);
      ctx.lineTo(endScr.sx, endScr.sy);
      ctx.strokeStyle = withAlpha(color, 0.5);
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();
    }
  }

  // ── Lake shoreline ─────────────────────────────────────────
  function drawLakeShoreline(ctx, colors, boatLat, boatLon, toScreen) {
    if (!LAKE_LUGANO_SHORE.length) return;

    // Water fill
    ctx.beginPath();
    for (let i = 0; i < LAKE_LUGANO_SHORE.length; i++) {
      const [lt, ln] = LAKE_LUGANO_SHORE[i];
      const local = toLocal(lt, ln, boatLat, boatLon);
      const { sx, sy } = toScreen(local);
      if (i === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    }
    ctx.closePath();
    ctx.fillStyle = withAlpha(colors.accent, 0.06);
    ctx.fill();

    // Shore outline
    ctx.beginPath();
    for (let i = 0; i < LAKE_LUGANO_SHORE.length; i++) {
      const [lt, ln] = LAKE_LUGANO_SHORE[i];
      const local = toLocal(lt, ln, boatLat, boatLon);
      const { sx, sy } = toScreen(local);
      if (i === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    }
    ctx.closePath();
    ctx.strokeStyle = withAlpha(colors.textDim, 0.35);
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Melide bridge
    if (MELIDE_BRIDGE.length === 2) {
      const [a, b] = MELIDE_BRIDGE;
      const aLocal = toLocal(a[0], a[1], boatLat, boatLon);
      const bLocal = toLocal(b[0], b[1], boatLat, boatLon);
      const aScr = toScreen(aLocal);
      const bScr = toScreen(bLocal);
      ctx.save();
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(aScr.sx, aScr.sy);
      ctx.lineTo(bScr.sx, bScr.sy);
      ctx.strokeStyle = withAlpha(colors.textDim, 0.4);
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();
    }
  }

  function markTypeColor(type, colors) {
    switch (type) {
      case "windward": return colors.accent;
      case "leeward": return colors.green;
      case "gate": return colors.orange;
      case "start":
      case "start_rc":
      case "start_pin": return colors.red;
      default: return withAlpha(colors.textDim, 0.5);
    }
  }
</script>

<svelte:window on:resize={resize} />

<div class="page" style="width:100%;height:100%;">
  <canvas bind:this={canvas} style="display:block;width:100%;height:100%;"></canvas>
  {#if showHelm}
    <div class="helm-overlay">
      <button class="helm-btn" on:click={() => helm(-10)}>-10</button>
      <button class="helm-btn" on:click={() => helm(-5)}>-5</button>
      <button class="helm-btn tack" on:click={tack}>TACK</button>
      <button class="helm-btn" on:click={() => helm(5)}>+5</button>
      <button class="helm-btn" on:click={() => helm(10)}>+10</button>
    </div>
  {/if}
  <button class="helm-toggle" on:click={() => showHelm = !showHelm}>
    {showHelm ? "HIDE" : "HELM"}
  </button>
</div>

<style>
  .page {
    width: 100%;
    height: 100%;
    overflow: hidden;
    position: relative;
  }

  .helm-overlay {
    position: absolute;
    bottom: 40px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: var(--gap-compact);
  }

  .helm-btn {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 14px;
    border: 2px solid var(--accent);
    border-radius: 8px;
    background: var(--card);
    color: var(--accent);
    cursor: pointer;
    touch-action: manipulation;
    opacity: 0.85;
  }

  .helm-btn:active {
    opacity: 1;
    background: var(--accent);
    color: var(--bg);
  }

  .helm-btn.tack {
    border-color: var(--orange);
    color: var(--orange);
    font-size: 12px;
  }

  .helm-btn.tack:active {
    background: var(--orange);
    color: var(--bg);
  }

  .helm-toggle {
    position: absolute;
    bottom: 8px;
    right: 8px;
    font-family: "SF Mono", "Menlo", monospace;
    font-size: var(--label-xs-size);
    font-weight: var(--label-sm-weight);
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--card);
    color: var(--text-dim);
    cursor: pointer;
    touch-action: manipulation;
    letter-spacing: 0.5px;
  }
</style>
