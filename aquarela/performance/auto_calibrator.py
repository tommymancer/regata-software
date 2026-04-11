"""Auto-calibration for compass offset, speed factor, and AWA offset.

Collects samples over a configurable window while sailing, then computes
the correction.

Compass offset:  circular mean of (raw_heading_mag - (COG - mag_var))
Speed factor:    median of (SOG / raw_bsp)
AWA offset:      tack-symmetry — compare |AWA| on port vs starboard legs
"""

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional

from ..pipeline.state import BoatState


@dataclass
class CalibrationResult:
    mode: str                    # "compass", "speed", or "awa"
    value: float                 # computed offset or factor
    samples: int                 # how many samples used
    std_dev: float               # spread (degrees or ratio)
    quality: str                 # "good", "fair", "poor"
    detail: Optional[dict] = None  # extra info (e.g. per-leg averages)


# Minimum thresholds
MIN_BSP_KT = 2.5
MIN_SOG_KT = 2.5
MAX_COG_SPREAD_DEG = 15.0  # reject if course wanders too much
DURATION_S = 30.0

# AWA calibration thresholds
AWA_MAX_CLOSE_HAULED = 55.0    # |AWA| must be below this to count
AWA_MIN_BSP_KT = 2.0           # minimum BSP for valid samples
AWA_MIN_LEG_DURATION_S = 15.0  # minimum seconds per leg
AWA_MIN_LEG_SAMPLES = 10       # minimum samples per leg (at 10 Hz decimated to ~1 Hz)
AWA_MIN_LEGS_PER_SIDE = 2      # need at least this many legs on each tack
AWA_TIMEOUT_S = 600.0           # 10 minute max


@dataclass
class _AwaLeg:
    """One close-hauled leg on a single tack."""
    tack: str                    # "port" or "stbd"
    awa_values: List[float] = field(default_factory=list)
    start_time: float = 0.0

    @property
    def duration_s(self) -> float:
        if not self.awa_values:
            return 0.0
        return time.monotonic() - self.start_time

    @property
    def mean_abs_awa(self) -> float:
        if not self.awa_values:
            return 0.0
        return sum(abs(a) for a in self.awa_values) / len(self.awa_values)

    @property
    def is_valid(self) -> bool:
        return (
            len(self.awa_values) >= AWA_MIN_LEG_SAMPLES
            and self.duration_s >= AWA_MIN_LEG_DURATION_S
        )


