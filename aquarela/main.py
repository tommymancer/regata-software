"""Aquarela Regatta Software — FastAPI entry point.

Pipeline loop:
  Source (simulator or CAN) → PGN decode → calibrate → true wind →
  derived → damp → targets → race timer → navigation → CSV log → WebSocket

Run with: uvicorn aquarela.main:app --host 0.0.0.0 --port 8000
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import AquarelaConfig
from .logging.csv_logger import CsvLogger
from .nmea.pgn_decoder import decode_pgn
from .nmea.source_base import NmeaSource
from .nmea.source_interactive import InteractiveSource
from .nmea.source_simulator import SimulatorSource
from .performance.polar import PolarTable
from .performance.targets import compute_targets
from .pipeline.calibration import apply_calibration
from .pipeline.damping import DampingFilters, ScalarBuffer
from .pipeline.derived import compute_derived
from .pipeline.state import BoatState
from .pipeline.true_wind import compute_true_wind
from .pipeline.upwash_learning import UpwashLearner
from .pipeline.upwash_table import UpwashTableSet
from .pipeline.wind_correction import apply_wind_correction
from .nmea.can_writer import CanWriter
from .race.marks import Mark, MarkStore
from .race.navigation import compute_navigation
from .race.timer import RaceTimer
from .performance.auto_calibrator import AutoCalibrator
from .performance.laylines import compute_layline_distances, compute_laylines
from .performance.polar_learner import PolarLearner
from .performance.polar_manager import SAIL_CONFIGS, PolarManager
from .performance.vmc import compute_vmc_targets
from .race.course_generator import CourseSetup, generate_course
from .race.course_setup import CourseSetupManager
from .race.sight_triangulator import SightTriangulator
from .race.start_line import StartLine
from .training.maneuvers import ManeuverDetector
from .training.sessions import SessionManager
from .training.trim_book import TrimBook

# API routers
from .api.race import router as race_router
from .api.marks import router as marks_router
from .api.line import router as line_router
from .api.course_setup import router as course_setup_router
from .api.sim import router as sim_router
from .api.trim import router as trim_router
from .api.sessions import router as sessions_router
from .api.maneuvers import router as maneuvers_router
from .api.polar import router as polar_router
from .api.sails import router as sails_router


logger = logging.getLogger("aquarela")

# ── Global state ────────────────────────────────────────────────────────
config: AquarelaConfig = AquarelaConfig.load()
csv_logger: CsvLogger = CsvLogger(
    csv_rate_hz=config.csv_rate_hz,
    pipeline_hz=config.sample_rate_hz,
)
damping: DampingFilters = DampingFilters(
    windows=config.damping,
    hz=config.sample_rate_hz,
)
ws_clients: Set[WebSocket] = set()
current_state: BoatState = BoatState.new()

# Wind correction: upwash tables + heel damper + learning
upwash_tables: UpwashTableSet = UpwashTableSet.load("data/upwash_tables.json")
heel_damper: ScalarBuffer = ScalarBuffer(
    max_len=max(1, int(4.0 * config.sample_rate_hz))  # 4-second window
)
upwash_learner: UpwashLearner = UpwashLearner(hz=config.sample_rate_hz)
_pipeline_task: asyncio.Task | None = None

# Race timer + mark navigation
race_timer: RaceTimer = RaceTimer()
mark_store: MarkStore = MarkStore()

# Start line + VMC
start_line: StartLine = StartLine()

# Course generation + sight triangulation
course_setup: CourseSetup | None = None
sight_triangulator: SightTriangulator = SightTriangulator()

# Pre-race course setup (per-mark triangulators)
course_setup_mgr: CourseSetupManager = CourseSetupManager()

# Training features
maneuver_detector: ManeuverDetector = ManeuverDetector(hz=config.sample_rate_hz)
session_manager: SessionManager = SessionManager(hz=config.sample_rate_hz)
trim_book: TrimBook = TrimBook()

# Auto-calibration (compass offset + speed factor)
auto_calibrator: AutoCalibrator = AutoCalibrator()

# Load polar table (optional — degrades gracefully if missing)
try:
    _base_polar: PolarTable | None = PolarTable.load()
    logger.info("Polar table loaded (%d TWS columns)", len(_base_polar.tws_values))
except FileNotFoundError:
    _base_polar = None
    logger.warning("No polar file found — performance targets disabled")

# Polar manager (6 sail types, all starting from the same base)
polar_manager: PolarManager = PolarManager(base_polar=_base_polar)
polar_manager.active_sail_type = config.sail_config_key()

# Convenience alias — pipeline code uses this
polar: PolarTable | None = polar_manager.active_polar

# Polar learning: one PolarLearner per sail type
polar_learners: dict[str, PolarLearner] = {
    key: PolarLearner(base_polar=_base_polar, hz=config.sample_rate_hz, sail_type=key)
    for key in SAIL_CONFIGS
}

# Convenience alias for the active learner (used by API)
polar_learner: PolarLearner = polar_learners[config.sail_config_key()]

# CAN writer — sends corrected true wind as PGN 130306
can_writer = CanWriter(
    enabled=config.can_writer_enabled,
    dry_run=config.can_writer_dry_run,
)

active_source: NmeaSource | None = None  # global reference for interactive REST API


def _create_source() -> NmeaSource:
    """Instantiate the configured data source."""
    global active_source
    if config.source == "simulator":
        active_source = SimulatorSource(hz=config.sample_rate_hz)
    elif config.source == "interactive":
        active_source = InteractiveSource(
            hz=config.sample_rate_hz,
            twd=config.initial_twd,
            tws=config.initial_tws,
        )
    elif config.source.startswith("can") or config.source.startswith("vcan"):
        # Lazy import — keeps Mac dev working without SocketCAN
        from aquarela.nmea.source_can import CanSource
        interface = config.source if config.source != "can" else "can0"
        active_source = CanSource(interface=interface, ignore_addresses={100})
    else:
        raise ValueError(f"Unknown source: {config.source}")
    return active_source


# ── WebSocket broadcast ─────────────────────────────────────────────────

def _state_to_json(state: BoatState) -> str:
    """Serialize BoatState to JSON for WebSocket clients."""
    d = asdict(state)
    d["timestamp"] = state.timestamp.isoformat()
    return json.dumps(d, default=str)


async def _broadcast(message: str) -> None:
    """Send message to all connected WebSocket clients."""
    if not ws_clients:
        return
    results = await asyncio.gather(
        *(ws.send_text(message) for ws in list(ws_clients)),
        return_exceptions=True,
    )
    for ws, result in zip(list(ws_clients), results):
        if isinstance(result, Exception):
            ws_clients.discard(ws)


# ── Pipeline loop ───────────────────────────────────────────────────────

async def _pipeline_loop(source: NmeaSource) -> None:
    """Main processing loop: read PGN frames, process, broadcast."""
    global current_state

    state = BoatState.new()
    ws_tick = 0
    ws_decimation = max(1, config.sample_rate_hz // config.websocket_rate_hz)
    frames_in_step = 0
    _disk_ok = True
    _disk_check_counter = 0

    await source.start()
    _clock_synced = False
    _clock_ready = False
    _first_frame_time = time.monotonic()
    logger.info("Pipeline loop running (ws_decimation=%d)", ws_decimation)

    try:
        # Sensor age tracking: PGN → age field name
        _pgn_age_map = {
            127250: "heading_age_ms",
            130306: "wind_age_ms",
            128259: "bsp_age_ms",
            128267: "depth_age_ms",
        }
        _last_seen: dict[int, float] = {}

        async for pgn, data in source.stream():
            try:
                decoded = decode_pgn(pgn, data)
                session_manager.notify_nmea_frame()

                # Sync system clock from GPS time before starting the CSV session.
                # This ensures session filenames have the correct date even without
                # an RTC or NTP (e.g., on the boat with no internet).
                if not _clock_synced and "gps_epoch_secs" in decoded:
                    gps_epoch = decoded["gps_epoch_secs"]
                    sys_epoch = int(time.time())
                    drift = abs(gps_epoch - sys_epoch)
                    if drift > 30:
                        import subprocess
                        try:
                            await asyncio.to_thread(
                                subprocess.run,
                                ["sudo", "date", "-u", "-s", f"@{gps_epoch}"],
                                capture_output=True, timeout=5,
                            )
                            logger.info(
                                "System clock synced from GPS (was off by %d seconds)",
                                drift,
                            )
                        except Exception:
                            logger.warning("Failed to set system clock from GPS")
                    else:
                        logger.info("System clock OK (drift %ds from GPS)", drift)
                    _clock_synced = True

                # Wait for clock sync (or 10s timeout) before allowing sessions
                if not _clock_ready:
                    if _clock_synced or (time.monotonic() - _first_frame_time > 10):
                        if not _clock_synced:
                            logger.warning(
                                "No GPS time after 10s — using current clock"
                            )
                        _clock_ready = True

                for key, value in decoded.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
                frames_in_step += 1

                # Track when each sensor PGN was last received
                if pgn in _pgn_age_map:
                    _last_seen[pgn] = time.monotonic()

                if frames_in_step >= source.pgns_per_step:
                    frames_in_step = 0

                    # Full time step collected — run pipeline
                    state.timestamp = datetime.now(timezone.utc)

                    # Update sensor age fields
                    _now = time.monotonic()
                    for _pgn, _field in _pgn_age_map.items():
                        if _pgn in _last_seen:
                            setattr(state, _field, int((_now - _last_seen[_pgn]) * 1000))
                        else:
                            setattr(state, _field, 9999)
                    apply_calibration(state, config)

                    # Smooth heel for wind correction (standalone damper)
                    _heel_smoothed = None
                    if state.heel_deg is not None:
                        _heel_smoothed = heel_damper.push(state.heel_deg)

                    # Wind correction: heel + upwash
                    _sail_key = config.sail_config_key()
                    state.active_sail_config = _sail_key
                    _upwash_table = upwash_tables.get_table(_sail_key)
                    apply_wind_correction(state, _upwash_table, _heel_smoothed)

                    compute_true_wind(state)

                    # Publish all calibrated data onto CAN bus
                    can_writer.update(
                        twa_water=state.twa_deg,
                        tws_water=state.tws_kt,
                        heading_mag=state.heading_mag,
                        bsp_kt=state.bsp_kt,
                        depth_m=state.depth_m,
                    )

                    compute_derived(state)
                    damping.apply(state)

                    # Resolve active polar for this tick
                    _polar = polar_manager.active_polar

                    if _polar is not None:
                        compute_targets(state, _polar)

                    # Start line geometry + VMC
                    if start_line.state.is_mark_set():
                        state.leg_bearing_deg = start_line.leg_bearing()
                        if state.twd_deg is not None:
                            state.course_offset_deg = start_line.course_offset_deg(
                                state.twd_deg
                            )
                            if state.line_bias_deg is None and start_line.state.is_line_set():
                                pass  # computed below
                        if (
                            _polar is not None
                            and state.course_offset_deg is not None
                        ):
                            compute_vmc_targets(
                                state, _polar, state.course_offset_deg
                            )
                    if start_line.state.is_line_set():
                        if state.twd_deg is not None:
                            state.line_bias_deg = start_line.line_bias_deg(
                                state.twd_deg
                            )
                        if state.lat is not None and state.lon is not None:
                            state.dist_to_line_nm = start_line.dist_to_line_nm(
                                state.lat, state.lon
                            )

                    # Race timer update
                    race_timer.update(state)

                    # Navigation to active mark
                    mark = mark_store.active_mark
                    if mark is not None:
                        compute_navigation(state, mark.lat, mark.lon, mark.name)

                    # Laylines (requires polar targets + optional mark)
                    if _polar is not None:
                        port_ll, stbd_ll = compute_laylines(state, _polar)
                        state.layline_port_deg = port_ll
                        state.layline_stbd_deg = stbd_ll
                        if (
                            mark is not None
                            and port_ll is not None
                            and stbd_ll is not None
                        ):
                            dp, ds = compute_layline_distances(
                                state, mark.lat, mark.lon, port_ll, stbd_ll
                            )
                            state.dist_to_port_layline_nm = dp
                            state.dist_to_stbd_layline_nm = ds

                    # Training: maneuver detection + session auto-start/stop
                    maneuver_result = maneuver_detector.update(
                        heading=state.heading_mag,
                        twa=state.twa_deg,
                        bsp=state.bsp_kt,
                        sog=state.sog_kt,
                        cog=state.cog_deg,
                        brg_to_mark=state.btw_deg,
                        lat=state.lat,
                        lon=state.lon,
                        wall_time=state.timestamp.strftime("%Y-%m-%dT%H:%M:%S.") +
                            f"{state.timestamp.microsecond // 1000:03d}Z",
                    )
                    if maneuver_result and session_manager.active_session:
                        from aquarela.training.maneuvers import persist_maneuver
                        persist_maneuver(
                            session_manager._get_conn(),
                            session_manager.active_session.id,
                            maneuver_result,
                        )
                    if _clock_ready and config.source not in (
                        "simulator", "interactive",
                    ):
                        session_event = session_manager.update(
                            state.bsp_kt, state.sog_kt
                        )
                    else:
                        session_event = None

                    # Check disk space once per minute (~600 ticks at 10 Hz)
                    _disk_check_counter += 1
                    if _disk_check_counter >= config.sample_rate_hz * 60:
                        _disk_check_counter = 0
                        _disk_ok = _disk_free_mb() > DISK_MIN_FREE_MB

                    # Start CSV + log when sailing starts, stop when it stops
                    if session_event == "started":
                        logger.info("Sailing detected — starting CSV session")
                        csv_logger.start_session(
                            session_manager.active_session.session_type
                        )
                        if csv_logger.file_path:
                            session_manager.set_csv_file(
                                str(csv_logger.file_path)
                            )
                    elif session_event == "stopped":
                        logger.info("Sailing stopped — closing CSV session")
                        csv_logger.stop_session()
                        # Auto polar rebuild + activate at session end
                        if config.source not in ("simulator", "interactive"):
                            _key = config.sail_config_key()
                            _learner = polar_learners[_key]
                            _learner.flush()
                            try:
                                _learned = _learner.rebuild()
                                if _learned is not None:
                                    polar_manager.set_polar(_key, _learned)
                                    polar = polar_manager.active_polar
                                    logger.info(
                                        "Auto-activated learned polar for %s",
                                        _key,
                                    )
                            except Exception:
                                logger.exception(
                                    "Auto-rebuild failed for %s, keeping current polar",
                                    _key,
                                )

                    # Upwash learning check
                    if config.upwash_learning_enabled and state.twd_deg is not None:
                        _learn_result = upwash_learner.update(
                            twd=state.twd_deg,
                            awa_corrected=state.awa_corrected_deg or state.awa_deg or 0.0,
                            heel=state.heel_deg or 0.0,
                            bsp=state.bsp_kt or 0.0,
                            sail_config=state.active_sail_config or config.sail_config_key(),
                        )
                        state.upwash_learning_status = upwash_learner.state
                        if _learn_result is not None:
                            _residual, _mean_awa, _mean_heel, _learn_config = _learn_result
                            _learn_table = upwash_tables.get_table(_learn_config)
                            if _learn_table is not None:
                                _learn_table.update_nearest(
                                    _mean_awa, _mean_heel, _residual,
                                    config.upwash_learning_rate,
                                )
                                upwash_tables.save("data/upwash_tables.json")
                                logger.info("Upwash table updated and saved")

                    # Auto-calibration (if a run is active)
                    auto_calibrator.update(state)

                    # Polar learning: only while actively sailing
                    # Simulation guard: never contaminate polars with simulated data
                    _is_sailing = session_manager.active_session is not None
                    if _is_sailing and _disk_ok and config.source not in (
                        "simulator",
                        "interactive",
                    ):
                        polar_learners[config.sail_config_key()].update(
                            state,
                            in_maneuver=maneuver_detector.in_maneuver,
                            session_id=session_manager.active_session.id,
                        )

                    # CSV: only log while sailing and disk OK
                    if _is_sailing and _disk_ok:
                        csv_logger.log(state)

                    # Broadcast to WebSocket clients
                    ws_tick += 1
                    if ws_tick >= ws_decimation:
                        ws_tick = 0
                        if ws_clients:
                            await _broadcast(_state_to_json(state))

                    current_state = state

            except Exception:
                logger.exception("Pipeline step error (PGN %d)", pgn)
    except asyncio.CancelledError:
        logger.info("Pipeline cancelled")
    except Exception:
        logger.exception("Pipeline loop crashed")
    finally:
        csv_logger.stop_session()
        for _st, _pl in polar_learners.items():
            _pl.flush()
        if config.source not in ("simulator", "interactive"):
            _key = config.sail_config_key()
            _active_learner = polar_learners[_key]
            try:
                _learned = _active_learner.rebuild()
                if _learned is not None:
                    polar_manager.set_polar(_key, _learned)
                    polar = polar_manager.active_polar
                    logger.info(
                        "Auto-activated learned polar for %s (%d bins ready)",
                        _key,
                        _active_learner.get_stats().get("bins_ready", 0),
                    )
            except Exception:
                logger.exception("Final rebuild failed for %s", _key)
        try:
            await source.stop()
        except Exception:
            logger.debug("source.stop() error (ignored)")
        logger.info("Pipeline loop ended")


# ── WebSocket heartbeat (keeps frontend updated even when no PGN data) ──

_heartbeat_task: asyncio.Task | None = None

async def _heartbeat_loop() -> None:
    """Broadcast current_state once per second so the frontend stays fresh."""
    while True:
        await asyncio.sleep(1.0)
        if ws_clients:
            await _broadcast(_state_to_json(current_state))


# ── App lifecycle ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start pipeline on boot, stop on shutdown."""
    global _pipeline_task, _heartbeat_task, course_setup
    source = _create_source()

    # Auto-generate race course in interactive mode
    if config.source == "interactive" and isinstance(source, InteractiveSource):
        course_setup = generate_course(
            twd=config.initial_twd,
            start_lat=source.lat,
            start_lon=source.lon,
        )
        start_line.log_rc(course_setup.rc_lat, course_setup.rc_lon)
        start_line.log_pin(course_setup.pin_lat, course_setup.pin_lon)
        mark_store.add_mark(Mark("RC Boat", course_setup.rc_lat, course_setup.rc_lon, "start"))
        mark_store.add_mark(Mark("Pin End", course_setup.pin_lat, course_setup.pin_lon, "start"))
        mark_store.add_mark(Mark("Windward", course_setup.windward_lat, course_setup.windward_lon, "windward"))
        mark_store.set_course_sequence(["Windward", "Leeward", "Windward"])
        mark_store.next_mark()  # auto-activate first mark so BTW/DTW work

        # Set leg bearing for VMC computation
        mid_lat = (course_setup.rc_lat + course_setup.pin_lat) / 2
        mid_lon = (course_setup.rc_lon + course_setup.pin_lon) / 2
        from .race.navigation import bearing_to
        brg = bearing_to(mid_lat, mid_lon, course_setup.windward_lat, course_setup.windward_lon)
        start_line.sight_mark(brg)

        logger.info(
            "Course generated: RC(%.5f,%.5f) Pin(%.5f,%.5f) WM(%.5f,%.5f) TWD=%.0f",
            course_setup.rc_lat, course_setup.rc_lon,
            course_setup.pin_lat, course_setup.pin_lon,
            course_setup.windward_lat, course_setup.windward_lon,
            course_setup.twd,
        )

    # Restore previously applied course (CAN mode — no auto-generated course)
    if config.source not in ("interactive", "simulator"):
        from .api.course_setup import restore_course
        restore_course()

    can_writer.start()
    _pipeline_task = asyncio.create_task(_pipeline_loop(source))
    _heartbeat_task = asyncio.create_task(_heartbeat_loop())
    _cleanup_task = asyncio.create_task(_periodic_cleanup())
    logger.info("Pipeline started (source=%s, hz=%d)", config.source, config.sample_rate_hz)
    yield
    _cleanup_task.cancel()
    _heartbeat_task.cancel()
    _pipeline_task.cancel()
    for task in (_pipeline_task, _heartbeat_task, _cleanup_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
    can_writer.stop()
    logger.info("Pipeline stopped")


app = FastAPI(title="Aquarela", lifespan=lifespan)

# ── Register API routers ───────────────────────────────────────────────
app.include_router(race_router)
app.include_router(marks_router)
app.include_router(line_router)
app.include_router(course_setup_router)
app.include_router(sim_router)
app.include_router(trim_router)
app.include_router(sessions_router)
app.include_router(maneuvers_router)
app.include_router(polar_router)
app.include_router(sails_router)

# ── WebSocket endpoint ──────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    logger.info("WebSocket client connected (%d total)", len(ws_clients))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(ws_clients))


# ── Core REST endpoints (kept in main — too coupled to globals) ─────────

@app.get("/api/state")
async def get_state():
    """Current boat state as JSON (polling fallback)."""
    d = current_state.__dict__.copy()
    d["timestamp"] = current_state.timestamp.isoformat()
    return d


@app.get("/api/config")
async def get_config():
    """Current configuration."""
    return asdict(config)


@app.post("/api/calibration")
async def set_calibration(payload: dict):
    """Update calibration offsets. Body: partial dict of calibration fields.

    Accepted keys: compass_offset, speed_factor, awa_offset, depth_offset,
    tws_downwind_factor, magnetic_variation, upwash_learning_rate,
    upwash_learning_enabled, can_writer_enabled, can_writer_dry_run.
    """
    allowed = {
        "compass_offset", "speed_factor", "awa_offset", "depth_offset",
        "tws_downwind_factor", "magnetic_variation",
    }
    changed = {}
    for key, val in payload.items():
        if key in allowed:
            try:
                setattr(config, key, float(val))
                changed[key] = float(val)
            except (ValueError, TypeError):
                pass

    # Upwash / CAN writer settings
    if "upwash_learning_rate" in payload:
        config.upwash_learning_rate = float(payload["upwash_learning_rate"])
        changed["upwash_learning_rate"] = config.upwash_learning_rate
    if "upwash_learning_enabled" in payload:
        config.upwash_learning_enabled = bool(payload["upwash_learning_enabled"])
        changed["upwash_learning_enabled"] = config.upwash_learning_enabled
    if "can_writer_enabled" in payload:
        config.can_writer_enabled = bool(payload["can_writer_enabled"])
        changed["can_writer_enabled"] = config.can_writer_enabled
        can_writer._enabled = config.can_writer_enabled
        if config.can_writer_enabled and not can_writer._address_claimed:
            can_writer.start()
    if "can_writer_dry_run" in payload:
        config.can_writer_dry_run = bool(payload["can_writer_dry_run"])
        changed["can_writer_dry_run"] = config.can_writer_dry_run
        can_writer._dry_run = config.can_writer_dry_run

    if changed:
        now_iso = datetime.now(timezone.utc).isoformat()
        _cal_key_map = {
            "compass_offset": "compass", "speed_factor": "speed",
            "awa_offset": "awa", "depth_offset": "depth",
            "tws_downwind_factor": "tws_factor",
            "magnetic_variation": "mag_var",
        }
        for key in changed:
            if key in _cal_key_map:
                config.cal_timestamps[_cal_key_map[key]] = now_iso
        config.save()
        logger.info("Calibration updated: %s", changed)
    return {k: getattr(config, k) for k in allowed | {
        "upwash_learning_rate", "upwash_learning_enabled",
        "can_writer_enabled", "can_writer_dry_run",
    }}


@app.post("/api/calibration/auto")
async def start_auto_calibration(payload: dict):
    """Start auto-calibration. Body: {"mode": "compass"} or {"mode": "speed"}.

    Collects 30 seconds of data while sailing straight, then computes
    the correction. Poll GET /api/calibration/auto for status/result.
    """
    mode = payload.get("mode", "").strip()
    if mode not in ("compass", "speed", "awa"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="mode must be 'compass', 'speed', or 'awa'")
    auto_calibrator.start(mode)
    logger.info("Auto-calibration started: %s", mode)
    return {"status": "collecting", "mode": mode}


@app.get("/api/calibration/auto")
async def auto_calibration_status():
    """Check auto-calibration progress and result."""
    if auto_calibrator.is_collecting:
        resp = {
            "status": "collecting",
            "mode": auto_calibrator.mode,
            "progress": round(auto_calibrator.progress, 2),
        }
        awa_st = auto_calibrator.awa_status
        if awa_st is not None:
            resp["awa"] = awa_st
        return resp
    r = auto_calibrator.result
    if r is None:
        return {"status": "idle"}
    resp = {
        "status": "done",
        "mode": r.mode,
        "value": r.value,
        "samples": r.samples,
        "std_dev": r.std_dev,
        "quality": r.quality,
    }
    if r.detail:
        resp["detail"] = r.detail
    return resp


@app.post("/api/calibration/auto/apply")
async def apply_auto_calibration():
    """Apply the last auto-calibration result to the config."""
    r = auto_calibrator.result
    if r is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No calibration result available")
    if r.quality == "poor":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Quality too poor to apply — try again in steadier conditions")
    if r.mode == "compass":
        config.compass_offset = r.value
    elif r.mode == "speed":
        config.speed_factor = r.value
    elif r.mode == "awa":
        config.awa_offset = r.value
    config.cal_timestamps[r.mode] = datetime.now(timezone.utc).isoformat()
    config.save()
    logger.info("Auto-calibration applied: %s = %s", r.mode, r.value)
    return {"applied": True, "mode": r.mode, "value": r.value}


@app.post("/api/calibration/auto/cancel")
async def cancel_auto_calibration():
    """Cancel an in-progress auto-calibration run."""
    auto_calibrator.cancel()
    return {"status": "cancelled"}


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "source": config.source,
        "logging": csv_logger.is_open,
        "clients": len(ws_clients),
        "race_state": race_timer.state,
    }


