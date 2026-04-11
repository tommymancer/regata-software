"""Maneuver detector — tack and gybe detection with loss metrics.

Detection rules:
  Tack:  HDG changes > 60° within 15 s while TWA sign flips (port↔stbd)
  Gybe:  HDG changes > 30° within 15 s while |TWA| > 90° (downwind)

Loss metrics per maneuver:
  - bsp_before:     average BSP in 5 s before entry
  - bsp_min:        minimum BSP during maneuver
  - bsp_after:      average BSP in 5 s after exit
  - recovery_secs:  seconds from exit until BSP recovers to 90% of bsp_before
  - vmg_loss_nm:    estimated VMG loss vs straight-line sailing (NM)
  - vmc_loss_nm:    estimated VMC loss toward active mark (NM, if mark available)
"""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional


@dataclass
class ManeuverEvent:
    """Recorded tack or gybe with metrics."""

    maneuver_type: str  # "tack" or "gybe"
    entry_time: float  # monotonic timestamp
    exit_time: float = 0.0
    wall_time: Optional[str] = None  # ISO 8601
    lat: Optional[float] = None
    lon: Optional[float] = None
    bsp_before: float = 0.0
    bsp_min: float = 999.0
    bsp_after: float = 0.0
    recovery_secs: Optional[float] = None
    vmg_before: Optional[float] = None
    vmg_loss_nm: Optional[float] = None
    vmc_before: Optional[float] = None
    vmc_loss_nm: Optional[float] = None
    hdg_before: float = 0.0
    hdg_after: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "type": self.maneuver_type,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "wall_time": self.wall_time,
            "lat": self.lat,
            "lon": self.lon,
            "bsp_before": round(self.bsp_before, 2),
            "bsp_min": round(self.bsp_min, 2),
            "bsp_after": round(self.bsp_after, 2),
            "recovery_secs": (
                round(self.recovery_secs, 1) if self.recovery_secs is not None else None
            ),
            "vmg_before": (
                round(self.vmg_before, 2) if self.vmg_before is not None else None
            ),
            "vmg_loss_nm": (
                round(self.vmg_loss_nm, 4) if self.vmg_loss_nm is not None else None
            ),
            "vmc_before": (
                round(self.vmc_before, 2) if self.vmc_before is not None else None
            ),
            "vmc_loss_nm": (
                round(self.vmc_loss_nm, 4) if self.vmc_loss_nm is not None else None
            ),
            "hdg_before": round(self.hdg_before, 1),
            "hdg_after": round(self.hdg_after, 1),
        }


@dataclass
class _Sample:
    """Pipeline sample for the sliding window."""

    t: float        # monotonic time
    hdg: float      # heading degrees
    twa: float      # signed TWA
    bsp: float      # boat speed
    sog: float      # speed over ground
    cog: float      # course over ground
    brg: Optional[float]  # bearing to active mark (None if no mark)
    lat: Optional[float]
    lon: Optional[float]
    wall_time: Optional[str]


