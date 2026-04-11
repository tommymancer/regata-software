"""Njord Analytics-compatible CSV logger.

Writes session data at 2 Hz (decimated from the 10 Hz pipeline).
The first 18 columns are the Njord-compatible base format.
Additional columns follow for richer analysis without breaking Njord import.

CSV format (Njord base):
  Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG
Extended columns:
  VMG,VMC,Leeway,WaterTemp,TargetTWA,TargetBSP,TargetVMG,VMGPerf,
  AWACorrected,AWSCorrected,UpwashOffset,HeelCorrection,
  SailConfig,CourseOffset,LineBias,DistToLine,
  LaylinePort,LaylineStbd,DistPortLayline,DistStbdLayline,
  DTW,RaceState,RaceTimer,GPSSats
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TextIO

from ..pipeline.state import BoatState

CSV_HEADER = (
    "Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,"
    "TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG,"
    "VMG,VMC,Leeway,WaterTemp,TargetTWA,TargetBSP,TargetVMG,VMGPerf,"
    "AWACorrected,AWSCorrected,UpwashOffset,HeelCorrection,"
    "SailConfig,CourseOffset,LineBias,DistToLine,"
    "LaylinePort,LaylineStbd,DistPortLayline,DistStbdLayline,"
    "DTW,RaceState,RaceTimer,GPSSats\n"
)


def _fmt(value: Optional[float], decimals: int = 2) -> str:
    """Format a float for CSV output, or empty string if None."""
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _fmt_str(value: Optional[str]) -> str:
    """Format a string for CSV output, or empty string if None."""
    return value or ""


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

        # Njord-compatible base (18 columns)
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
            f"{_fmt(state.btw_deg, 1)},"
            # Extended columns
            f"{_fmt(state.vmg_kt)},"
            f"{_fmt(state.vmc_kt)},"
            f"{_fmt(state.leeway_deg, 1)},"
            f"{_fmt(state.water_temp_c, 1)},"
            f"{_fmt(state.target_twa_deg, 1)},"
            f"{_fmt(state.target_bsp_kt)},"
            f"{_fmt(state.target_vmg_kt)},"
            f"{_fmt(state.vmg_perf_pct, 1)},"
            f"{_fmt(state.awa_corrected_deg, 1)},"
            f"{_fmt(state.aws_corrected_kt)},"
            f"{_fmt(state.upwash_offset_deg, 2)},"
            f"{_fmt(state.heel_correction_deg, 2)},"
            f"{_fmt_str(state.active_sail_config)},"
            f"{_fmt(state.course_offset_deg, 1)},"
            f"{_fmt(state.line_bias_deg, 1)},"
            f"{_fmt(state.dist_to_line_nm, 4)},"
            f"{_fmt(state.layline_port_deg, 1)},"
            f"{_fmt(state.layline_stbd_deg, 1)},"
            f"{_fmt(state.dist_to_port_layline_nm, 3)},"
            f"{_fmt(state.dist_to_stbd_layline_nm, 3)},"
            f"{_fmt(state.dtw_nm, 3)},"
            f"{_fmt_str(state.race_state)},"
            f"{_fmt(state.race_timer_secs, 0)},"
            f"{_fmt(state.gps_num_sats, 0)}\n"
        )

        self._file.write(row)
        # Flush every row for crash safety (power loss during sailing)
        # fsync every 10 rows (5 seconds at 2 Hz) to avoid SD card I/O bottleneck
        self._file.flush()
        if self._tick_count % (self._decimation * 10) == 0:
            os.fsync(self._file.fileno())
