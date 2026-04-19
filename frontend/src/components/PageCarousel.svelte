<!--
  PageCarousel — 3-page swipe navigator with labeled dot indicators.

  Design: START · RACE · TACTICS — active page shows elongated pill + label.
  Dots sit at the bottom of the carousel, above the bottom nav.

  Props:
    pages     : Array<{name, label}>  — page definitions
    current   : number                — current page index (bindable)
-->
<script>
  export let pages = [];
  export let current = 0;

  let touchStartX = 0;

  function next() { current = (current + 1) % pages.length; }
  function prev() { current = (current - 1 + pages.length) % pages.length; }

  function onKeyDown(e) {
    if (e.key === "ArrowRight") next();
    else if (e.key === "ArrowLeft") prev();
  }

  function onTouchStart(e) {
    touchStartX = e.touches[0].clientX;
  }

  function onTouchEnd(e) {
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {
      dx < 0 ? next() : prev();
    }
  }
</script>

<svelte:window on:keydown={onKeyDown} />

<div class="carousel"
     on:touchstart={onTouchStart}
     on:touchend={onTouchEnd}
     role="tablist">
  <div class="page-content">
    <slot />
  </div>

  <div class="pager">
    {#each pages as page, i}
      <button
        class="pager-item"
        class:active={i === current}
        on:click={() => current = i}
        role="tab"
        aria-selected={i === current}
        aria-label={page.label}
      >
        <span class="pager-dot" class:active={i === current}></span>
        {#if i === current}
          <span class="pager-label">{page.label}</span>
        {/if}
      </button>
    {/each}
  </div>
</div>

<style>
  .carousel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    touch-action: pan-y;
  }
  .page-content {
    flex: 1;
    overflow: hidden;
  }
  .pager {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    flex-shrink: 0;
    pointer-events: auto;
  }
  .pager-item {
    display: flex;
    align-items: center;
    gap: 5px;
    background: none;
    border: none;
    padding: 4px;
    cursor: pointer;
    touch-action: manipulation;
    opacity: 0.35;
    transition: opacity 0.2s;
  }
  .pager-item.active {
    opacity: 1;
  }
  .pager-dot {
    width: 5px;
    height: 5px;
    border-radius: 3px;
    background: var(--text-dim);
    transition: all 0.2s;
  }
  .pager-dot.active {
    width: 18px;
    background: var(--accent);
  }
  .pager-label {
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 800;
    color: var(--accent);
    letter-spacing: 1.5px;
  }
</style>
