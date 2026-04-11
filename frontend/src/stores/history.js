/**
 * History store — ring buffer of boat state samples for strip charts.
 *
 * Subscribes to the WebSocket-backed boatState store, downsamples to
 * ~1 Hz, and accumulates up to 10 minutes of data.
 */
import { writable } from "svelte/store";
import { boatState } from "./boat.js";

const MAX_SAMPLES = 600; // 10 minutes at 1 Hz
const DOWNSAMPLE = 10;   // keep 1 out of every 10 WebSocket frames (~10 Hz → 1 Hz)

let samples = [];
let frameCount = 0;
let unsub = null;

/** Readable store: array of historical samples. */
export const history = writable([]);

/** Start accumulating history from the boatState stream. */
export function startHistory() {
  if (unsub) return; // already running
  unsub = boatState.subscribe((s) => {
    if (!s) return;
    frameCount++;
    if (frameCount % DOWNSAMPLE !== 0) return;

    samples.push({
      t: Date.now(),
      bsp: s.bsp_kt,
      tws: s.tws_kt,
      twa: s.twa_deg,
      vmg: s.vmg_kt,
      sog: s.sog_kt,
      heel: s.heel_deg,
      perf: s.perf_pct,
      vmg_perf: s.vmg_perf_pct,
      target_bsp: s.target_bsp_kt,
      twd: s.twd_deg,
      lat: s.lat,
      lon: s.lon,
      hdg: s.heading_mag,
    });

    if (samples.length > MAX_SAMPLES) {
      samples = samples.slice(-MAX_SAMPLES);
    }

    history.set(samples);
  });
}

/** Stop accumulating and clear history. */
export function stopHistory() {
  if (unsub) {
    unsub();
    unsub = null;
  }
  samples = [];
  frameCount = 0;
  history.set([]);
}
