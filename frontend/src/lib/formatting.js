/**
 * Formatting helpers for instrument display values.
 */

/** Format a number to fixed decimals, or "---" if null. */
export function fmt(value, decimals = 1) {
  if (value == null || isNaN(value)) return "---";
  return value.toFixed(decimals);
}

/** Format an angle (0-360 or signed). */
export function fmtAngle(value, decimals = 0) {
  if (value == null || isNaN(value)) return "---";
  return value.toFixed(decimals) + "°";
}

/** Format signed angle with +/- sign (positive = starboard, negative = port). */
export function fmtSignedAngle(value, decimals = 0) {
  if (value == null || isNaN(value)) return "---";
  const abs = Math.abs(value).toFixed(decimals);
  if (value > 0) return "+" + abs + "°";
  if (value < 0) return "-" + abs + "°";
  return abs + "°";
}

/** Format speed in knots. */
export function fmtSpeed(value, decimals = 1) {
  if (value == null || isNaN(value)) return "---";
  return value.toFixed(decimals);
}

/** Format percentage. */
export function fmtPct(value, decimals = 0) {
  if (value == null || isNaN(value)) return "---";
  return value.toFixed(decimals) + "%";
}

/** Port/stbd color: port=red, stbd=green, neutral=white. */
export function sideColor(value) {
  if (value == null || value === 0) return "var(--text)";
  return value < 0 ? "var(--port)" : "var(--stbd)";
}

/**
 * Map trim level string to theme-aware CSS color.
 */
export function levelColor(val) {
  if (val === "light")  return "var(--green)";
  if (val === "medium") return "var(--orange)";
  if (val === "heavy")  return "var(--red)";
  return "var(--text-dim)";
}