class ManeuverDetector:
    """Detects tacks and gybes from the pipeline stream.

    Call `update()` once per pipeline step.  Completed maneuvers
    are appended to `events`.
    """

    WINDOW_SECS: float = 15.0  # look-back for heading change
    TACK_HDG_THRESHOLD: float = 60.0
    GYBE_HDG_THRESHOLD: float = 30.0
    METRIC_WINDOW: float = 5.0  # seconds for BSP averaging
    RECOVERY_THRESHOLD: float = 0.90  # 90% of pre-maneuver BSP
    COOLDOWN_SECS: float = 10.0  # min gap between detections

    def __init__(self, hz: int = 10) -> None:
        self._hz = hz
        self._window: Deque[_Sample] = deque()
        self.events: List[ManeuverEvent] = []
        self._active: Optional[ManeuverEvent] = None
        self._post_samples: List[_Sample] = []
        self._last_detection: float = 0.0

    @property
    def in_maneuver(self) -> bool:
        """True if a maneuver is currently being tracked."""
        return self._active is not None

    def update(
        self,
        heading: Optional[float],
        twa: Optional[float],
        bsp: Optional[float],
        sog: Optional[float] = None,
        cog: Optional[float] = None,
        brg_to_mark: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        wall_time: Optional[str] = None,
    ) -> Optional[ManeuverEvent]:
        """Feed a pipeline step; returns a completed ManeuverEvent or None."""
        if heading is None or twa is None or bsp is None:
            return None

        now = time.monotonic()
        sample = _Sample(
            t=now, hdg=heading, twa=twa, bsp=bsp,
            sog=sog or 0.0, cog=cog or 0.0,
            brg=brg_to_mark, lat=lat, lon=lon, wall_time=wall_time,
        )
        self._window.append(sample)

        cutoff = now - self.WINDOW_SECS
        while self._window and self._window[0].t < cutoff:
            self._window.popleft()

        if self._active is not None:
            return self._track_recovery(sample, now)

        return self._detect(sample, now)

    def _detect(self, current: _Sample, now: float) -> Optional[ManeuverEvent]:
        """Look for a tack or gybe in the sliding window."""
        if now - self._last_detection < self.COOLDOWN_SECS:
            return None

        if len(self._window) < 2:
            return None

        oldest = self._window[0]
        hdg_delta = self._heading_delta(oldest.hdg, current.hdg)

        # Check for tack: large HDG change + TWA sign flip
        twa_sign_flipped = (oldest.twa * current.twa) < 0
        if hdg_delta >= self.TACK_HDG_THRESHOLD and twa_sign_flipped:
            return self._start_maneuver("tack", now, oldest, current)

        # Check for gybe: moderate HDG change while downwind
        if (
            hdg_delta >= self.GYBE_HDG_THRESHOLD
            and abs(oldest.twa) > 90
            and abs(current.twa) > 90
            and twa_sign_flipped
        ):
            return self._start_maneuver("gybe", now, oldest, current)

        return None

    def _start_maneuver(
        self,
        maneuver_type: str,
        now: float,
        oldest: _Sample,
        current: _Sample,
    ) -> None:
        """Begin tracking a new maneuver."""
        pre_samples = [
            s for s in self._window
            if s.t < now - (now - oldest.t) / 2
        ]
        bsp_before = (
            sum(s.bsp for s in pre_samples) / len(pre_samples)
            if pre_samples else oldest.bsp
        )
        bsp_min = min(s.bsp for s in self._window)

        # VMG before: average abs(BSP * cos(TWA)) in pre-samples
        vmg_before = None
        if pre_samples:
            vmgs = [abs(s.bsp * math.cos(math.radians(s.twa))) for s in pre_samples]
            vmg_before = sum(vmgs) / len(vmgs)

        # VMC before: average SOG * cos(COG - BRG) in pre-samples (if BRG available)
        vmc_before = None
        brg_samples = [s for s in pre_samples if s.brg is not None]
        if brg_samples:
            vmcs = [s.sog * math.cos(math.radians(s.cog - s.brg)) for s in brg_samples]
            vmc_before = sum(vmcs) / len(vmcs)

        self._active = ManeuverEvent(
            maneuver_type=maneuver_type,
            entry_time=oldest.t,
            exit_time=now,
            wall_time=current.wall_time,
            lat=current.lat,
            lon=current.lon,
            bsp_before=bsp_before,
            bsp_min=bsp_min,
            vmg_before=vmg_before,
            vmc_before=vmc_before,
            hdg_before=oldest.hdg,
            hdg_after=current.hdg,
        )
        self._post_samples = []
        self._last_detection = now
        return None

    def _track_recovery(
        self, sample: _Sample, now: float
    ) -> Optional[ManeuverEvent]:
        """Track post-maneuver BSP recovery."""
        assert self._active is not None

        # Update bsp_min if still dropping
        if sample.bsp < self._active.bsp_min:
            self._active.bsp_min = sample.bsp

        self._post_samples.append(sample)
        elapsed = now - self._active.exit_time

        # Check recovery
        target_bsp = self._active.bsp_before * self.RECOVERY_THRESHOLD
        if sample.bsp >= target_bsp and self._active.recovery_secs is None:
            self._active.recovery_secs = elapsed

        # After METRIC_WINDOW seconds post-exit, finalise
        if elapsed >= self.METRIC_WINDOW:
            return self._finalise(now)

        # Safety timeout: 30 seconds max post-tracking
        if elapsed >= 30.0:
            return self._finalise(now)

        return None

    def _finalise(self, now: float) -> ManeuverEvent:
        """Complete the maneuver event and return it."""
        ev = self._active
        assert ev is not None

        if self._post_samples:
            ev.bsp_after = sum(s.bsp for s in self._post_samples) / len(
                self._post_samples
            )

        duration = now - ev.entry_time

        # VMG loss: (vmg_before - avg_vmg_during) * duration / 3600
        all_samples = list(self._window) + self._post_samples
        if ev.vmg_before is not None and all_samples:
            vmgs = [abs(s.bsp * math.cos(math.radians(s.twa))) for s in all_samples]
            avg_vmg = sum(vmgs) / len(vmgs)
            ev.vmg_loss_nm = max(0, (ev.vmg_before - avg_vmg) * duration / 3600.0)

        # VMC loss: (vmc_before - avg_vmc_during) * duration / 3600
        if ev.vmc_before is not None:
            brg_samples = [s for s in all_samples if s.brg is not None]
            if brg_samples:
                vmcs = [s.sog * math.cos(math.radians(s.cog - s.brg)) for s in brg_samples]
                avg_vmc = sum(vmcs) / len(vmcs)
                ev.vmc_loss_nm = max(0, (ev.vmc_before - avg_vmc) * duration / 3600.0)

        if ev.recovery_secs is None:
            ev.recovery_secs = now - ev.exit_time

        self.events.append(ev)
        self._active = None
        self._post_samples = []
        return ev

    @staticmethod
    def _heading_delta(h1: float, h2: float) -> float:
        """Smallest angular difference between two headings."""
        d = abs(h2 - h1) % 360
        return d if d <= 180 else 360 - d

    def get_stats(self) -> Dict:
        """Summary stats for all detected maneuvers."""
        tacks = [e for e in self.events if e.maneuver_type == "tack"]
        gybes = [e for e in self.events if e.maneuver_type == "gybe"]

        def _avg(items, attr):
            vals = [getattr(e, attr) for e in items if getattr(e, attr) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        return {
            "total_tacks": len(tacks),
            "total_gybes": len(gybes),
            "avg_tack_recovery": _avg(tacks, "recovery_secs"),
            "avg_gybe_recovery": _avg(gybes, "recovery_secs"),
            "avg_tack_bsp_min": _avg(tacks, "bsp_min"),
            "avg_gybe_bsp_min": _avg(gybes, "bsp_min"),
            "avg_tack_vmg_loss_nm": _avg(tacks, "vmg_loss_nm"),
            "avg_gybe_vmg_loss_nm": _avg(gybes, "vmg_loss_nm"),
            "avg_tack_vmc_loss_nm": _avg(tacks, "vmc_loss_nm"),
            "avg_gybe_vmc_loss_nm": _avg(gybes, "vmc_loss_nm"),
        }

    def reset(self) -> None:
        """Clear all events and state."""
        self._window.clear()
        self.events.clear()
        self._active = None
        self._post_samples = []
        self._last_detection = 0.0


def persist_maneuver(
    conn: "sqlite3.Connection",
    session_id: int,
    event: ManeuverEvent,
) -> None:
    """Insert a completed maneuver event into the database."""
    conn.execute(
        """INSERT INTO maneuvers
           (session_id, maneuver_type, wall_time, lat, lon,
            bsp_before, bsp_min, bsp_after, recovery_secs,
            vmg_before, vmg_loss_nm, vmc_before, vmc_loss_nm,
            hdg_before, hdg_after)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            event.maneuver_type,
            event.wall_time,
            event.lat,
            event.lon,
            event.bsp_before,
            event.bsp_min,
            event.bsp_after,
            event.recovery_secs,
            event.vmg_before,
            event.vmg_loss_nm,
            event.vmc_before,
            event.vmc_loss_nm,
            event.hdg_before,
            event.hdg_after,
        ),
    )
    conn.commit()


def list_maneuvers_for_session(
    conn: "sqlite3.Connection",
    session_id: int,
) -> list:
    """Retrieve all maneuvers for a given session."""
    cur = conn.execute(
        "SELECT * FROM maneuvers WHERE session_id = ? ORDER BY wall_time",
        (session_id,),
    )
    return [dict(row) for row in cur.fetchall()]
