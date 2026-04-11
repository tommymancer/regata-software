/**
 * WebSocket-backed boat state store.
 *
 * Connects to the backend, auto-reconnects on disconnect,
 * and exposes a readable Svelte store with the latest BoatState.
 */
import { writable, derived } from "svelte/store";

/** Raw boat state from WebSocket JSON */
export const boatState = writable(null);

/** Connection status: "connected" | "connecting" | "disconnected" */
export const connectionStatus = writable("disconnected");

// Derived convenience stores for common fields
export const bsp = derived(boatState, ($s) => $s?.bsp_kt ?? null);
export const twa = derived(boatState, ($s) => $s?.twa_deg ?? null);
export const tws = derived(boatState, ($s) => $s?.tws_kt ?? null);
export const twd = derived(boatState, ($s) => $s?.twd_deg ?? null);
export const awa = derived(boatState, ($s) => $s?.awa_deg ?? null);
export const aws = derived(boatState, ($s) => $s?.aws_kt ?? null);
export const hdg = derived(boatState, ($s) => $s?.heading_mag ?? null);
export const sog = derived(boatState, ($s) => $s?.sog_kt ?? null);
export const cog = derived(boatState, ($s) => $s?.cog_deg ?? null);
export const vmg = derived(boatState, ($s) => $s?.vmg_kt ?? null);
export const depth = derived(boatState, ($s) => $s?.depth_m ?? null);
export const heel = derived(boatState, ($s) => $s?.heel_deg ?? null);
export const gpsFix = derived(boatState, ($s) => $s?.gps_fix ?? false);
export const lat = derived(boatState, ($s) => $s?.lat ?? null);
export const lon = derived(boatState, ($s) => $s?.lon ?? null);
export const waterTemp = derived(boatState, ($s) => $s?.water_temp_c ?? null);
export const perfPct = derived(boatState, ($s) => $s?.perf_pct ?? null);
export const targetTwa = derived(boatState, ($s) => $s?.target_twa_deg ?? null);
export const targetBsp = derived(boatState, ($s) => $s?.target_bsp_kt ?? null);
export const targetVmg = derived(boatState, ($s) => $s?.target_vmg_kt ?? null);
export const targetVmc = derived(boatState, ($s) => $s?.target_vmc_kt ?? null);
export const vmgPerfPct = derived(boatState, ($s) => $s?.vmg_perf_pct ?? null);

// Race timer
export const raceState = derived(boatState, ($s) => $s?.race_state ?? "idle");
export const raceTimerSecs = derived(boatState, ($s) => $s?.race_timer_secs ?? null);

// Navigation to mark
export const btw = derived(boatState, ($s) => $s?.btw_deg ?? null);
export const dtw = derived(boatState, ($s) => $s?.dtw_nm ?? null);
export const nextMark = derived(boatState, ($s) => $s?.next_mark_name ?? null);

// Laylines
export const laylinePort = derived(boatState, ($s) => $s?.layline_port_deg ?? null);
export const laylineStbd = derived(boatState, ($s) => $s?.layline_stbd_deg ?? null);
export const distToPortLayline = derived(boatState, ($s) => $s?.dist_to_port_layline_nm ?? null);
export const distToStbdLayline = derived(boatState, ($s) => $s?.dist_to_stbd_layline_nm ?? null);

// Sail config
export const sailConfig = derived(boatState, ($s) => $s?.active_sail_config ?? "main_1__genoa");

// VMC / course geometry
export const vmc = derived(boatState, ($s) => $s?.vmc_kt ?? null);
export const targetTwaVmc = derived(boatState, ($s) => $s?.target_twa_vmc_deg ?? null);
export const courseOffset = derived(boatState, ($s) => $s?.course_offset_deg ?? null);
export const lineBias = derived(boatState, ($s) => $s?.line_bias_deg ?? null);
export const distToLine = derived(boatState, ($s) => $s?.dist_to_line_nm ?? null);
export const legBearing = derived(boatState, ($s) => $s?.leg_bearing_deg ?? null);

let ws = null;
let reconnectTimer = null;
const RECONNECT_DELAY = 2000;

function getWsUrl() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws`;
}

export function connect() {
  if (ws && ws.readyState <= 1) return; // already open or connecting

  connectionStatus.set("connecting");
  ws = new WebSocket(getWsUrl());

  ws.onopen = () => {
    connectionStatus.set("connected");
    clearTimeout(reconnectTimer);
  };

  ws.onmessage = (event) => {
    try {
      boatState.set(JSON.parse(event.data));
    } catch (e) {
      // ignore malformed frames
    }
  };

  ws.onclose = () => {
    connectionStatus.set("disconnected");
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws.close();
  };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
}

export function disconnect() {
  clearTimeout(reconnectTimer);
  if (ws) {
    ws.onclose = null;
    ws.close();
    ws = null;
  }
  connectionStatus.set("disconnected");
}
