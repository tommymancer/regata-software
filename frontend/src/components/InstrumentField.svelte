<!--
  InstrumentField — Core display component for a single instrument value.

  Props:
    label   : string  — short label ("TWA", "BSP", "VMG")
    value   : string  — formatted display value
    unit    : string  — unit label ("kt", "°", "%")
    size    : "lg" | "md" | "sm"  — digit size
    color   : string  — optional CSS color override
-->
<script>
  export let label = "";
  export let value = "---";
  export let unit = "";
  export let size = "md";
  export let color = null;

  let flash = false;
  let prevValue = value;
  $: if (value !== prevValue) {
    prevValue = value;
    flash = true;
    setTimeout(() => flash = false, 120);
  }
</script>

<div class="field field-{size}">
  <span class="label">{label}</span>
  <span class="value" class:flash style:color>{value}</span>
  {#if unit}<span class="unit">{unit}</span>{/if}
</div>

<style>
  .field {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4px 8px;
    min-width: 0;
  }
  .label {
    font-size: var(--label-sm-size);  /* 13px → 11px, intentional tightening */
    font-weight: var(--label-sm-weight);
    text-transform: uppercase;
    letter-spacing: var(--label-sm-spacing);
    color: var(--text-dim);
    line-height: 1;
    margin-bottom: 2px;
  }
  .value {
    font-family: "SF Mono", "Menlo", "Cascadia Mono", monospace;
    font-weight: 800;
    line-height: 1;
    color: var(--text);
    text-shadow: var(--glow-text);
    transition: opacity 0.12s ease;
  }
  .value.flash {
    opacity: 0.85;
  }
  .unit {
    font-size: var(--label-xs-size);  /* 12px → 9px, intentional shrink for units */
    font-weight: var(--label-xs-weight);
    color: var(--text-dim);
    line-height: 1;
    margin-top: 2px;
    letter-spacing: var(--label-xs-spacing);
  }

  .field-lg .value { font-size: clamp(64px, 20vw, 112px); }
  .field-lg .label { font-size: 16px; font-weight: var(--label-md-weight); letter-spacing: var(--label-md-spacing); }
  .field-lg .unit  { font-size: 16px; }

  .field-md .value { font-size: clamp(48px, 14vw, 72px); }
  .field-md .label { font-size: 14px; font-weight: var(--label-sm-weight); letter-spacing: var(--label-sm-spacing); }
  .field-md .unit  { font-size: 14px; }

  .field-sm .value { font-size: clamp(36px, 10vw, 44px); }
  .field-sm .label { font-size: var(--label-sm-size); }
  .field-sm .unit  { font-size: var(--label-xs-size); }

  @media (max-width: 480px) {
    .field { padding: 2px 4px; }
    .field-lg .label { font-size: 14px; }
    .field-lg .unit  { font-size: 14px; }
  }
</style>