@app.get("/api/source")
async def get_source():
    """Current data source mode."""
    return {"source": config.source}


@app.post("/api/source")
async def set_source(payload: dict):
    """Switch data source and restart the pipeline.

    Body: {"source": "can0"} or {"source": "simulator"} or {"source": "interactive"}
    """
    global _pipeline_task, config, active_source, current_state
    new_source = payload.get("source", "").strip()
    valid = {"simulator", "interactive", "can0", "can1"}
    if new_source not in valid:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid source: {new_source}. Must be one of {valid}")

    # Stop current pipeline
    if _pipeline_task is not None:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except (asyncio.CancelledError, Exception):
            pass

    # Reset state so stale data doesn't linger
    current_state = BoatState.new()

    # Update config and persist
    config.source = new_source
    config.save()

    # Restart pipeline with new source
    source = _create_source()
    _pipeline_task = asyncio.create_task(_pipeline_loop(source))
    logger.info("Source switched to %s — pipeline restarted", new_source)

    return {"source": config.source}


@app.get("/api/laylines")
async def get_laylines():
    """Current layline bearings and distances."""
    return {
        "port_bearing": current_state.layline_port_deg,
        "stbd_bearing": current_state.layline_stbd_deg,
        "dist_to_port_nm": current_state.dist_to_port_layline_nm,
        "dist_to_stbd_nm": current_state.dist_to_stbd_layline_nm,
    }


