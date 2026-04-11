"""Session manager — auto-start/stop sailing sessions.

Auto-start: (BSP > 0.5 kt OR SOG > 0.5 kt) for 10 consecutive seconds.
Auto-stop:  BSP < 0.3 kt AND SOG < 0.3 kt for 30 minutes.
NMEA guard: if no CAN frames for 30s, force-stop the session.

Each session records start/end time, type, notes, and CSV file path
in SQLite.
"""

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..logging.db import get_connection, init_schema


@dataclass
class Session:
    """A recorded sailing session."""

    id: Optional[int] = None
    start_time: str = ""
    end_time: Optional[str] = None
    session_type: str = "training"
    notes: str = ""
    csv_file: Optional[str] = None
    polar_included: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "session_type": self.session_type,
            "notes": self.notes,
            "csv_file": self.csv_file,
            "polar_included": self.polar_included,
        }


class SessionManager:
    """Manages sailing session lifecycle.

    Call `update(bsp, sog)` once per pipeline step.  When a session
    auto-starts or auto-stops, the corresponding callback fires.
    """

    START_SPEED_THRESHOLD: float = 0.5  # kt — BSP or SOG to start
    STOP_SPEED_THRESHOLD: float = 0.3   # kt — both BSP and SOG below to stop
    START_DURATION_SECS: float = 10.0
    STOP_DURATION_SECS: float = 1800.0  # 30 minutes
    NMEA_TIMEOUT_SECS: float = 30.0     # no CAN frames → force stop

    def __init__(self, hz: int = 10, db_path: Optional[str] = None) -> None:
        self._hz = hz
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.active_session: Optional[Session] = None
        self._moving_since: Optional[float] = None
        self._stopped_since: Optional[float] = None
        self._last_nmea_time: Optional[float] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._db_path:
                self._conn = sqlite3.connect(self._db_path)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
            else:
                self._conn = get_connection()
            init_schema(self._conn)
        return self._conn

    def notify_nmea_frame(self) -> None:
        """Call whenever a CAN/NMEA frame is received."""
        self._last_nmea_time = time.monotonic()

    def update(
        self,
        bsp: Optional[float],
        sog: Optional[float] = None,
    ) -> Optional[str]:
        """Feed current BSP and SOG; returns event string or None.

        Returns:
            "started"  — new session just began
            "stopped"  — session just ended
            None       — no state change
        """
        now = time.monotonic()

        # NMEA guard: no frames for 30s → force stop
        if self.active_session is not None and self._last_nmea_time is not None:
            if now - self._last_nmea_time > self.NMEA_TIMEOUT_SECS:
                self._stop_session()
                return "stopped"

        bsp_val = bsp if bsp is not None else 0.0
        sog_val = sog if sog is not None else 0.0

        # Start: either BSP or SOG above threshold
        is_moving_start = (
            bsp_val >= self.START_SPEED_THRESHOLD
            or sog_val >= self.START_SPEED_THRESHOLD
        )
        # Stop: both BSP and SOG below threshold
        is_moving_stop = (
            bsp_val >= self.STOP_SPEED_THRESHOLD
            or sog_val >= self.STOP_SPEED_THRESHOLD
        )

        if self.active_session is None:
            # Not in session — check for auto-start
            if is_moving_start:
                if self._moving_since is None:
                    self._moving_since = now
                elif now - self._moving_since >= self.START_DURATION_SECS:
                    self._start_session()
                    return "started"
            else:
                self._moving_since = None
        else:
            # In session — check for auto-stop
            if is_moving_stop:
                self._stopped_since = None
            else:
                if self._stopped_since is None:
                    self._stopped_since = now
                elif now - self._stopped_since >= self.STOP_DURATION_SECS:
                    self._stop_session()
                    return "stopped"

        return None

    def _start_session(self) -> None:
        """Create a new session in SQLite."""
        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO sessions (start_time, session_type) VALUES (?, ?)",
            (now_iso, "training"),
        )
        conn.commit()
        self.active_session = Session(
            id=cur.lastrowid,
            start_time=now_iso,
            session_type="training",
        )
        self._stopped_since = None

    def _stop_session(self) -> None:
        """Close the active session in SQLite."""
        if self.active_session is None:
            return
        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE sessions SET end_time = ? WHERE id = ?",
            (now_iso, self.active_session.id),
        )
        conn.commit()
        self.active_session.end_time = now_iso
        self.active_session = None
        self._moving_since = None

    def force_start(self, session_type: str = "training") -> Session:
        """Manually start a session."""
        if self.active_session is not None:
            self._stop_session()
        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO sessions (start_time, session_type) VALUES (?, ?)",
            (now_iso, session_type),
        )
        conn.commit()
        self.active_session = Session(
            id=cur.lastrowid,
            start_time=now_iso,
            session_type=session_type,
        )
        self._stopped_since = None
        return self.active_session

    def force_stop(self) -> Optional[Session]:
        """Manually stop the active session."""
        if self.active_session is None:
            return None
        session = self.active_session
        self._stop_session()
        return session

    def set_csv_file(self, csv_path: str) -> None:
        """Associate a CSV file with the active session."""
        if self.active_session is None:
            return
        conn = self._get_conn()
        conn.execute(
            "UPDATE sessions SET csv_file = ? WHERE id = ?",
            (csv_path, self.active_session.id),
        )
        conn.commit()
        self.active_session.csv_file = csv_path

    def list_sessions(self, limit: int = 20) -> List[Session]:
        """List recent sessions, newest first."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY start_time DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def get_session(self, session_id: int) -> Optional[Session]:
        """Fetch a single session by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def set_polar_included(self, session_id: int, included: bool) -> None:
        """Toggle whether a session's polar data is used in rebuilds."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE sessions SET polar_included = ? WHERE id = ?",
            (1 if included else 0, session_id),
        )
        conn.commit()

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        # polar_included may not exist in old DBs before migration runs
        try:
            polar_included = bool(row["polar_included"])
        except (IndexError, KeyError):
            polar_included = True
        return Session(
            id=row["id"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            session_type=row["session_type"] or "training",
            notes=row["notes"] or "",
            csv_file=row["csv_file"],
            polar_included=polar_included,
        )

    def reset(self) -> None:
        """Reset manager state (doesn't clear DB)."""
        self.active_session = None
        self._moving_since = None
        self._stopped_since = None
        self._last_nmea_time = None
