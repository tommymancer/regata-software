"""Trim book — CRUD for sail trim snapshots + best-trim query.

Stores trim settings (cunningham, outhaul, vang, jib lead, jib halyard,
traveller, forestay) together with conditions (TWS, TWA) and performance
(BSP, PERF%).  The "best trim" query finds the highest-performing snapshot
for given conditions.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..logging.db import get_connection, init_schema


@dataclass
class TrimSnapshot:
    """A single trim snapshot with conditions and settings."""

    id: Optional[int] = None
    session_id: Optional[int] = None
    timestamp: str = ""
    # Conditions
    tws_kt: Optional[float] = None
    twa_deg: Optional[float] = None
    bsp_kt: Optional[float] = None
    perf_pct: Optional[float] = None
    # Sail controls
    cunningham: str = ""
    outhaul: str = ""
    vang: str = ""
    jib_lead: str = ""
    jib_halyard: str = ""
    traveller: str = ""
    forestay: str = ""
    notes: str = ""
    sea_state: str = ""  # "flat", "choppy", "rough"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "tws_kt": self.tws_kt,
            "twa_deg": self.twa_deg,
            "bsp_kt": self.bsp_kt,
            "perf_pct": self.perf_pct,
            "cunningham": self.cunningham,
            "outhaul": self.outhaul,
            "vang": self.vang,
            "jib_lead": self.jib_lead,
            "jib_halyard": self.jib_halyard,
            "traveller": self.traveller,
            "forestay": self.forestay,
            "notes": self.notes,
            "sea_state": self.sea_state,
        }


class TrimBook:
    """In-memory trim book backed by SQLite."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._conn: Optional[sqlite3.Connection] = None
        self._db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._db_path:
                import sqlite3 as _s

                self._conn = _s.connect(self._db_path)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
            else:
                self._conn = get_connection()
            init_schema(self._conn)
        return self._conn

    def save(self, snap: TrimSnapshot) -> int:
        """Insert a trim snapshot, return its ID."""
        conn = self._get_conn()
        if not snap.timestamp:
            snap.timestamp = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """INSERT INTO trim_snapshots
               (session_id, timestamp, tws_kt, twa_deg, bsp_kt, perf_pct,
                cunningham, outhaul, vang, jib_lead, jib_halyard,
                traveller, forestay, notes, sea_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                snap.session_id,
                snap.timestamp,
                snap.tws_kt,
                snap.twa_deg,
                snap.bsp_kt,
                snap.perf_pct,
                snap.cunningham,
                snap.outhaul,
                snap.vang,
                snap.jib_lead,
                snap.jib_halyard,
                snap.traveller,
                snap.forestay,
                snap.notes,
                snap.sea_state,
            ),
        )
        conn.commit()
        snap.id = cur.lastrowid
        return snap.id

    def get(self, snap_id: int) -> Optional[TrimSnapshot]:
        """Fetch a single snapshot by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM trim_snapshots WHERE id = ?", (snap_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_snap(row)

    def delete(self, snap_id: int) -> bool:
        """Delete a snapshot by ID."""
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM trim_snapshots WHERE id = ?", (snap_id,)
        )
        conn.commit()
        return cur.rowcount > 0

    def list_all(self, limit: int = 50) -> List[TrimSnapshot]:
        """List recent snapshots, newest first."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM trim_snapshots ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_snap(r) for r in rows]

    def best_for_conditions(
        self,
        tws_kt: float,
        twa_deg: float,
        tws_tolerance: float = 3.0,
        twa_tolerance: float = 10.0,
        sea_state: str = "",
    ) -> Optional[TrimSnapshot]:
        """Find the best-performing snapshot near given TWS/TWA.

        Searches for snapshots where TWS and |TWA| are within tolerance
        of the query values.  Returns the one with the highest PERF%.
        Uses absolute TWA for matching (port/stbd equivalent).
        Optionally filters by sea_state when non-empty.
        """
        conn = self._get_conn()
        abs_twa = abs(twa_deg)
        sql = """SELECT * FROM trim_snapshots
               WHERE tws_kt BETWEEN ? AND ?
                 AND ABS(twa_deg) BETWEEN ? AND ?
                 AND perf_pct IS NOT NULL"""
        params: list = [
            tws_kt - tws_tolerance,
            tws_kt + tws_tolerance,
            abs_twa - twa_tolerance,
            abs_twa + twa_tolerance,
        ]
        if sea_state:
            sql += "\n                 AND sea_state = ?"
            params.append(sea_state)
        sql += "\n               ORDER BY perf_pct DESC\n               LIMIT 1"
        rows = conn.execute(sql, params).fetchall()
        if not rows:
            return None
        return self._row_to_snap(rows[0])

    def _row_to_snap(self, row: sqlite3.Row) -> TrimSnapshot:
        return TrimSnapshot(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=row["timestamp"],
            tws_kt=row["tws_kt"],
            twa_deg=row["twa_deg"],
            bsp_kt=row["bsp_kt"],
            perf_pct=row["perf_pct"],
            cunningham=row["cunningham"] or "",
            outhaul=row["outhaul"] or "",
            vang=row["vang"] or "",
            jib_lead=row["jib_lead"] or "",
            jib_halyard=row["jib_halyard"] or "",
            traveller=row["traveller"] or "",
            forestay=row["forestay"] or "",
            notes=row["notes"] or "",
            sea_state=row["sea_state"] or "",
        )
