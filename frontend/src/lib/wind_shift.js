/**
 * Wind shift detection — compares current TWD to rolling average.
 *
 * A "lift" means TWD shifted so you can point higher on current tack.
 * A "header" means TWD shifted so you must bear away.
 *
 * Convention (starboard tack, TWA > 0):
 *   delta > 0 (wind veered right) → LIFT
 *   delta < 0 (wind backed left)  → HEADER
 * Port tack is reversed.
 *
 * @param {Array}  history     - samples from history store [{t, twd, ...}]
 * @param {number} currentTwd  - current TWD degrees (0-360)
 * @param {number} currentTwa  - current TWA degrees (signed)
 * @param {number} windowSec   - averaging window seconds (default 300 = 5 min)
 * @returns {{ shift: number, type: "lift"|"header"|null }}
 */
export function computeWindShift(history, currentTwd, currentTwa, windowSec = 300) {
  if (currentTwd == null || currentTwa == null || !history || history.length < 10) {
    return { shift: 0, type: null };
  }

  const now = history[history.length - 1]?.t ?? Date.now();
  const cutoff = now - windowSec * 1000;

  // Collect TWD samples in the window
  const twdSamples = [];
  for (const s of history) {
    if (s.t >= cutoff && s.twd != null) {
      twdSamples.push(s.twd);
    }
  }

  if (twdSamples.length < 5) {
    return { shift: 0, type: null };
  }

  // Circular mean for angles (TWD is 0-360)
  let sinSum = 0, cosSum = 0;
  for (const d of twdSamples) {
    const rad = (d * Math.PI) / 180;
    sinSum += Math.sin(rad);
    cosSum += Math.cos(rad);
  }
  let avgTwd = (Math.atan2(sinSum / twdSamples.length, cosSum / twdSamples.length) * 180) / Math.PI;
  if (avgTwd < 0) avgTwd += 360;

  // Signed angular difference: current - average (shortest arc)
  let delta = currentTwd - avgTwd;
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;

  // Determine lift/header based on tack
  const THRESHOLD = 1.0; // ignore shifts below 1 degree
  if (Math.abs(delta) < THRESHOLD) {
    return { shift: Math.round(delta), type: null };
  }

  const isStbd = currentTwa > 0;
  const type = isStbd
    ? (delta > 0 ? "lift" : "header")
    : (delta < 0 ? "lift" : "header");

  return { shift: Math.round(delta), type };
}
