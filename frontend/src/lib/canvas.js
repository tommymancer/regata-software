/**
 * Resize a canvas element to fit its parent, accounting for device pixel ratio.
 * Returns { size, dpr } where size is the CSS pixel dimension.
 */
export function resizeCanvas(canvas) {
  const rect = canvas.parentElement.getBoundingClientRect();
  const size = Math.min(rect.width, rect.height);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + "px";
  canvas.style.height = size + "px";
  const ctx = canvas.getContext("2d");
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { size, dpr };
}
