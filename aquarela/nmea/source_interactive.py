"""Interactive sailing simulator — steered from the keyboard via REST API.

Generates PGN frames like the hardware CAN source, but computes boat state
from user-controlled heading + configurable wind.  The full downstream
pipeline (calibration → true wind → derived → targets → broadcast) runs
identically to a live session.

Helm input:  POST /api/sim/helm  {"delta": ±5}  or  {"heading": 220}
Wind input:  POST /api/sim/wind  {"twd": 185, "tws": 12}
"""

import asyncio
import math
import random
import struct
from typing import AsyncIterator, Tuple

from .source_base import NmeaSource
from .source_simulator import _polar_speed, _true_to_apparent, _encode_state

# ── Constants ──────────────────────────────────────────────────────────
DEG_TO_RAD = math.pi / 180.0
KT_TO_MS = 1.0 / 1.94384


def _encode_attitude(heel_deg: float, trim_deg: float) -> Tuple[int, bytes]:
    """Encode PGN 127257 — Attitude (roll = heel, pitch = trim).

    Byte layout: [SID(1)] [yaw(2)] [pitch(2)] [roll(2)] [reserved(1)]
    All angles: radians × 10000, signed 16-bit.
    """
    yaw_raw = -32768  # not available
    pitch_raw = int((trim_deg * DEG_TO_RAD) / 0.0001)
    roll_raw = int((heel_deg * DEG_TO_RAD) / 0.0001)
    # Clamp to int16 range
    pitch_raw = max(-32767, min(32767, pitch_raw))
    roll_raw = max(-32767, min(32767, roll_raw))
    data = struct.pack("<BhhhB", 0xFF, yaw_raw, pitch_raw, roll_raw, 0xFF)
    return (127257, data)


def _compute_heel(twa_deg: float, tws_kt: float) -> float:
    """Simple heel model — higher heel close-hauled, less downwind."""
    abs_twa = abs(twa_deg)
    # Heel peaks around 30–60° TWA, drops off downwind
    if abs_twa < 30:
        twa_factor = abs_twa / 30 * 0.9
    elif abs_twa < 90:
        twa_factor = 0.9 + 0.1 * (1 - (abs_twa - 30) / 60)
    elif abs_twa < 140:
        twa_factor = 0.5 * (1 - (abs_twa - 90) / 50)
    else:
        twa_factor = 0.05

    heel = tws_kt * 1.4 * twa_factor
    heel = min(heel, 28.0)  # cap at 28°
    # Sign: positive TWA (starboard) → positive heel (to leeward)
    sign = 1.0 if twa_deg >= 0 else -1.0
    return sign * (heel + random.gauss(0, 0.3))


class InteractiveSource(NmeaSource):
    """User-steered sailing simulator for laptop testing.

    Wind oscillates ±3° with a ~90s period for natural shift testing.
    Position updates by dead reckoning from BSP + heading.
    """

    def __init__(
        self,
        hz: int = 10,
        twd: float = 180.0,
        tws: float = 10.0,
    ):
        self.hz = hz
        self._running = False

        # Mutable state (set from REST endpoints)
        self.heading = 40.0  # magnetic, initial port tack close-hauled (TWD=0°)
        self.twd_base = twd
        self.tws_base = tws
        self.sim_speed = 5.0  # position multiplier for fast simulation

        # Lake Lugano start position (near start line)
        self.lat = 46.0000
        self.lon = 8.9630
        self.magnetic_variation = 2.5

        # Internal tick counter for wind oscillation
        self._tick = 0

    @property
    def pgns_per_step(self) -> int:
        return 8  # 7 standard + PGN 127257 (attitude)

    # ── Thread-safe mutators (called from REST handlers) ──────────

    def set_heading(self, heading: float = None, delta: float = None) -> float:
        """Set absolute heading or apply delta.  Returns new heading."""
        if heading is not None:
            self.heading = heading % 360
        elif delta is not None:
            self.heading = (self.heading + delta) % 360
        return self.heading

    def set_position(self, lat: float, lon: float, heading: float = None) -> dict:
        """Teleport boat to a specific lat/lon (and optionally heading)."""
        self.lat = lat
        self.lon = lon
        if heading is not None:
            self.heading = heading % 360
        return {"lat": self.lat, "lon": self.lon, "heading": self.heading}

    def set_wind(
        self,
        twd: float = None,
        tws: float = None,
        twd_delta: float = None,
        tws_delta: float = None,
    ) -> dict:
        """Update base wind conditions (absolute or delta)."""
        if twd is not None:
            self.twd_base = twd % 360
        elif twd_delta is not None:
            self.twd_base = (self.twd_base + twd_delta) % 360
        if tws is not None:
            self.tws_base = max(0.0, tws)
        elif tws_delta is not None:
            self.tws_base = max(0.0, self.tws_base + tws_delta)
        return {"twd": self.twd_base, "tws": self.tws_base}

    # ── NmeaSource interface ──────────────────────────────────────

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def stream(self) -> AsyncIterator[Tuple[int, bytes]]:
        """Yield PGN frames at configured Hz, physics computed each step."""
        dt = 1.0 / self.hz

        while self._running:
            self._tick += 1

            # ── Wind with natural oscillation ────────────────────
            osc = 3.0 * math.sin(2 * math.pi * self._tick / (90 * self.hz))
            twd = (self.twd_base + osc) % 360
            tws = self.tws_base + random.gauss(0, 0.2)
            tws = max(1.0, tws)

            # ── Boat physics ─────────────────────────────────────
            hdg = self.heading

            # TWA: signed angle from bow to true wind
            raw_twa = twd - hdg
            # Normalise to −180…+180
            if raw_twa > 180:
                raw_twa -= 360
            elif raw_twa < -180:
                raw_twa += 360

            # BSP from polar + small noise
            bsp = _polar_speed(raw_twa, tws)
            bsp = max(0.0, bsp + random.gauss(0, 0.05))

            # Reverse wind triangle → apparent wind
            awa, aws = _true_to_apparent(raw_twa, tws, bsp)

            # SOG and COG (simplified: slight current effect)
            sog = bsp * 0.97 + random.gauss(0, 0.03)
            sog = max(0.0, sog)
            hdg_true = hdg - self.magnetic_variation
            cog = (hdg_true + random.gauss(0, 0.8)) % 360

            # Dead reckoning position (sim_speed multiplies movement)
            dist_nm = (sog * dt * self.sim_speed) / 3600.0
            cog_rad = math.radians(cog)
            self.lat += (dist_nm / 60.0) * math.cos(cog_rad)
            self.lon += (dist_nm / 60.0) * math.sin(cog_rad) / math.cos(
                math.radians(self.lat)
            )

            # Heel from wind
            heel = _compute_heel(raw_twa, tws)
            trim = random.gauss(-1.0, 0.3)  # slight bow-down

            # Environment
            depth = 15.0 + random.gauss(0, 0.2)
            water_temp = 12.5

            # ── Yield PGN frames ─────────────────────────────────
            # 7 standard PGNs (same as SimulatorSource)
            for pgn, data in _encode_state(
                hdg, bsp, awa, aws, depth, water_temp,
                self.lat, self.lon, sog, cog,
            ):
                yield (pgn, data)

            # PGN 127257: Attitude (heel/trim) — frame #8
            yield _encode_attitude(heel, trim)

            await asyncio.sleep(dt)
