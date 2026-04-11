/**
 * Audio — Web Audio API beep generation for race timer.
 *
 * No audio files needed; tones are synthesised in real time.
 */

let audioCtx = null;

function getCtx() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  // Resume context if suspended (autoplay policy)
  if (audioCtx.state === "suspended") audioCtx.resume();
  return audioCtx;
}

/**
 * Play a simple sine-wave beep.
 * @param {number} frequency  Hz (default 880)
 * @param {number} duration   seconds (default 0.15)
 * @param {number} volume     0–1 (default 0.3)
 */
export function beep(frequency = 880, duration = 0.15, volume = 0.3) {
  const ctx = getCtx();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = frequency;
  osc.type = "sine";
  gain.gain.value = volume;

  const now = ctx.currentTime;
  osc.start(now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
  osc.stop(now + duration + 0.05);
}

/** Short high beep — each minute mark (5, 4, 3, 2, 1). */
export function minuteBeep() {
  beep(880, 0.3, 0.35);
}

/** Medium beep — every 10 s in last minute. */
export function tenSecBeep() {
  beep(660, 0.15, 0.3);
}

/** Quick beep — last 10 seconds countdown. */
export function secondBeep() {
  beep(1100, 0.08, 0.25);
}

/** Long low tone — gun (start)! */
export function gunBeep() {
  beep(440, 1.2, 0.5);
}
