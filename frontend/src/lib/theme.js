/**
 * Theme color utilities for canvas components.
 *
 * Canvas 2D context cannot use CSS custom properties directly.
 * These helpers read computed CSS variable values from a DOM element
 * so canvas draw functions can use the current theme's colors.
 */

/**
 * Read current theme colors from computed CSS custom properties.
 * Pass any element within the themed `.app[data-theme]` subtree.
 */
export function getThemeColors(element) {
  const style = getComputedStyle(element);
  const get = (name) => style.getPropertyValue(name).trim();
  return {
    bg:       get('--bg'),
    card:     get('--card'),
    cardGlow: get('--card-glow') || get('--card'),
    border:   get('--border'),
    text:     get('--text'),
    textDim:  get('--text-dim'),
    accent:   get('--accent'),
    green:    get('--green'),
    orange:   get('--orange'),
    red:      get('--red'),
    port:     get('--port'),
    stbd:     get('--stbd'),
  };
}

/**
 * Return a CSS color string with alpha transparency.
 * Converts hex (#rrggbb) or rgb() to rgba().
 */
export function withAlpha(color, alpha) {
  if (color.startsWith('#')) {
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }
  const m = color.match(/\d+/g);
  if (m && m.length >= 3) {
    return `rgba(${m[0]},${m[1]},${m[2]},${alpha})`;
  }
  return color;
}
