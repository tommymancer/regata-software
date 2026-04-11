<!--
  RaceTimerDisplay — large countdown/elapsed time digits with color coding.

  Props:
    state  — "idle" | "countdown" | "racing"
    secs   — seconds (countdown: remaining, racing: elapsed)
-->
<script>
  export let state = "idle";
  export let secs = null;

  $: minutes = secs != null ? Math.floor(Math.abs(secs) / 60) : 0;
  $: seconds = secs != null ? Math.floor(Math.abs(secs) % 60) : 0;

  $: display = secs == null
    ? "--:--"
    : state === "racing" && Math.abs(secs) >= 3600
      ? formatHMS(secs)
      : `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  $: timerColor =
    state === "idle" ? "var(--text-dim)"
    : state === "racing" ? "var(--green)"
    : secs <= 10 ? "var(--red)"
    : secs <= 60 ? "var(--orange)"
    : "var(--text)";

  $: stateLabel =
    state === "idle" ? "PRONTO"
    : state === "countdown" ? "COUNTDOWN"
    : "REGATA";

  function formatHMS(s) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }
</script>

<div class="timer-display">
  <div class="state-label" style="color: {timerColor}">{stateLabel}</div>
  <div class="digits" style="color: {timerColor}">{display}</div>
</div>

<style>
  .timer-display {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .state-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    opacity: 0.8;
  }
  .digits {
    font-family: "SF Mono", "Menlo", "Cascadia Mono", monospace;
    font-size: 144px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -4px;
    text-shadow: var(--glow-text);
  }
</style>
