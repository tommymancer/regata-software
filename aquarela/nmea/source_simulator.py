"""Simulated NMEA 2000 PGN source for development and testing.

Generates realistic sailing data for Lake Lugano without any marine hardware.
Produces the same (pgn, bytes) tuples that the CAN HAT source would,
so the entire downstream pipeline is exercised identically.

Scenarios model a Nitro 80 training session: upwind legs, tacks, downwind,
gybes, wind shifts — all with realistic speeds, angles, and sensor noise.
"""

import asyncio
import math
import random
import struct
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional, Tuple

from .source_base import NmeaSource

# ── Unit conversion constants ──────────────────────────────────────────
KT_TO_MS = 1.0 / 1.94384
DEG_TO_RAD = math.pi / 180.0


# ── Scenario definition ───────────────────────────────────────────────

@dataclass
class SimulatorScenario:
    """A single segment of a simulated sailing session."""
    name: str                # e.g. "upwind_port", "tack_to_starboard"
    duration_s: float        # how long this segment lasts
    twa_target: float        # target TWA in degrees (signed: −port +stbd)
    tws_base: float          # base TWS in knots
    heading_start: float     # heading at segment start (magnetic degrees)
    heading_end: float       # heading at segment end (for tacks/gybes)
    bsp_factor: float        # fraction of polar speed (0.0–1.0)
    tws_trend: float = 0.0   # TWS change per second (for building/dying wind)


# ── Pre-defined Lake Lugano training session ───────────────────────────
# Wind: southerly Breva ~180° magnetic, 8–12 kn, typical afternoon thermal

LUGANO_TRAINING_SESSION: List[SimulatorScenario] = [
    # Upwind port tack (TWD ~180, heading ~220, TWA ~-42)
    SimulatorScenario("upwind_port",         120, -42,  10, 222, 222, 0.92),
    # Tack to starboard
    SimulatorScenario("tack_to_stbd",         10, -42,  10, 222, 138, 0.55),
    # Upwind starboard tack
    SimulatorScenario("upwind_stbd",         120,  42,  10, 138, 138, 0.90),
    # Bear away to reach
    SimulatorScenario("bear_away",            12,  42,  10, 138,  80, 0.80),
    # Beam reach
    SimulatorScenario("beam_reach",           60,  90,  10,  80,  80, 0.93),
    # Bear away to run
    SimulatorScenario("bear_away_to_run",     10,  90,  10,  80,  35, 0.75),
    # Downwind starboard gybe
    SimulatorScenario("downwind_stbd",        90, 150,  10,  35,  35, 0.88),
    # Gybe to port
    SimulatorScenario("gybe_to_port",          8, 150,  10,  35, 325, 0.50),
    # Downwind port gybe
    SimulatorScenario("downwind_port",        90,-150,  10, 325, 325, 0.87),
    # Round up to upwind
    SimulatorScenario("round_up",             12,-150,  10, 325, 218, 0.75),
    # Upwind port with building wind
    SimulatorScenario("upwind_port_building", 90, -42,  10, 218, 218, 0.91, tws_trend=0.02),
    # Wind shift: TWD shifts right 10°, header on port tack
    SimulatorScenario("wind_shift",           20, -47,  12, 218, 218, 0.85),
    # Tack after shift
    SimulatorScenario("tack_after_shift",     10, -47,  12, 218, 128, 0.55),
    # Upwind stbd, lifted after shift
    SimulatorScenario("upwind_stbd_lifted",   90,  37,  12, 128, 128, 0.93),
]


