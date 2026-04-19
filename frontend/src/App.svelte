<!--
  App.svelte — Root component (redesigned).

  - Connects WebSocket on mount
  - Provides theme CSS variables (Notte / Giorno / Sole)
  - 3-page race carousel: START → RACE → TACTICS
  - Settings as a dedicated tab
  - Menu for tools/utilities
-->
<script>
  import { onMount, onDestroy } from "svelte";
  import { connect, disconnect, connectionStatus } from "./stores/boat.js";
  import { startHistory, stopHistory } from "./stores/history.js";
  import PageCarousel from "./components/PageCarousel.svelte";
  import PageStart from "./pages/PageStart.svelte";
  import PageRace from "./pages/PageRace.svelte";
  import PageTactics from "./pages/PageTactics.svelte";
  import PageSettings from "./pages/PageSettings.svelte";

  // Legacy pages — accessible from menu
  import TrimPage from "./pages/TrimPage.svelte";
  import CalibrationPage from "./pages/CalibrationPage.svelte";
  import TrimGuidePage from "./pages/TrimGuidePage.svelte";
  import PolarDiagramPage from "./pages/PolarDiagramPage.svelte";
  import SystemPage from "./pages/SystemPage.svelte";
  import CourseSetupPage from "./pages/CourseSetupPage.svelte";
  import SensorsPage from "./pages/SensorsPage.svelte";

  // Carousel: 3 pages matching the race arc
  const pages = [
    { name: "start",   label: "START" },
    { name: "race",    label: "RACE" },
    { name: "tactics", label: "TACTICS" },
  ];

  // Menu: tools/utilities accessed via hamburger menu
  const menuItems = [
    { name: "settings",       label: "Impostazioni",    icon: "⚙" },
    { name: "course_setup",   label: "Campo di Regata", icon: "◎" },
    { name: "sensors",        label: "Sensori",         icon: "▤" },
    { name: "calibration",    label: "Calibrazione",    icon: "◎" },
    { name: "trim",           label: "Trim Book",       icon: "▤" },
    { name: "trim_guide",     label: "Trim Guide",      icon: "▧" },
    { name: "polar_diagram",  label: "Polar Diagram",   icon: "◑" },
    { name: "system",         label: "Sistema",         icon: "⚙" },
  ];

  let currentPage = 1; // Start on RACE
  let menuOpen = false;
  let menuPage = null; // null = carousel visible, string = menu page name
  let theme = "dark";

  function openMenu() { menuOpen = true; }
  function closeMenu() { menuOpen = false; }
  function goToMenuPage(name) {
    menuPage = name;
    menuOpen = false;
  }
  function backToCarousel() { menuPage = null; }

  const themes = ["dark", "light", "sun"];
  const themeLabels = { dark: "Notte", light: "Giorno", sun: "Sole" };
  const themeIcons = { dark: "☾", light: "☀", sun: "◉" };

  function cycleTheme() {
    const idx = themes.indexOf(theme);
    theme = themes[(idx + 1) % themes.length];
  }

  // Allow setting theme from child components (e.g., PageSettings)
  function setTheme(t) {
    if (themes.includes(t)) theme = t;
  }

  // Keyboard simulator controls:
  //   A/D  = helm +/-5 deg
  //   W/S  = TWS +/-2 kt
  function handleKey(e) {
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
  {#if menuPage === null}
    <!-- Main 3-page carousel -->
    <PageCarousel {pages} bind:current={currentPage}>
      {#if pages[currentPage].name === "start"}
        <PageStart />
      {:else if pages[currentPage].name === "race"}
        <PageRace />
      {:else if pages[currentPage].name === "tactics"}
        <PageTactics />
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
        {#if menuPage === "settings"}
          <PageSettings {theme} on:theme={(e) => setTheme(e.detail)} />
        {:else if menuPage === "course_setup"}
          <CourseSetupPage />
        {:else if menuPage === "sensors"}
          <SensorsPage />
        {:else if menuPage === "calibration"}
          <CalibrationPage />
        {:else if menuPage === "trim"}
          <TrimPage />
        {:else if menuPage === "trim_guide"}
          <TrimGuidePage />
        {:else if menuPage === "polar_diagram"}
          <PolarDiagramPage />
        {:else if menuPage === "system"}
          <SystemPage />
        {/if}
      </div>
    </div>
  {/if}

  <!-- Bottom nav: Live / Sessions / Settings -->
  <nav class="bottom-nav">
    <button class="nav-btn" class:active={menuPage === null}
            on:click={backToCarousel}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
      <span>Live</span>
    </button>
    <button class="nav-btn" on:click={openMenu}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      <span>Menu</span>
    </button>
    <button class="nav-btn" class:active={menuPage === "settings"}
            on:click={() => goToMenuPage("settings")}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
      <span>Impostazioni</span>
    </button>
  </nav>

  <!-- Menu overlay -->
  {#if menuOpen}
    <div class="menu-overlay" on:click={closeMenu}>
      <nav class="menu-panel" on:click|stopPropagation>
        <div class="menu-header">MENU</div>
        {#each menuItems as item}
          {#if item.name !== "settings"}
            <button class="menu-item" on:click={() => goToMenuPage(item.name)}
                    class:active={menuPage === item.name}>
              <span class="menu-icon">{item.icon}</span>
              <span class="menu-label">{item.label}</span>
            </button>
          {/if}
        {/each}
        <div class="menu-divider"></div>
        <button class="menu-item theme-item" on:click={cycleTheme}>
          <span class="menu-icon">{themeIcons[theme]}</span>
          <span class="menu-label">Tema: {themeLabels[theme]}</span>
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
    font-family: "Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  @keyframes aqpulse {
    0% { transform: scale(0.5); opacity: 0.8; }
    100% { transform: scale(1.4); opacity: 0; }
  }

  /* ── Notte theme (default) — dark instrument cockpit ──────── */
  .app[data-theme="dark"] {
    --bg:           #06090c;
    --surface:      #0e1318;
    --surface-alt:  #151b22;
    --card:         #0e1318;
    --card-glow:    #151b22;
    --border:       rgba(255,255,255,0.08);
    --border-strong: rgba(255,255,255,0.18);
    --text:         #e8eef4;
    --text-dim:     #7a8a99;
    --text-faint:   #4a5866;
    --accent:       #4fa8d8;
    --accent-strong: #7cc3e8;
    --green:        #3fbf7f;
    --orange:       #f2b84b;
    --red:          #e86a5a;
    --wind:         #4fa8d8;
    --port:         #e04848;
    --stbd:         #3fbf7f;
    --glow-text:    0 0 20px rgba(232, 238, 244, 0.1);
    --glow-accent:  0 0 24px rgba(79, 168, 216, 0.2);
    --glow-green:   0 0 20px rgba(63, 191, 127, 0.25);
    --glow-red:     0 0 20px rgba(232, 106, 90, 0.25);
    --glow-orange:  0 0 20px rgba(242, 184, 75, 0.25);
    --scanline:     rgba(255, 255, 255, 0.008);
  }

  /* ── Giorno theme (light, daytime) ───────────────────────── */
  .app[data-theme="light"] {
    --bg:           #f5f6f7;
    --surface:      #ffffff;
    --surface-alt:  #eef0f2;
    --card:         #ffffff;
    --card-glow:    #eef0f2;
    --border:       rgba(10,20,30,0.08);
    --border-strong: rgba(10,20,30,0.22);
    --text:         #0a1420;
    --text-dim:     #5a6674;
    --text-faint:   #8a96a4;
    --accent:       #0c63a6;
    --accent-strong: #084a80;
    --green:        #1a8a52;
    --orange:       #c47a0c;
    --red:          #c43a2a;
    --wind:         #0c63a6;
    --port:         #c43a2a;
    --stbd:         #1a8a52;
    --glow-text:    none;
    --glow-accent:  none;
    --glow-green:   none;
    --glow-red:     none;
    --glow-orange:  none;
    --scanline:     transparent;
  }

  /* ── Sole theme (high-contrast, direct sunlight) ─────────── */
  .app[data-theme="sun"] {
    --bg:           #fffef4;
    --surface:      #ffffff;
    --surface-alt:  #fff8d8;
    --card:         #ffffff;
    --card-glow:    #fff8d8;
    --border:       #000000;
    --border-strong: #000000;
    --text:         #000000;
    --text-dim:     #000000;
    --text-faint:   #3a3a3a;
    --accent:       #000000;
    --accent-strong: #000000;
    --green:        #006b2f;
    --orange:       #8a4800;
    --red:          #a81500;
    --wind:         #000000;
    --port:         #a81500;
    --stbd:         #006b2f;
    --glow-text:    none;
    --glow-accent:  none;
    --glow-green:   none;
    --glow-red:     none;
    --glow-orange:  none;
    --scanline:     transparent;
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

    /* Font stacks */
    --font-mono: "JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace;
    --font-numeric: "Barlow", "Helvetica Neue", Helvetica, Arial, sans-serif;
    --font-text: "Inter", "Helvetica Neue", Helvetica, Arial, sans-serif;

    /* Spacing tokens */
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

  /* Subtle scan-line overlay for cockpit feel (only on dark themes) */
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
    overflow-y: auto;
  }

  /* ── Bottom navigation bar ──────────────────────────── */
  .bottom-nav {
    display: flex;
    border-top: 1px solid var(--border);
    background: var(--surface);
    flex-shrink: 0;
    z-index: 10;
  }
  .nav-btn {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 0 4px;
    background: none;
    border: none;
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    cursor: pointer;
    touch-action: manipulation;
  }
  .nav-btn.active {
    color: var(--accent);
  }
  .nav-btn:active { opacity: 0.6; }

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
    background: var(--surface);
    border: none;
    border-bottom: 1px solid var(--border);
    color: var(--accent);
    font-family: var(--font-text);
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
    font-family: var(--font-mono);
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
    background: rgba(0, 0, 0, 0.55);
    z-index: 50;
    display: flex;
    justify-content: flex-end;
    animation: fadeIn 0.15s ease;
  }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

  .menu-panel {
    width: 260px;
    max-width: 75vw;
    height: 100%;
    background: var(--surface);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 0;
    animation: slideIn 0.2s ease;
    overflow-y: auto;
  }
  @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }

  .menu-header {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--text-dim);
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
    font-family: var(--font-text);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    touch-action: manipulation;
    text-align: left;
    transition: background 0.15s;
  }
  .menu-item:active { background: var(--surface-alt); }
  .menu-item.active {
    color: var(--accent);
  }
  .menu-icon {
    font-size: 18px;
    width: 24px;
    text-align: center;
    color: var(--text-dim);
  }
  .menu-item.active .menu-icon { color: var(--accent); }
  .menu-label {
    letter-spacing: 0.02em;
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

  /* ── Global typography for instrument values ──────────────── */
  :global(.instrument-value) {
    font-family: var(--font-numeric);
    font-weight: 700;
    color: var(--text);
    line-height: 1;
  }

  /* ── Global card style ─────────────────────────────────────── */
  :global(.instrument-card) {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
</style>
