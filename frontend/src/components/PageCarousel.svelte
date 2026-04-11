<!--
  PageCarousel — Swipe/arrow-key page navigator.

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

  <div class="dots">
    {#each pages as page, i}
      <button
        class="dot"
        class:active={i === current}
        on:click={() => current = i}
        role="tab"
        aria-selected={i === current}
        aria-label={page.label}
      ></button>
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
  .dots {
    display: flex;
    justify-content: center;
    gap: 8px;
    padding: 6px 0;
    flex-shrink: 0;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1px solid var(--text-dim);
    background: transparent;
    opacity: 0.35;
    cursor: pointer;
    padding: 0;
    transition: all 0.25s ease;
  }
  .dot.active {
    opacity: 1;
    background: var(--accent);
    border-color: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    transform: scale(1.2);
  }

  @media (max-width: 480px) {
    .dots { gap: 6px; padding: 4px 0; }
    .dot { width: 7px; height: 7px; }
  }
</style>