class SimulatorSource(NmeaSource):
    """Generate realistic PGN data simulating sailing on Lake Lugano.

    The simulator works in "true wind space": it defines TWD, TWS, and the
    boat's response (TWA, BSP from polar), then reverse-computes apparent
    wind (AWA, AWS) using the wind triangle — exactly as a real sensor setup
    would produce.
    """

    def __init__(
        self,
        hz: int = 10,
        scenarios: Optional[List[SimulatorScenario]] = None,
        loop: bool = True,
    ):
        self.hz = hz
        self.scenarios = scenarios or LUGANO_TRAINING_SESSION
        self.loop = loop
        self._running = False

        # Lake Lugano starting position (near Lugano bay)
        self.lat = 46.0020
        self.lon = 8.9627
        self.magnetic_variation = 2.5  # degrees east
        self._twd = 180.0  # initial true wind direction (southerly Breva)

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def stream(self) -> AsyncIterator[Tuple[int, bytes]]:
        """Yield PGN frames at configured Hz, cycling through scenarios."""
        dt = 1.0 / self.hz

        while self._running:
            for scenario in self.scenarios:
                if not self._running:
                    return

                steps = int(scenario.duration_s * self.hz)
                tws_current = scenario.tws_base

                for i in range(steps):
                    if not self._running:
                        return

                    t = i / max(steps - 1, 1)  # 0.0 → 1.0 progress

                    # Evolve TWS with trend
                    tws_current += scenario.tws_trend * dt

                    # Interpolate heading (smooth for tacks/gybes)
                    hdg = _interp_heading(
                        scenario.heading_start, scenario.heading_end, t
                    )

                    # Add wind oscillation (±3° over ~90s period)
                    twd_osc = 3.0 * math.sin(2 * math.pi * i / (90 * self.hz))
                    twd = self._twd + twd_osc

                    # Compute TWA from heading and TWD
                    twa = scenario.twa_target + random.gauss(0, 1.0)

                    # BSP from approximate Nitro 80 polar
                    tws_noisy = tws_current + random.gauss(0, 0.3)
                    tws_noisy = max(0.5, tws_noisy)
                    bsp = _polar_speed(twa, tws_noisy) * scenario.bsp_factor
                    # BSP reduction during maneuvers (smoothstep already handles heading)
                    if scenario.heading_start != scenario.heading_end:
                        # Mid-maneuver speed dip
                        maneuver_dip = 1.0 - 0.4 * math.sin(math.pi * t)
                        bsp *= maneuver_dip
                    bsp = max(0.0, bsp + random.gauss(0, 0.08))

                    # Reverse wind triangle: TWA/TWS/BSP → AWA/AWS
                    awa, aws = _true_to_apparent(twa, tws_noisy, bsp)

                    # Dead reckoning position
                    hdg_true = hdg - self.magnetic_variation
                    sog = bsp * 0.97 + random.gauss(0, 0.05)
                    sog = max(0.0, sog)
                    cog = (hdg_true + random.gauss(0, 1.5)) % 360
                    self._update_position(sog, cog, dt)

                    # Environment
                    depth = 15.0 + random.gauss(0, 0.3)
                    water_temp = 12.5 + random.gauss(0, 0.05)

                    # Encode and yield all PGN frames for this instant
                    for pgn, data in _encode_state(
                        hdg, bsp, awa, aws, depth, water_temp,
                        self.lat, self.lon, sog, cog,
                    ):
                        yield (pgn, data)

                    await asyncio.sleep(dt)

            if not self.loop:
                return

    def _update_position(self, sog_kt: float, cog_deg: float, dt: float) -> None:
        """Dead-reckon position update."""
        dist_nm = (sog_kt * dt) / 3600.0
        cog_rad = math.radians(cog_deg)
        self.lat += (dist_nm / 60.0) * math.cos(cog_rad)
        self.lon += (dist_nm / 60.0) * math.sin(cog_rad) / math.cos(
            math.radians(self.lat)
        )


# ── Sailing physics helpers ────────────────────────────────────────────

def _polar_speed(twa: float, tws: float) -> float:
    """Approximate Nitro 80 polar speed in knots.

    Simplified model based on similar sportboats (Melges 24, J/70) scaled
    for the Nitro 80's displacement (~1100 kg) and sail area (~35 m² upwind).
    """
    abs_twa = abs(twa)
    if abs_twa < 30:
        factor = 0.35
    elif abs_twa < 42:
        factor = 0.65
    elif abs_twa < 55:
        factor = 0.72
    elif abs_twa < 75:
        factor = 0.78
    elif abs_twa < 100:
        factor = 0.82
    elif abs_twa < 120:
        factor = 0.80
    elif abs_twa < 145:
        factor = 0.75
    elif abs_twa < 165:
        factor = 0.65
    else:
        factor = 0.55
    return min(tws * factor, 12.0)  # cap at ~12 kn


