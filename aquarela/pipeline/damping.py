"""Per-field moving-average damping filters.

Each field gets an independent circular buffer.  Angular quantities (TWD)
use vector averaging to handle the 360°/0° wrap correctly.

Damping windows are configurable per field in aquarela-config.json.
"""

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

from .state import BoatState


@dataclass
class _AngleBuffer:
    """Circular buffer for angle averaging using sin/cos components."""
    sin_sum: float = 0.0
    cos_sum: float = 0.0
    values: Deque = field(default_factory=deque)
    max_len: int = 100

    def push(self, angle_deg: float) -> float:
        rad = math.radians(angle_deg)
        s = math.sin(rad)
        c = math.cos(rad)
        self.sin_sum += s
        self.cos_sum += c
        self.values.append((s, c))
        if len(self.values) > self.max_len:
            old_s, old_c = self.values.popleft()
            self.sin_sum -= old_s
            self.cos_sum -= old_c
        n = len(self.values)
        return math.degrees(math.atan2(self.sin_sum / n, self.cos_sum / n)) % 360


@dataclass
class ScalarBuffer:
    """Circular buffer for simple moving average."""
    total: float = 0.0
    values: Deque = field(default_factory=deque)
    max_len: int = 100

    _push_count: int = 0

    def push(self, value: float) -> float:
        self.total += value
        self.values.append(value)
        if len(self.values) > self.max_len:
            self.total -= self.values.popleft()
        # Periodically recompute sum from scratch to prevent float drift
        self._push_count += 1
        if self._push_count >= 10000:
            self._push_count = 0
            self.total = sum(self.values)
        return self.total / len(self.values)


# Backward-compatible alias
_ScalarBuffer = ScalarBuffer


class DampingFilters:
    """Collection of per-field damping filters.

    Args:
        windows: dict mapping field names to damping window in seconds.
        hz: pipeline sample rate (used to compute buffer sizes).
    """

    def __init__(self, windows: Dict[str, float], hz: int = 10):
        self._filters: Dict[str, _ScalarBuffer | _AngleBuffer] = {}
        for name, window_s in windows.items():
            buf_len = max(1, int(window_s * hz))
            if name == "twd_deg":
                self._filters[name] = _AngleBuffer(max_len=buf_len)
            else:
                self._filters[name] = ScalarBuffer(max_len=buf_len)

    def apply(self, state: BoatState) -> None:
        """Apply damping to the relevant fields of *state* in-place."""
        field_map = {
            "tws_kt": "tws_kt",
            "twd_deg": "twd_deg",
            "bsp_kt": "bsp_kt",
            "vmg_kt": "vmg_kt",
        }

        for filter_name, state_field in field_map.items():
            if filter_name not in self._filters:
                continue
            value = getattr(state, state_field, None)
            if value is None:
                continue
            damped = self._filters[filter_name].push(value)
            setattr(state, state_field, damped)