# ── Disk management ───────────────────────────────────────────────────────

import shutil

_data_dir = Path("data")
_sessions_dir = _data_dir / "sessions"

# Minimum free disk space (MB) before we stop writing
DISK_MIN_FREE_MB = 100
# Keep CSV files for at most this many days (0 = keep forever)
CSV_RETENTION_DAYS = 90


def _disk_free_mb() -> float:
    """Free disk space in MB on the partition containing data/."""
    try:
        usage = shutil.disk_usage(str(_data_dir))
        return usage.free / (1024 * 1024)
    except OSError:
        return float("inf")


def _disk_usage_info() -> dict:
    """Disk usage summary for the API."""
    try:
        usage = shutil.disk_usage(str(_data_dir))
    except OSError:
        return {"error": "cannot read disk"}
    # CSV files size
    csv_bytes = sum(f.stat().st_size for f in _sessions_dir.glob("*.csv")) if _sessions_dir.exists() else 0
    # SQLite DB size
    from .logging.db import DB_PATH
    db_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "total_mb": round(usage.total / (1024 * 1024)),
        "used_mb": round(usage.used / (1024 * 1024)),
        "free_mb": round(usage.free / (1024 * 1024)),
        "free_pct": round(usage.free / usage.total * 100, 1),
        "csv_mb": round(csv_bytes / (1024 * 1024), 1),
        "db_mb": round(db_bytes / (1024 * 1024), 1),
        "min_free_mb": DISK_MIN_FREE_MB,
    }


