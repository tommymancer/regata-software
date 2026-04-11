"""Njord Analytics-compatible CSV logger.

Writes the exact 18-column header from the Aquarela Njord CSV Spec at 2 Hz
(decimated from the 10 Hz pipeline).  Each sailing session gets its own file
under data/sessions/.

CSV format:
  Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TextIO

from ..pipeline.state import BoatState

CSV_HEADER = (
    "Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,"
    "TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG\n"
)


def _fmt(value: Optional[float], decimals: int = 2) -> str:
    """Format a float for CSV output, or empty string if None."""
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


class CsvLogger:
    """Logs BoatState to Njord-compatible CSV files.

    Args:
        output_dir: directory for session CSV files.
        csv_rate_hz: target write rate (rows per second).
        pipeline_hz: pipeline tick rate (used for decimation).
    """

    def __init__(
        self,
        output_dir: str = "data/sessions",
        csv_rate_hz: int = 2,
        pipeline_hz: int = 10,
    ):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._decimation = max(1, pipeline_hz // csv_rate_hz)
        self._tick_count = 0
        self._file: Optional[TextIO] = None
        self._file_path: Optional[Path] = None

    @property
    def is_open(self) -> bool:
        return self._file is not None

    @property
    def file_path(self) -> Optional[Path]:
        return self._file_path

    def start_session(self, label: Optional[str] = None) -> Path:
        """Open a new CSV file for the current session.

        Uses a boot-unique suffix to prevent filename collisions when the
        system clock is wrong (no RTC).  Never opens an existing file —
        if a name collision is somehow still possible, appends _2, _3, etc.
        """
        self.stop_session()
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Add monotonic boot time (seconds since boot) as a collision guard.
        # Two boots will never produce the same boot_secs at the same wall-clock.
        boot_secs = int(time.monotonic())
        base = f"{ts}_b{boot_secs}_{label}" if label else f"{ts}_b{boot_secs}"
        name = f"{base}.csv"
        self._file_path = self._output_dir / name
        # Extra safety: never truncate an existing file
        counter = 2
        while self._file_path.exists():
            self._file_path = self._output_dir / f"{base}_{counter}.csv"
            counter += 1
        self._file = open(self._file_path, "x", newline="")
        self._file.write(CSV_HEADER)
        self._file.flush()
        self._tick_count = 0
        return self._file_path

    def stop_session(self) -> None:
        """Flush and close the current CSV file."""
        if self._file is not None:
            self._file.flush()
            os.fsync(self._file.fileno())
            self._file.close()
            self._file = None

    def log(self, state: BoatState) -> None:
        """Write a row if it's time (decimation from pipeline Hz to CSV Hz).

        Called once per pipeline tick.  Writes every Nth tick.
        """
        if self._file is None:
            return

        self._tick_count += 1
        if self._tick_count % self._decimation != 0:
            return

        ts = state.timestamp.strftime("%Y-%m-%dT%H:%M:%S.") + \
             f"{state.timestamp.microsecond // 1000:03d}Z"

        row = (
            f"{ts},"
            f"{_fmt(state.lat, 7)},"
            f"{_fmt(state.lon, 7)},"
            f"{_fmt(state.sog_kt)},"
            f"{_fmt(state.cog_deg, 1)},"
            f"{_fmt(state.heading_mag, 1)},"
            f"{_fmt(state.bsp_kt)},"
            f"{_fmt(state.awa_deg, 1)},"
            f"{_fmt(state.aws_kt)},"
            f"{_fmt(state.twa_deg, 1)},"
            f"{_fmt(state.tws_kt)},"
            f"{_fmt(state.twd_deg, 1)},"
            f"{_fmt(state.heel_deg, 1)},"
            f"{_fmt(state.trim_deg, 1)},"
            f"{_fmt(state.depth_m)},"
            f"{_fmt(state.magnetic_variation, 1)},"
            f"{_fmt(state.perf_pct, 1)},"
            f"{_fmt(state.btw_deg, 1)}\n"
        )

        self._file.write(row)
        # Flush every row for crash safety (power loss during sailing)
        # fsync every 10 rows (5 seconds at 2 Hz) to avoid SD card I/O bottleneck
        self._file.flush()
        if self._tick_count % (self._decimation * 10) == 0:
            os.fsync(self._file.fileno())
