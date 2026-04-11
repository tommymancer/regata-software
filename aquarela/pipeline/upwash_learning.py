"""Upwash auto-learning from tack/gybe TWD residuals.

Principle: in stable wind the true wind direction must be identical on
both tacks.  A systematic TWD shift after a tack is attributed to
residual upwash error and used to nudge the correction table.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Optional, Tuple


# ── helper functions ────────────────────────────────────────────────────

def _angle_mean(angles: list[float]) -> float:
    """Circular mean of a list of angles in degrees."""
    s = sum(math.sin(math.radians(a)) for a in angles)
    c = sum(math.cos(math.radians(a)) for a in angles)
    return math.degrees(math.atan2(s, c)) % 360


def _angle_std(angles: list[float]) -> float:
    """Circular standard deviation in degrees.

    sigma = degrees(sqrt(-2 * ln(R))) where R is the mean resultant length.
    """
    n = len(angles)
    if n == 0:
        return 0.0
    s = sum(math.sin(math.radians(a)) for a in angles)
    c = sum(math.cos(math.radians(a)) for a in angles)
    r = math.hypot(s, c) / n
    # Clamp R to avoid log(0) or negative argument
    r = min(r, 1.0)
    if r < 1e-10:
        return 180.0  # maximally dispersed
    return math.degrees(math.sqrt(-2.0 * math.log(r)))


def _angle_diff(a: float, b: float) -> float:
    """Signed angular difference (a - b) wrapped to -180..+180."""
    d = (a - b) % 360
    if d > 180:
        d -= 360
    return d


def _std(values: list[float]) -> float:
    """Linear standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


# ── UpwashLearner ───────────────────────────────────────────────────────

class UpwashLearner:
    """Detects tacks/gybes and learns upwash corrections from TWD residuals."""

    def __init__(
        self,
        hz: int = 10,
        buffer_seconds: int = 180,
        pre_window: int = 120,
        post_window: int = 120,
        twd_sigma_max: float = 5.0,
        bsp_min: float = 3.0,
        awa_settle_sigma: float = 3.0,
        awa_settle_seconds: int = 30,
    ) -> None:
        self.hz = hz
        self.buffer_seconds = buffer_seconds
        self.pre_window = pre_window
        self.post_window = post_window
        self.twd_sigma_max = twd_sigma_max
        self.bsp_min = bsp_min
        self.awa_settle_sigma = awa_settle_sigma
        self.awa_settle_seconds = awa_settle_seconds

        # Rolling buffer at 1 Hz (downsampled from pipeline rate)
        self._buffer: deque[dict] = deque(maxlen=buffer_seconds)

        # Downsample counter: emit one sample every `hz` calls
        self._ds_counter = 0

        # State machine: "waiting" or "post_tack"
        self.state = "waiting"

        # Last AWA sign seen (True = positive, False = negative, None = unknown)
        self._last_awa_positive: bool | None = None

        # Snapshot of pre-tack buffer (list copy taken at tack detection)
        self._pre_snapshot: list[dict] = []

        # Post-tack accumulator
        self._post_buffer: list[dict] = []

        # Sail config at tack time
        self._pre_sail_config: str | None = None

        # Last result for inspection in tests
        self.last_result: str | None = None

    # ── public API ──────────────────────────────────────────────────

    def update(
        self,
        twd: float,
        awa_corrected: float,
        heel: float,
        bsp: float,
        sail_config: str,
    ) -> Optional[Tuple[float, float, float, str]]:
        """Feed one sample at pipeline rate.

        Returns (residual, mean_awa, mean_heel, sail_config) when a valid
        maneuver is evaluated, None otherwise.
        """
        # Downsample to 1 Hz
        self._ds_counter += 1
        if self._ds_counter < self.hz:
            return None
        self._ds_counter = 0

        sample = {
            "twd": twd,
            "awa": awa_corrected,
            "heel": heel,
            "bsp": bsp,
            "sail": sail_config,
        }

        awa_positive = awa_corrected >= 0

        if self.state == "waiting":
            self._buffer.append(sample)

            # Detect tack: AWA sign change
            if self._last_awa_positive is not None and awa_positive != self._last_awa_positive:
                # Snapshot pre-tack data
                self._pre_snapshot = list(self._buffer)
                self._post_buffer = []
                self._pre_sail_config = sail_config
                self.state = "post_tack"

            self._last_awa_positive = awa_positive
            return None

        elif self.state == "post_tack":
            self._post_buffer.append(sample)
            self._last_awa_positive = awa_positive

            # Check if AWA has settled and we have enough post-tack data
            if len(self._post_buffer) >= max(self.awa_settle_seconds, self.post_window):
                recent_awa = [s["awa"] for s in self._post_buffer[-self.awa_settle_seconds:]]
                if _std(recent_awa) < self.awa_settle_sigma:
                    # AWA settled -- evaluate maneuver
                    result = self._evaluate()
                    # Reset to waiting
                    self.state = "waiting"
                    # Seed buffer with post-tack data for next maneuver
                    self._buffer.clear()
                    for s in self._post_buffer:
                        self._buffer.append(s)
                    self._post_buffer = []
                    self._pre_snapshot = []
                    return result

            return None

        return None

    # ── evaluation ──────────────────────────────────────────────────

    def _evaluate(self) -> Optional[Tuple[float, float, float, str]]:
        """Check validity and compute residual."""
        pre = self._pre_snapshot
        post = self._post_buffer

        # Window duration checks
        if len(pre) < self.pre_window:
            self.last_result = "rejected_pre_short"
            return None
        if len(post) < self.post_window:
            self.last_result = "rejected_post_short"
            return None

        pre_slice = pre[-self.pre_window:]
        post_slice = post[:self.post_window]

        # TWD stability pre-maneuver
        pre_twd = [s["twd"] for s in pre_slice]
        if _angle_std(pre_twd) > self.twd_sigma_max:
            self.last_result = "rejected_twd_unstable_pre"
            return None

        # TWD stability post-maneuver
        post_twd = [s["twd"] for s in post_slice]
        if _angle_std(post_twd) > self.twd_sigma_max:
            self.last_result = "rejected_twd_unstable_post"
            return None

        # Sufficient BSP pre-maneuver
        pre_bsp = [s["bsp"] for s in pre_slice]
        if sum(pre_bsp) / len(pre_bsp) < self.bsp_min:
            self.last_result = "rejected_low_bsp"
            return None

        # No sail config change
        post_sails = {s["sail"] for s in post_slice}
        if len(post_sails) != 1 or self._pre_sail_config not in post_sails:
            self.last_result = "rejected_sail_change"
            return None

        # Compute residual
        twd_pre_mean = _angle_mean(pre_twd)
        twd_post_mean = _angle_mean(post_twd)
        residual = _angle_diff(twd_post_mean, twd_pre_mean) / 2.0

        # Mean AWA and heel from post-tack window (the corrected side)
        mean_awa = sum(s["awa"] for s in post_slice) / len(post_slice)
        mean_heel = sum(abs(s["heel"]) for s in post_slice) / len(post_slice)

        self.last_result = "updated"
        return (residual, mean_awa, mean_heel, self._pre_sail_config)
