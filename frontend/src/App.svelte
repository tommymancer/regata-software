<!--
  App.svelte — Root component.

  - Connects WebSocket on mount
  - Provides theme CSS variables (night / sun / red-night)
  - Page carousel with swipe + keyboard navigation
-->
<script>
  import { onMount, onDestroy } from "svelte";
  import { connect, disconnect, connectionStatus } from "./stores/boat.js";
  import { startHistory, stopHistory } from "./stores/history.js";
  import PageCarousel from "./components/PageCarousel.svelte";
  import StatusBar from "./components/StatusBar.svelte";
  import RegattaPage from "./pages/RegattaPage.svelte";
  import RaceTimerPage from "./pages/RaceTimerPage.svelte";
  import TrimPage from "./pages/TrimPage.svelte";
  import PolarPage from "./pages/PolarPage.svelte";
  import CourseSetupPage from "./pages/CourseSetupPage.svelte";
  import MapPage from "./pages/MapPage.svelte";
  import SensorsPage from "./pages/SensorsPage.svelte";
  import SystemPage from "./pages/SystemPage.svelte";
  import CalibrationPage from "./pages/CalibrationPage.svelte";
  import TrimGuidePage from "./pages/TrimGuidePage.svelte";
  import PolarDiagramPage from "./pages/PolarDiagramPage.svelte";

  // Carousel: pages you swipe through while sailing
  const pages = [
    { name: "course_setup", label: "Course Setup" },
    { name: "race_timer",  label: "Race Timer" },
    { name: "regatta",     label: "Regatta" },
    { name: "map",         label: "Map" },
    { name: "sensors",     label: "Sensors" },
  ];

  // Menu: settings/tools accessed via hamburger menu
  const menuItems = [
    { name: "calibration",    label: "Calibrazione",    icon: "◎" },
    { name: "trim",           label: "Trim Book",       icon: "▤" },
    { name: "trim_guide",     label: "Trim Guide",      icon: "▧" },
    { name: "polar_diagram",  label: "Polar Diagram",   icon: "◑" },
    { name: "polar",          label: "Polar Learning",  icon: "◐" },
    { name: "system",         label: "Sistema",         icon: "⚙" },
  ];

  let currentPage = 1; // Start on Race Timer; Course Setup is page 0 (swipe left)
  let menuOpen = false;
  let menuPage = null; // null = carousel visible, string = menu page name
  let theme = "night";

  function openMenu() { menuOpen = true; }
  function closeMenu() { menuOpen = false; }
  function goToMenuPage(name) {
    menuPage = name;
    menuOpen = false;
  }
  function backToCarousel() { menuPage = null; }

  const themes = ["night", "sun", "red-night"];

  function cycleTheme() {
    const idx = themes.indexOf(theme);
    theme = themes[(idx + 1) % themes.length];
  }

  // Keyboard simulator controls:
  //   A/D  = helm ±5°
  //   W/S  = TWS ±2 kt (more / less wind)
  function handleKey(e) {
    // Don't fire simulator controls when typing in form fields
    const tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === "a" || e.key === "A") {
      fetch("/api/sim/helm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delta: -5 }),
      }).catch(() => {});
    } else if (e.key === "d" || e.key === "D") {
      fetch("/api/sim/helm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delta: 5 }),
      }).catch(() => {});
    } else if (e.key === "w" || e.key === "W") {
      fetch("/api/sim/wind", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tws_delta: 2 }),
      }).catch(() => {});
    } else if (e.key === "s" || e.key === "S") {
      fetch("/api/sim/wind", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tws_delta: -2 }),
      }).catch(() => {});
    }
  }

  onMount(() => { connect(); startHistory(); });
  onDestroy(() => { disconnect(); stopHistory(); });
</script>

<svelte:window on:keydown={handleKey} />