def _cleanup_old_data() -> dict:
    """Remove old CSV files and vacuum the database. Returns summary."""
    removed_csv = 0
    if CSV_RETENTION_DAYS > 0 and _sessions_dir.exists():
        cutoff = time.time() - (CSV_RETENTION_DAYS * 86400)
        for f in _sessions_dir.glob("*.csv"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed_csv += 1
            except OSError:
                pass

    # Vacuum SQLite to reclaim space
    vacuumed = False
    try:
        from .logging.db import get_connection
        conn = get_connection()
        conn.execute("PRAGMA optimize")
        conn.execute("VACUUM")
        conn.close()
        vacuumed = True
    except Exception:
        pass

    return {"removed_csv_files": removed_csv, "vacuumed": vacuumed}


@app.get("/api/system/disk")
async def disk_info():
    """Disk usage and data sizes."""
    return _disk_usage_info()


@app.post("/api/system/cleanup")
async def manual_cleanup():
    """Manually trigger old data cleanup and VACUUM."""
    result = _cleanup_old_data()
    result["disk"] = _disk_usage_info()
    return result


# Background cleanup: runs once per hour
_cleanup_task: asyncio.Task | None = None


async def _periodic_cleanup() -> None:
    """Periodically clean old data and warn on low disk."""
    while True:
        await asyncio.sleep(3600)  # every hour
        free = _disk_free_mb()
        if free < DISK_MIN_FREE_MB * 2:
            logger.warning("Low disk space: %.0f MB free", free)
            _cleanup_old_data()
        if free < DISK_MIN_FREE_MB:
            logger.error(
                "CRITICAL: only %.0f MB free — disabling CSV and polar logging",
                free,
            )


# ── Session file downloads ────────────────────────────────────────────────


@app.get("/api/logs")
async def list_logs():
    """List available CSV session files, newest first."""
    if not _sessions_dir.exists():
        return []
    files = sorted(_sessions_dir.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        stat = f.stat()
        result.append({
            "name": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return result


@app.get("/api/logs/{filename}")
async def download_log(filename: str):
    """Download a session CSV file."""
    from fastapi import HTTPException
    # Sanitize: only allow simple filenames
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = _sessions_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path, media_type="text/csv", filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── OTA update from GitHub ──────────────────────────────────────────────

@app.get("/api/system/version")
async def system_version():
    """Return current git commit info."""
    import subprocess
    repo = Path(__file__).parent.parent
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo, timeout=5,
        ).decode().strip()
        msg = subprocess.check_output(
            ["git", "log", "-1", "--format=%s"], cwd=repo, timeout=5,
        ).decode().strip()
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"], cwd=repo, timeout=5,
        ).decode().strip()
        return {"sha": sha, "message": msg, "date": date}
    except Exception as e:
        return {"sha": "unknown", "message": str(e), "date": ""}


@app.post("/api/system/update")
async def system_update(request: Request):
    """Receive tarball from Android app, extract, rebuild, restart.

    The Android app downloads the tarball from GitHub and uploads it here,
    so the Pi doesn't need internet access.
    """
    import subprocess
    import tarfile
    import tempfile
    import shutil

    repo = Path(__file__).parent.parent
    steps = []

    try:
        # 1. Receive tarball
        body = await request.body()
        if len(body) < 100:
            return {"success": False, "steps": [{"step": "upload", "ok": False,
                    "output": f"Tarball troppo piccolo ({len(body)} bytes)"}]}
        steps.append({"step": "upload", "ok": True,
                       "output": f"Ricevuto {len(body) // 1024} KB"})

        # 2. Extract to temp dir
        with tempfile.TemporaryDirectory() as tmp:
            tar_path = Path(tmp) / "update.tar.gz"
            tar_path.write_bytes(body)

            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(tmp)

            # GitHub tarballs have a top-level dir like "user-repo-sha/"
            subdirs = [d for d in Path(tmp).iterdir() if d.is_dir()]
            if not subdirs:
                return {"success": False, "steps": steps + [
                    {"step": "extract", "ok": False, "output": "Nessuna cartella nell'archivio"}]}
            src_dir = subdirs[0]
            steps.append({"step": "extract", "ok": True,
                           "output": f"Estratto in {src_dir.name}"})

            # 3. Sync files (exclude data, config, sessions, .git)
            exclude = {".git", "data", "node_modules", "venv", "__pycache__",
                       "aquarela-android", ".claude"}
            for item in src_dir.iterdir():
                if item.name in exclude:
                    continue
                dest = repo / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            steps.append({"step": "sync", "ok": True, "output": "File aggiornati"})

        # 4. npm build — skip if pre-built static assets exist in tarball
        static_dir = repo / "aquarela" / "static" / "assets"
        if static_dir.exists() and any(static_dir.glob("*.js")):
            steps.append({"step": "frontend", "ok": True,
                           "output": "pre-built assets presenti"})
        else:
            frontend_dir = repo / "frontend"
            if (frontend_dir / "package.json").exists():
                result = subprocess.run(
                    ["npm", "run", "build"],
                    cwd=frontend_dir, capture_output=True, text=True, timeout=120,
                )
                steps.append({"step": "npm build", "ok": result.returncode == 0,
                               "output": result.stdout[-200:] if result.stdout else result.stderr[-200:]})
            else:
                steps.append({"step": "frontend", "ok": True, "output": "skipped"})

        # 5. Restart service
        subprocess.Popen(
            ["sudo", "systemctl", "restart", "aquarela"],
            cwd=repo,
        )
        steps.append({"step": "restart", "ok": True, "output": "scheduled"})

        return {"success": True, "steps": steps}
    except Exception as e:
        steps.append({"step": "error", "ok": False, "output": str(e)})
        return {"success": False, "steps": steps}


# ── Static files (Svelte dashboard, when built) ─────────────────────────
static_dir = Path(__file__).parent / "static"
_index_html = static_dir / "index.html"
_assets_dir = static_dir / "assets"

if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

if _index_html.exists():
    @app.get("/")
    async def index():
        return FileResponse(
            _index_html,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
