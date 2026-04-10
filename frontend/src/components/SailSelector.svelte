<!--
  SailSelector — Two-step sail picker (main + headsail).
  Calls POST /api/sails to switch both upwash and polar systems.
-->
<script>
  import { onMount } from "svelte";
  import { boatState } from "../stores/boat.js";

  let open = false;
  let sailData = null;
  let loading = false;

  $: configKey = $boatState?.active_sail_config ?? "main_1__genoa";
  $: shortLabel = sailData?.label ?? configKey;

  onMount(async () => {
    try {
      const res = await fetch("/api/sails");
      sailData = await res.json();
    } catch (e) { /* ignore */ }
  });

  async function openPicker() {
    open = true;
    try {
      const res = await fetch("/api/sails");
      sailData = await res.json();
    } catch (e) {
      sailData = null;
    }
  }

  async function pickMain(main) {
    if (!sailData || main === sailData.active_main) return;
    loading = true;
    try {
      const res = await fetch("/api/sails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_main: main }),
      });
      if (res.ok) {
        const data = await res.json();
        sailData = { ...sailData, active_main: data.active_main, active_config_key: data.active_config_key };
        boatState.update(s => s ? { ...s, active_sail_config: data.active_config_key } : s);
        // Re-fetch to update labels
        const r2 = await fetch("/api/sails");
        sailData = await r2.json();
      }
    } catch (e) { /* ignore */ }
    loading = false;
  }

  async function pickHeadsail(headsail) {
    if (!sailData || headsail === sailData.active_headsail) return;
    loading = true;
    try {
      const res = await fetch("/api/sails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_headsail: headsail }),
      });
      if (res.ok) {
        const data = await res.json();
        sailData = { ...sailData, active_headsail: data.active_headsail, active_config_key: data.active_config_key };
        boatState.update(s => s ? { ...s, active_sail_config: data.active_config_key } : s);
        const r2 = await fetch("/api/sails");
        sailData = await r2.json();
      }
    } catch (e) { /* ignore */ }
    loading = false;
  }

  // Build flat headsail list from the nested config
  $: allHeadsails = sailData ? Object.entries(sailData.sails?.headsails ?? {}).flatMap(
    ([cat, names]) => names.map(n => ({ name: n, category: cat }))
  ) : [];
</script>

<button class="sail-btn" on:click={openPicker} title="Cambia vele">
  {shortLabel}
</button>

{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="overlay" on:click|self={() => (open = false)}>
    <div class="picker">
      <div class="picker-title">RANDA</div>
      <div class="grid">
        {#each sailData?.sails?.mains ?? [] as main}
          <button
            class="sail-option"
            class:active={main === sailData?.active_main}
            disabled={loading}
            on:click={() => pickMain(main)}
          >
            <span class="opt-short">{main.replace("_", " ").toUpperCase()}</span>
          </button>
        {/each}
      </div>

      <div class="picker-title" style="margin-top: 12px;">PRUA</div>
      <div class="grid">
        {#each allHeadsails as hs}
          <button
            class="sail-option"
            class:active={hs.name === sailData?.active_headsail}
            disabled={loading}
            on:click={() => pickHeadsail(hs.name)}
          >
            <span class="opt-short">{hs.name.replace("_", " ").toUpperCase()}</span>
            <span class="opt-label">{hs.category}</span>
          </button>
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .sail-btn {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.05em;
    color: var(--accent);
    background: transparent;
    border: 1px solid var(--accent);
    border-radius: 4px;
    padding: 2px 6px;
    cursor: pointer;
    touch-action: manipulation;
    text-shadow: var(--glow-accent);
    transition: opacity 0.15s;
  }
  .sail-btn:active {
    opacity: 0.7;
  }

  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .picker {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    min-width: 260px;
    max-width: 320px;
  }
  .picker-title {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.2em;
    color: var(--accent);
    text-align: center;
    margin-bottom: 12px;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .sail-option {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 10px 6px;
    border: 2px solid var(--border);
    border-radius: 8px;
    background: var(--bg);
    cursor: pointer;
    touch-action: manipulation;
    transition: border-color 0.2s, opacity 0.15s;
  }
  .sail-option:active:not(:disabled) {
    opacity: 0.7;
  }
  .sail-option.active {
    border-color: var(--accent);
    background: linear-gradient(180deg, var(--card-glow, var(--card)) 0%, var(--card) 100%);
  }
  .opt-short {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 14px;
    font-weight: 800;
    color: var(--text);
  }
  .sail-option.active .opt-short {
    color: var(--accent);
    text-shadow: var(--glow-accent);
  }
  .opt-label {
    font-size: 9px;
    color: var(--text-dim);
    text-align: center;
    line-height: 1.2;
  }
</style>