<div class="app" data-theme={theme}>
  {#if $connectionStatus !== "connected"}
    <div class="conn-banner" class:connecting={$connectionStatus === "connecting"}>
      <span class="conn-icon">{$connectionStatus === "connecting" ? "◌" : "✕"}</span>
      {$connectionStatus === "connecting" ? "Connessione…" : "Disconnesso — riprovo…"}
    </div>
  {/if}

  {#if menuPage === null}
    <!-- Main carousel -->
    <PageCarousel {pages} bind:current={currentPage}>
      {#if pages[currentPage].name === "course_setup"}
        <CourseSetupPage />
      {:else if pages[currentPage].name === "regatta"}
        <RegattaPage />
      {:else if pages[currentPage].name === "race_timer"}
        <RaceTimerPage />
      {:else if pages[currentPage].name === "map"}
        <MapPage />
      {:else if pages[currentPage].name === "sensors"}
        <SensorsPage />
      {/if}
    </PageCarousel>
  {:else}
    <!-- Menu page (full screen with back button) -->
    <div class="menu-page-wrapper">
      <button class="menu-back-btn" on:click={backToCarousel}>
        <span class="back-arrow">‹</span>
        <span class="back-label">{menuItems.find(m => m.name === menuPage)?.label ?? ""}</span>
      </button>
      <div class="menu-page-content">
        {#if menuPage === "calibration"}
          <CalibrationPage />
        {:else if menuPage === "trim"}
          <TrimPage />
        {:else if menuPage === "trim_guide"}
          <TrimGuidePage />
        {:else if menuPage === "polar_diagram"}
          <PolarDiagramPage />
        {:else if menuPage === "polar"}
          <PolarPage />
        {:else if menuPage === "system"}
          <SystemPage />
        {/if}
      </div>
    </div>
  {/if}

  <StatusBar on:menu={openMenu} />

  <!-- Menu overlay -->
  {#if menuOpen}
    <div class="menu-overlay" on:click={closeMenu}>
      <nav class="menu-panel" on:click|stopPropagation>
        <div class="menu-header">MENU</div>
        {#each menuItems as item}
          <button class="menu-item" on:click={() => goToMenuPage(item.name)}
                  class:active={menuPage === item.name}>
            <span class="menu-icon">{item.icon}</span>
            <span class="menu-label">{item.label}</span>
          </button>
        {/each}
        <div class="menu-divider"></div>
        <button class="menu-item theme-item" on:click={cycleTheme}>
          <span class="menu-icon">{theme === "night" ? "☾" : theme === "sun" ? "☀" : "◉"}</span>
          <span class="menu-label">Tema: {theme === "night" ? "Notte" : theme === "sun" ? "Giorno" : "Rosso"}</span>
        </button>
      </nav>
    </div>
  {/if}

</div>

<style>
  :global(*) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    margin: 0;
    overflow: hidden;
    font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* ── Night theme (default) — deep ocean cockpit ──────────── */
  .app[data-theme="night"] {
    --bg:        #050e1a;
    --card:      #0b1726;
    --card-glow: #0d1d33;
    --border:    #152742;
    --text:      #e4ecf7;
    --text-dim:  #3d6a8e;
    --accent:    #00d4ff;
    --green:     #00e676;
    --orange:    #ffab00;
    --red:       #ff1744;
    --port:      #ff1744;
    --stbd:      #00e676;
    --glow-text: 0 0 20px rgba(228, 236, 247, 0.15);
    --glow-accent: 0 0 24px rgba(0, 212, 255, 0.25);
    --glow-green: 0 0 20px rgba(0, 230, 118, 0.3);
    --glow-red:  0 0 20px rgba(255, 23, 68, 0.3);
    --glow-orange: 0 0 20px rgba(255, 171, 0, 0.3);
    --scanline:  rgba(255, 255, 255, 0.012);
  }

  /* ── Sun theme (maximum contrast for direct sunlight) ──────── */
  .app[data-theme="sun"] {
    --bg:        #000000;
    --card:      #080808;
    --card-glow: #101010;
    --border:    #1a1a1a;
    --text:      #ffffff;
    --text-dim:  #888888;
    --accent:    #ffd000;
    --green:     #00ff66;
    --orange:    #ffaa00;
    --red:       #ff3333;
    --port:      #ff3333;
    --stbd:      #00ff66;
    --glow-text: 0 0 12px rgba(255, 255, 255, 0.2);
    --glow-accent: 0 0 20px rgba(255, 208, 0, 0.3);
    --glow-green: 0 0 16px rgba(0, 255, 102, 0.35);
    --glow-red:  0 0 16px rgba(255, 51, 51, 0.35);
    --glow-orange: 0 0 16px rgba(255, 170, 0, 0.35);
    --scanline:  rgba(255, 255, 255, 0.008);
  }

  /* ── Red-night theme (preserves night vision) ────────────── */
  .app[data-theme="red-night"] {
    --bg:        #0c0404;
    --card:      #180808;
    --card-glow: #200c0c;
    --border:    #2a1010;
    --text:      #ff6b6b;
    --text-dim:  #802020;
    --accent:    #ff4444;
    --green:     #ff6b6b;
    --orange:    #ff8844;
    --red:       #ff4444;
    --port:      #ff4444;
    --stbd:      #ff8844;
    --glow-text: 0 0 16px rgba(255, 68, 68, 0.2);
    --glow-accent: 0 0 20px rgba(255, 68, 68, 0.3);
    --glow-green: 0 0 16px rgba(255, 107, 107, 0.3);
    --glow-red:  0 0 16px rgba(255, 68, 68, 0.3);
    --glow-orange: 0 0 16px rgba(255, 136, 68, 0.3);
    --scanline:  rgba(255, 0, 0, 0.015);
  }

  .app {
    width: 100vw;
    height: 100vh;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    user-select: none;
    position: relative;

    /* Spacing tokens — hybrid */
    --gap-compact: 6px;
    --gap-airy: 12px;
    --pad-compact: 4px;
    --pad-airy: 8px;

    /* Typography scale */
    --label-xs-size: 9px;
    --label-xs-weight: 700;
    --label-xs-spacing: 0.08em;
    --label-sm-size: 11px;
    --label-sm-weight: 700;
    --label-sm-spacing: 0.12em;
    --label-md-size: 13px;
    --label-md-weight: 800;
    --label-md-spacing: 0.12em;
  }

  /* Subtle scan-line overlay for cockpit instrument feel */
  .app::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 100;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      var(--scanline) 2px,
      var(--scanline) 4px
    );
  }

  :global(.page) {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: var(--pad-airy);
    gap: var(--gap-airy);
    overflow-y: auto;
  }

  /* ── Menu page wrapper (back button + content) ───────────── */
  .menu-page-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .menu-back-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: var(--card);
    border: none;
    border-bottom: 1px solid var(--border);
    color: var(--accent);
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    flex-shrink: 0;
    touch-action: manipulation;
  }
  .menu-back-btn:active { opacity: 0.6; }
  .back-arrow {
    font-size: 22px;
    line-height: 1;
  }
  .back-label {
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .menu-page-content {
    flex: 1;
    overflow: hidden;
  }

  /* ── Menu overlay ────────────────────────────────────────── */
  .menu-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 50;
    display: flex;
    justify-content: flex-end;
    animation: fadeIn 0.15s ease;
  }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

  .menu-panel {
    width: 240px;
    max-width: 75vw;
    height: 100%;
    background: var(--card);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 0;
    animation: slideIn 0.2s ease;
    overflow-y: auto;
  }
  @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }

  .menu-header {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.2em;
    color: var(--accent);
    text-shadow: var(--glow-accent);
    padding: 20px 20px 12px;
  }
  .menu-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 20px;
    background: none;
    border: none;
    color: var(--text);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    touch-action: manipulation;
    text-align: left;
    transition: background 0.15s;
  }
  .menu-item:active { background: var(--border); }
  .menu-item.active {
    color: var(--accent);
    background: rgba(0, 212, 255, 0.06);
  }
  .menu-icon {
    font-size: 18px;
    width: 24px;
    text-align: center;
    color: var(--text-dim);
  }
  .menu-item.active .menu-icon { color: var(--accent); }
  .menu-label {
    letter-spacing: 0.03em;
  }
  .menu-divider {
    height: 1px;
    background: var(--border);
    margin: 8px 20px;
  }
  .theme-item {
    color: var(--text-dim);
    font-size: 13px;
  }

  .conn-banner {
    background: var(--red);
    color: #fff;
    text-align: center;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .conn-banner.connecting {
    background: var(--orange);
    color: #000;
  }

  .conn-icon {
    font-size: 16px;
  }

  /* ── Global typography for instrument values ──────────────── */
  :global(.instrument-value) {
    font-family: "SF Mono", "Menlo", "Cascadia Mono", monospace;
    font-weight: 700;
    color: var(--text);
    text-shadow: var(--glow-text);
    line-height: 1;
  }

  /* ── Global card style ─────────────────────────────────────── */
  :global(.instrument-card) {
    background: linear-gradient(180deg, var(--card-glow) 0%, var(--card) 100%);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
</style>
