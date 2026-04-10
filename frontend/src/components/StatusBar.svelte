<!--
  StatusBar — Bottom bar showing connection, GPS, logging status, and menu button.
-->
<script>
  import { createEventDispatcher } from "svelte";
  import { connectionStatus, gpsFix } from "../stores/boat.js";
  import SailSelector from "./SailSelector.svelte";

  const dispatch = createEventDispatcher();
</script>

<div class="status-bar">
  <span class="status-item">
    <span class="dot" class:green={$connectionStatus === "connected"}
                       class:yellow={$connectionStatus === "connecting"}
                       class:red={$connectionStatus === "disconnected"}></span>
    {$connectionStatus === "connected" ? "LIVE" : $connectionStatus === "connecting" ? "..." : "OFF"}
  </span>

  <span class="status-item">
    <span class="dot" class:green={$gpsFix} class:red={!$gpsFix}></span>
    GPS
  </span>

  <span class="status-item">
    <SailSelector />
  </span>

  <button class="menu-btn" on:click={() => dispatch("menu")} aria-label="Menu">
    <span class="hamburger">≡</span>
  </button>
</div>

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 16px;
    background: var(--card);
    border-top: 1px solid var(--border);
    font-size: var(--label-sm-size);
    font-weight: var(--label-sm-weight);
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
    height: 56px;
    flex-shrink: 0;
  }
  .status-item {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .menu-btn {
    background: none;
    border: none;
    color: var(--accent);
    cursor: pointer;
    padding: 0 4px;
    touch-action: manipulation;
    display: flex;
    align-items: center;
  }
  .menu-btn:active { opacity: 0.5; }
  .hamburger {
    font-size: 22px;
    line-height: 1;
    text-shadow: var(--glow-accent);
  }
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-dim);
    transition: background 0.3s, box-shadow 0.3s;
  }
  .dot.green {
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
  }
  .dot.yellow {
    background: var(--orange);
    box-shadow: 0 0 6px var(--orange);
  }
  .dot.red {
    background: var(--red);
    box-shadow: 0 0 6px var(--red);
  }
</style>