class AutoCalibrator:
    """Collects pipeline samples and computes calibration corrections."""

    def __init__(self) -> None:
        self._mode: Optional[str] = None   # "compass" | "speed" | "awa" | None
        self._start_time: float = 0.0
        self._compass_samples: List[tuple] = []   # (raw_hdg, cog, mag_var)
        self._speed_samples: List[tuple] = []      # (raw_bsp, sog)
        self._cog_samples: List[float] = []        # for spread check
        self._result: Optional[CalibrationResult] = None
        # AWA tack-symmetry state
        self._awa_legs: List[_AwaLeg] = []
        self._awa_current_leg: Optional[_AwaLeg] = None
        self._awa_tick: int = 0  # decimation counter

    @property
    def is_collecting(self) -> bool:
        return self._mode is not None

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    @property
    def progress(self) -> float:
        """0.0–1.0 fraction of collection complete."""
        if not self._mode:
            return 0.0
        if self._mode == "awa":
            return self._awa_progress()
        elapsed = time.monotonic() - self._start_time
        return min(1.0, elapsed / DURATION_S)

    @property
    def awa_status(self) -> Optional[dict]:
        """AWA-specific progress info (legs collected per side)."""
        if self._mode != "awa":
            return None
        port = sum(1 for l in self._awa_legs if l.tack == "port" and l.is_valid)
        stbd = sum(1 for l in self._awa_legs if l.tack == "stbd" and l.is_valid)
        current_tack = self._awa_current_leg.tack if self._awa_current_leg else None
        current_dur = self._awa_current_leg.duration_s if self._awa_current_leg else 0
        return {
            "port_legs": port,
            "stbd_legs": stbd,
            "target_per_side": AWA_MIN_LEGS_PER_SIDE,
            "current_tack": current_tack,
            "current_leg_s": round(current_dur, 0),
            "min_leg_s": AWA_MIN_LEG_DURATION_S,
        }

    def _awa_progress(self) -> float:
        port = sum(1 for l in self._awa_legs if l.tack == "port" and l.is_valid)
        stbd = sum(1 for l in self._awa_legs if l.tack == "stbd" and l.is_valid)
        total_needed = AWA_MIN_LEGS_PER_SIDE * 2
        return min(1.0, (port + stbd) / total_needed)

    @property
    def result(self) -> Optional[CalibrationResult]:
        return self._result

    def start(self, mode: str) -> None:
        """Begin collecting samples. mode = 'compass', 'speed', or 'awa'."""
        if mode not in ("compass", "speed", "awa"):
            raise ValueError(f"Invalid mode: {mode}")
        self._mode = mode
        self._start_time = time.monotonic()
        self._compass_samples.clear()
        self._speed_samples.clear()
        self._cog_samples.clear()
        self._awa_legs.clear()
        self._awa_current_leg = None
        self._awa_tick = 0
        self._result = None

    def cancel(self) -> None:
        self._mode = None
        self._result = None

    def update(self, state: BoatState) -> None:
        """Called every pipeline tick while collecting."""
        if self._mode is None:
            return

        if self._mode == "awa":
            self._update_awa(state)
            return

        # Time's up — compute result
        if time.monotonic() - self._start_time >= DURATION_S:
            self._compute()
            return

        # Gate: need GPS fix, decent speed, straight-ish course
        if state.raw_sog_kt is None or state.raw_cog_deg is None:
            return
        if state.raw_sog_kt < MIN_SOG_KT:
            return

        if self._mode == "compass":
            if state.raw_heading_mag is None:
                return
            self._compass_samples.append((
                state.raw_heading_mag,
                state.raw_cog_deg,
                state.magnetic_variation or 0.0,
            ))
            self._cog_samples.append(state.raw_cog_deg)

        elif self._mode == "speed":
            if state.raw_bsp_kt is None or state.raw_bsp_kt < MIN_BSP_KT:
                return
            self._speed_samples.append((
                state.raw_bsp_kt,
                state.raw_sog_kt,
            ))
            self._cog_samples.append(state.raw_cog_deg)

    # ── AWA tack-symmetry calibration ──────────────────────────────

    def _update_awa(self, state: BoatState) -> None:
        """Collect AWA samples, detect tacks, finalize legs."""
        # Timeout
        if time.monotonic() - self._start_time >= AWA_TIMEOUT_S:
            self._compute_awa()
            return

        # Check if we have enough legs already
        port_ok = sum(1 for l in self._awa_legs if l.tack == "port" and l.is_valid)
        stbd_ok = sum(1 for l in self._awa_legs if l.tack == "stbd" and l.is_valid)
        if port_ok >= AWA_MIN_LEGS_PER_SIDE and stbd_ok >= AWA_MIN_LEGS_PER_SIDE:
            self._compute_awa()
            return

        # Need raw AWA and decent BSP
        if state.raw_awa_deg is None or state.raw_bsp_kt is None:
            return
        if state.raw_bsp_kt < AWA_MIN_BSP_KT:
            return
        if abs(state.raw_awa_deg) > AWA_MAX_CLOSE_HAULED:
            return  # not close-hauled, skip

        # Determine current tack from raw AWA sign
        tack = "stbd" if state.raw_awa_deg > 0 else "port"

        # Detect tack change — finalize current leg
        if self._awa_current_leg is not None and self._awa_current_leg.tack != tack:
            if self._awa_current_leg.is_valid:
                self._awa_legs.append(self._awa_current_leg)
            self._awa_current_leg = None

        # Start new leg if needed
        if self._awa_current_leg is None:
            self._awa_current_leg = _AwaLeg(tack=tack, start_time=time.monotonic())

        # Collect sample (raw AWA — the offset error is what we're measuring)
        self._awa_current_leg.awa_values.append(state.raw_awa_deg)

    def _compute_awa(self) -> None:
        """Compute AWA offset from tack symmetry.

        On starboard: raw_AWA ≈ +true_AWA + δ
        On port:      raw_AWA ≈ -true_AWA + δ

        So: mean_stbd_abs = true_AWA + δ
            mean_port_abs = true_AWA - δ
            δ = (mean_stbd_abs - mean_port_abs) / 2
        """
        # Include current leg if valid
        if self._awa_current_leg is not None and self._awa_current_leg.is_valid:
            self._awa_legs.append(self._awa_current_leg)
        self._awa_current_leg = None
        self._mode = None

        port_legs = [l for l in self._awa_legs if l.tack == "port" and l.is_valid]
        stbd_legs = [l for l in self._awa_legs if l.tack == "stbd" and l.is_valid]

        if len(port_legs) < 1 or len(stbd_legs) < 1:
            self._result = CalibrationResult(
                mode="awa", value=0.0,
                samples=len(port_legs) + len(stbd_legs),
                std_dev=0.0, quality="poor",
                detail={
                    "port_legs": len(port_legs),
                    "stbd_legs": len(stbd_legs),
                    "reason": "non abbastanza bordi",
                },
            )
            return

        # Per-leg mean |AWA|
        port_means = [l.mean_abs_awa for l in port_legs]
        stbd_means = [l.mean_abs_awa for l in stbd_legs]

        avg_port = sum(port_means) / len(port_means)
        avg_stbd = sum(stbd_means) / len(stbd_means)

        # Offset = half the asymmetry
        offset = (avg_stbd - avg_port) / 2.0

        # Quality: check consistency across legs
        all_means = port_means + stbd_means
        total_samples = sum(len(l.awa_values) for l in port_legs + stbd_legs)
        spread = max(all_means) - min(all_means) if len(all_means) > 1 else 0.0

        quality = "good" if spread < 4.0 else "fair" if spread < 8.0 else "poor"
        # Downgrade if too few legs
        if len(port_legs) < AWA_MIN_LEGS_PER_SIDE or len(stbd_legs) < AWA_MIN_LEGS_PER_SIDE:
            quality = "fair" if quality == "good" else quality

        self._result = CalibrationResult(
            mode="awa",
            value=round(offset, 1),
            samples=total_samples,
            std_dev=round(spread, 1),
            quality=quality,
            detail={
                "port_legs": len(port_legs),
                "stbd_legs": len(stbd_legs),
                "avg_port_awa": round(avg_port, 1),
                "avg_stbd_awa": round(avg_stbd, 1),
                "per_leg": [
                    {"tack": l.tack, "mean_awa": round(l.mean_abs_awa, 1),
                     "samples": len(l.awa_values), "duration_s": round(l.duration_s, 0)}
                    for l in self._awa_legs if l.is_valid
                ],
            },
        )

    # ── Compass / Speed compute ──────────────────────────────────

    def _compute(self) -> None:
        """Compute calibration result from collected samples."""
        mode = self._mode
        self._mode = None

        # Check course stability
        if len(self._cog_samples) > 10:
            spread = _circular_spread(self._cog_samples)
            if spread > MAX_COG_SPREAD_DEG:
                self._result = CalibrationResult(
                    mode=mode,
                    value=0.0,
                    samples=0,
                    std_dev=spread,
                    quality="poor",
                )
                return

        if mode == "compass":
            self._compute_compass()
        elif mode == "speed":
            self._compute_speed()

    def _compute_compass(self) -> None:
        if len(self._compass_samples) < 20:
            self._result = CalibrationResult(
                mode="compass", value=0.0, samples=len(self._compass_samples),
                std_dev=0.0, quality="poor",
            )
            return

        # Compute offset: raw_heading_mag should equal (COG - mag_var) when
        # going straight. So offset = raw_heading - (COG - mag_var).
        # Use circular mean for angles.
        diffs = []
        for raw_hdg, cog, mag_var in self._compass_samples:
            expected_mag = (cog - mag_var) % 360
            diff = _angle_diff(raw_hdg, expected_mag)
            diffs.append(diff)

        offset = _circular_mean_scalar(diffs)
        std = _circular_std(diffs)

        quality = "good" if std < 3.0 else "fair" if std < 6.0 else "poor"

        self._result = CalibrationResult(
            mode="compass",
            value=round(offset, 1),
            samples=len(self._compass_samples),
            std_dev=round(std, 1),
            quality=quality,
        )

    def _compute_speed(self) -> None:
        if len(self._speed_samples) < 20:
            self._result = CalibrationResult(
                mode="speed", value=1.0, samples=len(self._speed_samples),
                std_dev=0.0, quality="poor",
            )
            return

        # Factor = SOG / raw_bsp (median, robust to outliers)
        ratios = [sog / raw_bsp for raw_bsp, sog in self._speed_samples if raw_bsp > 0.5]
        if not ratios:
            self._result = CalibrationResult(
                mode="speed", value=1.0, samples=0, std_dev=0.0, quality="poor",
            )
            return

        ratios.sort()
        n = len(ratios)
        median = ratios[n // 2] if n % 2 else (ratios[n // 2 - 1] + ratios[n // 2]) / 2

        # Standard deviation of ratios
        mean = sum(ratios) / n
        std = math.sqrt(sum((r - mean) ** 2 for r in ratios) / n)

        quality = "good" if std < 0.03 else "fair" if std < 0.06 else "poor"

        self._result = CalibrationResult(
            mode="speed",
            value=round(median, 3),
            samples=len(ratios),
            std_dev=round(std, 3),
            quality=quality,
        )


# ── Circular stats helpers ────────────────────────────────────────────

def _angle_diff(a: float, b: float) -> float:
    """Signed difference a - b, normalized to [-180, 180)."""
    d = (a - b) % 360
    return d if d < 180 else d - 360


def _circular_mean_scalar(angles_deg: list) -> float:
    """Circular mean of a list of angles in degrees."""
    sin_sum = sum(math.sin(math.radians(a)) for a in angles_deg)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles_deg)
    return math.degrees(math.atan2(sin_sum, cos_sum))


def _circular_std(angles_deg: list) -> float:
    """Circular standard deviation in degrees."""
    n = len(angles_deg)
    if n == 0:
        return 0.0
    sin_sum = sum(math.sin(math.radians(a)) for a in angles_deg)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles_deg)
    r = math.sqrt(sin_sum ** 2 + cos_sum ** 2) / n
    if r >= 1.0:
        return 0.0
    return math.degrees(math.sqrt(-2 * math.log(r)))


def _circular_spread(angles_deg: list) -> float:
    """Range of angles (max angular spread) in degrees."""
    if len(angles_deg) < 2:
        return 0.0
    diffs = []
    for i in range(1, len(angles_deg)):
        d = abs(_angle_diff(angles_deg[i], angles_deg[i - 1]))
        diffs.append(d)
    # Use 95th percentile of consecutive diffs as spread indicator
    diffs.sort()
    idx = int(0.95 * len(diffs))
    return sum(diffs[:idx + 1]) / (idx + 1) if diffs else 0.0