def _true_to_apparent(twa: float, tws: float, bsp: float) -> Tuple[float, float]:
    """Reverse wind triangle: given TWA/TWS/BSP, compute AWA/AWS.

    This is the inverse of the true wind calculation in the pipeline.
    """
    twa_rad = math.radians(twa)
    tw_x = tws * math.cos(twa_rad)
    tw_y = tws * math.sin(twa_rad)
    aw_x = tw_x + bsp
    aw_y = tw_y
    aws = math.sqrt(aw_x ** 2 + aw_y ** 2)
    awa = math.degrees(math.atan2(aw_y, aw_x))
    return awa, aws


def _interp_heading(start: float, end: float, t: float) -> float:
    """Smoothly interpolate heading with 360°/0° wrap handling.

    Uses smoothstep for natural tack/gybe motion (slow at start/end,
    fast through the middle).
    """
    diff = ((end - start + 180) % 360) - 180
    s = t * t * (3 - 2 * t)  # smoothstep
    return (start + diff * s) % 360


# ── PGN encoding (simulator → same bytes as real CAN bus) ──────────────

def _encode_state(
    hdg: float,
    bsp: float,
    awa: float,
    aws: float,
    depth: float,
    water_temp: float,
    lat: float,
    lon: float,
    sog: float,
    cog: float,
) -> List[Tuple[int, bytes]]:
    """Encode current boat state into NMEA 2000 PGN byte frames.

    The encoding matches the byte layouts expected by pgn_decoder.py,
    ensuring a perfect round-trip: encode → decode → original values (±precision).
    """
    frames: List[Tuple[int, bytes]] = []

    # PGN 127250: Vessel Heading
    hdg_raw = int((hdg * DEG_TO_RAD) / 0.0001) & 0xFFFF
    data = bytes([0xFF]) + struct.pack("<H", hdg_raw) + bytes(5)
    frames.append((127250, data))

    # PGN 128259: Speed, Water Referenced
    bsp_raw = int((bsp * KT_TO_MS) / 0.01) & 0xFFFF
    data = bytes([0xFF]) + struct.pack("<H", bsp_raw) + bytes(5)
    frames.append((128259, data))

    # PGN 130306: Wind Data (apparent, reference=2)
    aws_raw = int((aws * KT_TO_MS) / 0.01) & 0xFFFF
    awa_norm = awa if awa >= 0 else awa + 360
    awa_raw = int((awa_norm * DEG_TO_RAD) / 0.0001) & 0xFFFF
    data = bytes([0xFF]) + struct.pack("<HH", aws_raw, awa_raw) + bytes([2, 0xFF, 0xFF])
    frames.append((130306, data))

    # PGN 128267: Water Depth
    depth_raw = int(depth / 0.01) & 0xFFFFFFFF
    data = bytes([0xFF]) + struct.pack("<I", depth_raw) + bytes(3)
    frames.append((128267, data))

    # PGN 129025: Position Rapid Update
    lat_raw = int(lat * 1e7)
    lon_raw = int(lon * 1e7)
    data = struct.pack("<ii", lat_raw, lon_raw)
    frames.append((129025, data))

    # PGN 129026: COG/SOG Rapid Update
    cog_norm = cog % 360
    cog_raw = int((cog_norm * DEG_TO_RAD) / 0.0001) & 0xFFFF
    sog_raw = int((sog * KT_TO_MS) / 0.01) & 0xFFFF
    data = bytes([0xFF, 0xFF]) + struct.pack("<HH", cog_raw, sog_raw) + bytes(2)
    frames.append((129026, data))

    # PGN 130310: Environmental Parameters
    temp_k = water_temp + 273.15
    temp_raw = int(temp_k / 0.01) & 0xFFFF
    data = bytes([0xFF]) + struct.pack("<H", temp_raw) + bytes(5)
    frames.append((130310, data))

    return frames
