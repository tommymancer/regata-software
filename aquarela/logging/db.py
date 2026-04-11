"""SQLite database — schema and helpers.

Phase 4: marks table (used by race/marks.py for persistent storage later).
Phase 5: sessions + trim_snapshots tables.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/aquarela.db")


def get_connection() -> sqlite3.Connection:
    """Open (or create) the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS marks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            lat        REAL NOT NULL,
            lon        REAL NOT NULL,
            mark_type  TEXT DEFAULT 'generic'
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time  TEXT NOT NULL,
            end_time    TEXT,
            session_type TEXT DEFAULT 'training',
            notes       TEXT DEFAULT '',
            csv_file    TEXT
        );

        CREATE TABLE IF NOT EXISTS trim_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER REFERENCES sessions(id),
            timestamp   TEXT NOT NULL,
            tws_kt      REAL,
            twa_deg     REAL,
            bsp_kt      REAL,
            perf_pct    REAL,
            cunningham  TEXT,
            outhaul     TEXT,
            vang        TEXT,
            jib_lead    TEXT,
            jib_halyard TEXT,
            traveller   TEXT,
            forestay    TEXT,
            notes       TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS polar_samples (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER REFERENCES sessions(id),
            timestamp   TEXT NOT NULL,
            tws_bin     INTEGER NOT NULL,
            twa_bin     REAL NOT NULL,
            bsp_kt      REAL NOT NULL,
            tws_kt      REAL NOT NULL,
            twa_deg     REAL NOT NULL,
            perf_pct    REAL,
            sail_type   TEXT NOT NULL DEFAULT 'racing_white'
        );

        CREATE INDEX IF NOT EXISTS idx_polar_samples_bin
            ON polar_samples(tws_bin, twa_bin);

        CREATE TABLE IF NOT EXISTS polar_learned (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tws_bin      INTEGER NOT NULL,
            twa_bin      REAL NOT NULL,
            bsp_p95      REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            updated_at   TEXT NOT NULL,
            sail_type    TEXT NOT NULL DEFAULT 'racing_white',
            UNIQUE(sail_type, tws_bin, twa_bin)
        );

        CREATE TABLE IF NOT EXISTS maneuvers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER REFERENCES sessions(id),
            maneuver_type   TEXT NOT NULL,
            wall_time       TEXT,
            lat             REAL,
            lon             REAL,
            bsp_before      REAL,
            bsp_min         REAL,
            bsp_after       REAL,
            recovery_secs   REAL,
            vmg_before      REAL,
            vmg_loss_nm     REAL,
            vmc_before      REAL,
            vmc_loss_nm     REAL,
            hdg_before      REAL,
            hdg_after       REAL
        );

        CREATE INDEX IF NOT EXISTS idx_maneuvers_session
            ON maneuvers(session_id);
    """)
    conn.commit()

    # Migration: add polar_included flag to sessions (default 1 = included)
    try:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN polar_included INTEGER DEFAULT 1"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add sea_state column to trim_snapshots
    try:
        conn.execute(
            "ALTER TABLE trim_snapshots ADD COLUMN sea_state TEXT DEFAULT ''"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add sail_type column to polar_samples
    try:
        conn.execute(
            "ALTER TABLE polar_samples ADD COLUMN sail_type TEXT NOT NULL DEFAULT 'racing_white'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add sail_type column to polar_learned
    try:
        conn.execute(
            "ALTER TABLE polar_learned ADD COLUMN sail_type TEXT NOT NULL DEFAULT 'racing_white'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add sail_type indexes (after columns exist)
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_polar_samples_sail ON polar_samples(sail_type, tws_bin, twa_bin)")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_polar_learned_sail_bin ON polar_learned(sail_type, tws_bin, twa_bin)")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Migration: map old sail_type values to new config keys
    _OLD_TO_NEW = {
        "training_white": "main_1__genoa",
        "racing_white": "main_1__genoa",
        "racing_gennaker": "main_1__gennaker",
        "racing_gennaker_runner": "main_1__gennaker",
    }
    for _old, _new in _OLD_TO_NEW.items():
        try:
            conn.execute(
                "UPDATE polar_samples SET sail_type = ? WHERE sail_type = ?",
                (_new, _old),
            )
            conn.execute(
                "UPDATE polar_learned SET sail_type = ? WHERE sail_type = ?",
                (_new, _old),
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass
