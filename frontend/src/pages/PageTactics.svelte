<!--
  PageTactics — Full-screen map with marks, track, boat, laylines.

  Replaces both "Regatta map" and raw "Map" pages.
  Compass rose top-right, wind indicator top-left,
  next-mark bearing/distance overlay at bottom.
-->
<script>
  import { lat, lon, hdg, cog, twd, tws, twa, targetTwa,
           btw, dtw, nextMark,
           distToPortLayline, distToStbdLayline,
           laylinePort, laylineStbd }
    from "../stores/boat.js";
  import { history } from "../stores/history.js";

  // Viewport dimensions for the SVG
  const W = 390, H = 660;

  // Track: convert GPS history to normalized viewport positions
  // We'll use a simple relative-to-boat projection
  $: track = buildTrack($history, $lat, $lon);

  function buildTrack(hist, boatLat, boatLon) {
    if (!hist || hist.length < 2 || boatLat == null) return [];
    // Use last 60 track points
    const pts = hist.slice(-60).filter(h => h.lat != null && h.lon != null);
    if (pts.length < 2) return [];

    // Scale: 1nm ≈ 200px on screen
    const scale = 200 / 0.001; // degrees per nm ≈ 1/60
    const nmPerDeg = 60;
    const pxPerNm = 200;
    const pxPerDeg = pxPerNm * nmPerDeg;

    return pts.map(p => ({
      x: W / 2 + (p.lon - boatLon) * pxPerDeg * Math.cos(boatLat * Math.PI / 180),
      y: H * 0.6 - (p.lat - boatLat) * pxPerDeg,
    }));
  }

  // Boat position (centered lower-mid)
  const boatX = W / 2;
  const boatY = H * 0.6;

  // Laylines from next mark
  $: twdVal = $twd ?? 0;
  $: btwDeg = $btw ?? 0;
  $: dtwNm = $dtw ?? 0;

  // Mark position — estimated from BTW and DTW
  $: markDist = dtwNm * 200 / 0.05; // rough pixel distance
  $: markDistClamped = Math.min(markDist, 280);
  $: markX = boatX + Math.sin(btwDeg * Math.PI / 180) * markDistClamped;
  $: markY = boatY - Math.cos(btwDeg * Math.PI / 180) * markDistClamped;

  // Laylines come from the backend: `layline_port_deg` / `layline_stbd_deg`
  // are COMPASS BEARINGS = the heading a boat on that tack sails toward the mark.
  // The backend applies target_TWA (from polar, interpolated on TWS) + leeway
  // correction + current correction.
  //
  // To draw the layline from the mark extending back toward the approaching
  // boat, we go in the OPPOSITE direction (+180°).
  //
  // Fallback (polar-only, no leeway/current): TWD ± target_TWA.
  $: tackAngle = $targetTwa ?? 40;
  $: portBearing = $laylinePort ?? ((twdVal + tackAngle + 360) % 360);
  $: stbdBearing = $laylineStbd ?? ((twdVal - tackAngle + 360) % 360);

  const layLen = 400;
  function rad(deg) { return deg * Math.PI / 180; }

  // Extend the layline from the mark AWAY from the boat's approach heading.
  $: layPortEnd = {
    x: markX + Math.sin(rad(portBearing + 180)) * layLen,
    y: markY - Math.cos(rad(portBearing + 180)) * layLen,
  };
  $: layStbdEnd = {
    x: markX + Math.sin(rad(stbdBearing + 180)) * layLen,
    y: markY - Math.cos(rad(stbdBearing + 180)) * layLen,
  };

  // Format distance
  function fmtDist(nm) {
    if (nm == null) return "---";
    return nm < 0.1 ? `${Math.round(nm * 1852)}m` : `${nm.toFixed(2)}nm`;
  }
</script>

