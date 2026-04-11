"""BoatState — complete instrument state at a single moment in time."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BoatState:
    """All sensor, calibrated, and derived fields for the current instant.

    Field groups:
    - raw_*     : values straight from PGN decode (before calibration)
    - no prefix : calibrated values (after offset/factor correction)
    - derived   : computed from calibrated values (TWA, VMG, leeway, …)
    - target_*  : from polar table lookup (Phase 3)
    - *_age_ms  : sensor health / staleness tracking
    """

    timestamp: datetime

    # ── Raw sensor data (from PGN decode, before calibration) ──────────
    raw_heading_mag: Optional[float] = None   # degrees, PGN 127250
    raw_bsp_kt: Optional[float] = None        # knots, PGN 128259
    raw_awa_deg: Optional[float] = None        # degrees signed (−port +stbd), PGN 130306
    raw_aws_kt: Optional[float] = None         # knots, PGN 130306
    raw_depth_m: Optional[float] = None        # meters, PGN 128267
    raw_water_temp_c: Optional[float] = None   # celsius, PGN 130310
    lat: Optional[float] = None                # decimal degrees, PGN 129025/129029
    lon: Optional[float] = None                # decimal degrees
    raw_sog_kt: Optional[float] = None         # knots, PGN 129026
    raw_cog_deg: Optional[float] = None        # degrees true, PGN 129026
    magnetic_variation: float = 2.5            # degrees east positive

    # ── Calibrated values ──────────────────────────────────────────────
    heading_mag: Optional[float] = None        # degrees magnetic
    bsp_kt: Optional[float] = None             # knots (through water)
    awa_deg: Optional[float] = None            # degrees signed
    aws_kt: Optional[float] = None             # knots
    depth_m: Optional[float] = None            # meters (below keel after offset)
    sog_kt: Optional[float] = None             # knots (over ground)
    cog_deg: Optional[float] = None            # degrees true
    water_temp_c: Optional[float] = None       # celsius

    # ── Wind correction (after calibration, before true wind) ──────────
    awa_corrected_deg: Optional[float] = None   # after heel + upwash correction
    aws_corrected_kt: Optional[float] = None    # after heel correction
    upwash_offset_deg: Optional[float] = None   # upwash offset applied (debug)
    heel_correction_deg: Optional[float] = None  # heel angle correction applied (debug)

    # ── Active sail configuration ────────────────────────────────────────
    active_sail_config: Optional[str] = None     # e.g. "main_1__genoa"

    # ── Upwash learning status ──────────────────────────────────────────
    upwash_learning_status: Optional[str] = None  # waiting|pre_tack|post_tack|updated|rejected

    # ── Computed / derived ─────────────────────────────────────────────
    twa_deg: Optional[float] = None            # signed: −port +stbd
    tws_kt: Optional[float] = None             # knots
    twd_deg: Optional[float] = None            # 0–360, direction wind comes FROM
    vmg_kt: Optional[float] = None             # BSP × cos(TWA)
    leeway_deg: Optional[float] = None         # estimated from heel
    current_set_deg: Optional[float] = None    # direction current flows TO, 0–360
    current_drift_kt: Optional[float] = None   # knots

    # ── Atlas 2 IMU data (via NMEA 2000 when available) ────────────────
    heel_deg: Optional[float] = None           # −port +stbd
    trim_deg: Optional[float] = None           # −bow down +bow up

    # ── Performance targets (Phase 3, from polar table) ────────────────
    target_twa_deg: Optional[float] = None     # optimal VMG angle (upwind or downwind)
    target_bsp_kt: Optional[float] = None      # polar speed at current TWA/TWS
    target_vmg_kt: Optional[float] = None      # polar VMG
    perf_pct: Optional[float] = None           # BSP / target_BSP × 100
    vmg_perf_pct: Optional[float] = None       # VMG / target_VMG × 100

    # ── Race timer (Phase 4) ─────────────────────────────────────────
    race_state: str = "idle"                     # idle | countdown | racing
    race_timer_secs: Optional[float] = None      # countdown: remaining, racing: elapsed

    # ── Navigation to mark (Phase 4) ─────────────────────────────────
    btw_deg: Optional[float] = None              # bearing to waypoint, 0–360
    dtw_nm: Optional[float] = None               # distance to waypoint, NM
    next_mark_name: Optional[str] = None          # active mark name

    # ── VMC / course geometry ──────────────────────────────────────────
    leg_bearing_deg: Optional[float] = None     # bearing from start to mark, 0–360
    course_offset_deg: Optional[float] = None   # leg_bearing − TWD (course rotation)
    vmc_kt: Optional[float] = None              # velocity made on course
    target_twa_vmc_deg: Optional[float] = None  # VMC-optimal TWA (per-tack adjusted)
    target_vmc_kt: Optional[float] = None       # target VMC at adjusted TWA
    line_bias_deg: Optional[float] = None       # start line bias (+ = pin favored)
    dist_to_line_nm: Optional[float] = None     # distance to start line

    # ── Laylines ────────────────────────────────────────────────────────
    layline_port_deg: Optional[float] = None     # port layline compass bearing
    layline_stbd_deg: Optional[float] = None     # starboard layline compass bearing
    dist_to_port_layline_nm: Optional[float] = None  # cross-track distance to port layline
    dist_to_stbd_layline_nm: Optional[float] = None  # cross-track distance to stbd layline

    # ── GPS / system info ────────────────────────────────────────────────
    gps_time: Optional[str] = None              # UTC time string from GNSS
    gps_num_sats: Optional[int] = None          # satellites in view
    trip_log_nm: Optional[float] = None         # trip distance (NM)
    total_log_nm: Optional[float] = None        # cumulative distance (NM)

    # ── Sensor health ──────────────────────────────────────────────────
    gps_fix: bool = False
    heading_age_ms: int = 9999
    bsp_age_ms: int = 9999
    wind_age_ms: int = 9999
    depth_age_ms: int = 9999

    @classmethod
    def new(cls) -> "BoatState":
        """Create a fresh BoatState with current UTC timestamp."""
        return cls(timestamp=datetime.now(timezone.utc))