<div class="page">
  <!-- Header -->
  <div class="header">
    <span>TATTICA &middot; CAMPO</span>
    <span>{$nextMark ? `BOA: ${$nextMark}` : ""}</span>
  </div>

  <!-- Map -->
  <div class="map-container">
    <svg width="100%" height="100%" viewBox="0 0 {W} {H}"
      preserveAspectRatio="xMidYMid slice"
      style="display:block; position:absolute; inset:0;">

      <!-- Grid -->
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none"
            stroke="var(--grid-stroke)" stroke-width="1"/>
        </pattern>
      </defs>
      <rect width={W} height={H} fill="url(#grid)"/>

      <!-- Laylines from mark (if mark position known) -->
      {#if $btw != null && $dtw != null && $dtw > 0}
        <line x1={markX} y1={markY} x2={layPortEnd.x} y2={layPortEnd.y}
          stroke="var(--port)" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>
        <line x1={markX} y1={markY} x2={layStbdEnd.x} y2={layStbdEnd.y}
          stroke="var(--stbd)" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.7"/>

        <!-- Layline ladders -->
        {#each [0.25, 0.5, 0.75] as r}
          {@const pp = { x: markX + (layPortEnd.x - markX) * r, y: markY + (layPortEnd.y - markY) * r }}
          {@const sp = { x: markX + (layStbdEnd.x - markX) * r, y: markY + (layStbdEnd.y - markY) * r }}
          <line x1={pp.x} y1={pp.y} x2={sp.x} y2={sp.y}
            stroke="var(--text-dim)" stroke-width="1" stroke-dasharray="2,3" opacity="0.35"/>
        {/each}

        <!-- Bearing line to mark -->
        <line x1={boatX} y1={boatY} x2={markX} y2={markY}
          stroke="var(--accent)" stroke-width="1" stroke-dasharray="2,5" opacity="0.5"/>

        <!-- Mark -->
        <circle cx={markX} cy={markY} r="8" fill="var(--orange)"/>
        <circle cx={markX} cy={markY} r="16"
          fill="none" stroke="var(--orange)" stroke-width="1" opacity="0.4">
          <animate attributeName="r" values="14;22;14" dur="2.2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.6;0;0.6" dur="2.2s" repeatCount="indefinite"/>
        </circle>
        {#if $nextMark}
          <text x={markX} y={markY + 3} fill="#fff"
            font-family="var(--font-mono)" font-size="9" font-weight="800"
            text-anchor="middle" letter-spacing="0.5">{$nextMark}</text>
        {/if}
      {/if}

      <!-- GPS track -->
      {#if track.length >= 2}
        <polyline points={track.map(p => `${p.x},${p.y}`).join(" ")}
          fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round"
          stroke-linejoin="round" opacity="0.65"/>
        {#each track.slice(0, -1) as p, i}
          <circle cx={p.x} cy={p.y} r="1.5" fill="var(--accent)"
            opacity={0.2 + (i / track.length) * 0.6}/>
        {/each}
      {/if}

      <!-- Boat -->
      <g transform="translate({boatX}, {boatY}) rotate({$hdg ?? 0})">
        <line x1="0" y1="0" x2="0" y2="-34" stroke="var(--accent)" stroke-width="1.5" opacity="0.6"/>
        <path d="M 0 -14 L 8 10 L 0 7 L -8 10 Z" fill="var(--accent)"/>
        <circle r="3" fill="var(--text)" stroke="var(--bg)" stroke-width="1"/>
      </g>
    </svg>

    <!-- Compass rose — top right -->
    <div class="compass-rose">
      <svg width="56" height="56" viewBox="0 0 56 56">
        <g transform="rotate({-($hdg ?? 0)}, 28, 28)">
          <polygon points="28,6 32,24 28,20 24,24" fill="var(--red)"/>
          <polygon points="28,50 32,32 28,36 24,32" fill="var(--text-dim)"/>
        </g>
        <text x="28" y="17" text-anchor="middle" fill="var(--text)"
          font-family="var(--font-mono)" font-size="9" font-weight="800">N</text>
      </svg>
    </div>

    <!-- Wind indicator — top left -->
    <div class="wind-indicator">
      <svg width="22" height="22" viewBox="0 0 22 22">
        <g transform="rotate({(twdVal - 180)}, 11, 11)">
          <line x1="11" y1="3" x2="11" y2="18" stroke="var(--wind)" stroke-width="2"/>
          <polygon points="11,20 7,14 15,14" fill="var(--wind)"/>
        </g>
      </svg>
      <div class="wind-info">
        <span class="wind-speed">{$tws != null ? Math.round($tws) : "---"}<span class="wind-unit">kt</span></span>
        <span class="wind-dir">{twdVal}&deg;</span>
      </div>
    </div>

    <!-- Next mark overlay — bottom -->
    {#if $nextMark || ($btw != null)}
      <div class="next-mark-overlay">
        {#if $nextMark}
          <div class="mark-icon">{$nextMark}</div>
        {/if}
        <div class="mark-info">
          <span class="mark-label">PROSSIMA BOA</span>
          <div class="mark-data">
            <span class="mark-btw">{$btw != null ? Math.round($btw) : "---"}&deg;
              <span class="mark-data-label">BTW</span>
            </span>
            <span class="mark-dtw">{fmtDist($dtw)}
              <span class="mark-data-label">DTW</span>
            </span>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .page {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-text);
  }

  .header {
    padding: 8px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 1.5px;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  /* ── Map container ───────────────────────── */
  .map-container {
    flex: 1;
    min-height: 0;
    position: relative;
    overflow: hidden;
    --grid-stroke: var(--border);
  }
  :global(.app[data-theme="dark"]) .map-container {
    background: #08131c;
    --grid-stroke: rgba(255,255,255,0.05);
  }
  :global(.app[data-theme="light"]) .map-container {
    background: #eaf0f3;
    --grid-stroke: rgba(10,20,30,0.08);
  }
  :global(.app[data-theme="sun"]) .map-container {
    background: #fffef4;
    --grid-stroke: rgba(0,0,0,0.12);
  }

  /* ── Compass rose ────────────────────────── */
  .compass-rose {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 56px;
    height: 56px;
    border-radius: 28px;
    background: var(--surface);
    border: 1.5px solid var(--border-strong);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* ── Wind indicator ──────────────────────── */
  .wind-indicator {
    position: absolute;
    top: 10px;
    left: 10px;
    padding: 6px 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 3px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .wind-info {
    display: flex;
    flex-direction: column;
  }
  .wind-speed {
    font-family: var(--font-numeric);
    font-size: 18px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -1px;
    line-height: 1;
  }
  .wind-unit {
    font-size: 11px;
    color: var(--text-dim);
  }
  .wind-dir {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 1px;
  }

  /* ── Next mark overlay ───────────────────── */
  .next-mark-overlay {
    position: absolute;
    left: 10px;
    right: 10px;
    bottom: 10px;
    background: var(--surface);
    border-radius: 4px;
    border: 1px solid var(--border);
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .mark-icon {
    width: 40px;
    height: 40px;
    border-radius: 20px;
    background: var(--orange);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
    flex-shrink: 0;
  }
  :global(.app[data-theme="sun"]) .mark-icon { color: #fff; }
  :global(.app[data-theme="dark"]) .mark-icon { color: #1a1305; }
  :global(.app[data-theme="light"]) .mark-icon { color: #1a1305; }

  .mark-info {
    flex: 1;
  }
  .mark-label {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--text-dim);
    font-weight: 700;
  }
  .mark-data {
    display: flex;
    gap: 14px;
    margin-top: 2px;
  }
  .mark-btw, .mark-dtw {
    font-family: var(--font-numeric);
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.5px;
  }
  .mark-data-label {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 1px;
    margin-left: 3px;
  }
</style>
