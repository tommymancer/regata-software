# Android Offline Sessions — Design Spec

## Goal

Add offline session review to the Aquarela Android app. Users can browse past sailing sessions with key stats, maneuver analysis, and a GPS track map — all without needing a connection to the Pi.

## Architecture

Two-tab bottom navigation:

- **Live** — existing WebView connecting to the Pi
- **Sessioni** — native Compose screens backed by a local Room database

Auto-sync downloads new session data whenever the app connects to the Pi.

```
┌──────────────────────────────────┐
│  BottomNav  [ Live | Sessioni ]  │
├───────────┬──────────────────────┤
│ LiveTab   │ SessionsTab          │
│ (WebView) │  SessionListScreen   │
│           │  → SessionDetailScreen│
│           │      StatsCards      │
│           │      ManeuversCard   │
│           │      TrackMap        │
└───────────┴──────────────────────┘
       │
  AutoSyncWorker (on Pi connection)
       │
  ┌────▼─────┐
  │  Room DB  │
  └──────────┘
```

## Prerequisites: Backend Changes

Before the Android work, these backend changes are needed on the Pi:

### 1. Add `Perf` and `BRG` columns to CSV logger

File: `aquarela/logging/csv_logger.py`

- `Perf`: performance percentage. Source: `BoatState.perf_pct`.
- `BRG`: bearing to active mark in degrees (0-360). Source: navigation engine's bearing to active mark. Empty/blank when no mark is active.

### 2. Refactor ManeuverDetector to use VMG/VMC-based loss metrics

File: `aquarela/training/maneuvers.py`

Replace the current BSP-based `distance_lost_nm` with:

- **`vmg_loss_nm`**: distance lost along wind axis = `(vmg_before - vmg_avg_during) * duration / 3600`
  - Where `vmg = abs(BSP * cos(TWA))`
  - `vmg_before`: avg VMG in 5s before entry
  - `vmg_avg_during`: avg VMG during the maneuver window
- **`vmc_loss_nm`** (nullable): distance lost toward active mark = `(vmc_before - vmc_avg_during) * duration / 3600`
  - Where `vmc = SOG * cos(COG - BRG)` (or `BSP * cos(HDG - BRG)`)
  - Only computed when a mark is active (BRG available)
  - `null` when no mark is active

The `ManeuverDetector.update()` method needs additional inputs:
- `twa`: already available
- `sog`: for VMC calculation
- `cog`: for VMC calculation
- `brg_to_mark`: bearing to active mark (nullable)

### 3. Extend ManeuverEvent with lat/lon, wall-clock timestamp, and VMG/VMC fields

File: `aquarela/training/maneuvers.py`

Add to `ManeuverEvent`:
- `wall_time`: ISO 8601 wall-clock timestamp at entry
- `lat`, `lon`: GPS position at entry (from current BoatState)
- `vmg_before`, `vmg_loss_nm`: VMG-based loss metrics
- `vmc_before`, `vmc_loss_nm`: VMC-based loss metrics (nullable)

Remove: `distance_lost_nm` (replaced by vmg_loss_nm / vmc_loss_nm)

### 4. Persist maneuvers to SQLite

Files: `aquarela/logging/db.py`, `aquarela/training/maneuvers.py`

Create a `maneuvers` table in the Pi's SQLite database:

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| session_id | INTEGER FK | |
| maneuver_type | TEXT | "tack" or "gybe" |
| wall_time | TEXT | ISO 8601 |
| lat | REAL | |
| lon | REAL | |
| bsp_before | REAL | |
| bsp_min | REAL | |
| bsp_after | REAL | |
| recovery_secs | REAL | |
| vmg_before | REAL | VMG before maneuver (kt) |
| vmg_loss_nm | REAL | Distance lost on wind axis |
| vmc_before | REAL | VMC before maneuver (kt), nullable |
| vmc_loss_nm | REAL | Distance lost toward mark, nullable |
| hdg_before | REAL | |
| hdg_after | REAL | |

Insert each completed ManeuverEvent into this table, keyed by the active session_id.

### 5. New API endpoint: `GET /api/sessions/{id}/maneuvers`

File: `aquarela/api/maneuvers.py`

Returns the list of persisted maneuvers for a given session_id from the database.

## Database (Room — Android)

### Table: `sessions`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | From backend session id |
| start_time | TEXT | ISO 8601 |
| end_time | TEXT | ISO 8601 |
| session_type | TEXT | "training" |
| notes | TEXT | Nullable |
| duration_secs | INTEGER | Computed from CSV |
| distance_nm | REAL | Sum of haversine segment distances |
| avg_bsp_kt | REAL | Mean BSP from track points |
| max_bsp_kt | REAL | Max BSP from track points |
| avg_tws_kt | REAL | Mean TWS from track points |
| avg_vmg_kt | REAL | Mean VMG across all points |
| avg_vmc_kt | REAL | Mean VMC, nullable (only when BRG available) |
| synced_at | TEXT | When this session was downloaded |

### Table: `track_points`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| session_id | INTEGER FK | References sessions(id) |
| timestamp | TEXT | ISO 8601 |
| lat | REAL | |
| lon | REAL | |
| bsp_kt | REAL | |
| sog_kt | REAL | CSV column: SOG |
| cog_deg | REAL | CSV column: COG |
| perf_pct | REAL | For track coloring |
| hdg_deg | REAL | CSV column: Heading |
| twa_deg | REAL | CSV column: TWA |
| tws_kt | REAL | CSV column: TWS |
| brg_deg | REAL | CSV column: BRG, nullable |

### Table: `maneuvers`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| session_id | INTEGER FK | References sessions(id) |
| maneuver_type | TEXT | "tack" or "gybe" |
| entry_time | TEXT | ISO 8601 |
| lat | REAL | Position at entry |
| lon | REAL | Position at entry |
| bsp_before | REAL | Avg BSP 5s before |
| bsp_min | REAL | Min BSP during |
| bsp_after | REAL | Avg BSP 5s after |
| recovery_secs | REAL | Time to recover 90% BSP |
| vmg_before | REAL | VMG before (kt) |
| vmg_loss_nm | REAL | Distance lost on wind axis |
| vmc_before | REAL | VMC before (kt), nullable |
| vmc_loss_nm | REAL | Distance lost toward mark, nullable |
| hdg_before | REAL | |
| hdg_after | REAL | |

## Sync Strategy

### Trigger

When the existing Pi discovery logic (`onAquarelaFound`) resolves a URL, the sync starts automatically in a background coroutine.

### Flow

1. **Fetch session list**: `GET /api/sessions` — returns all sessions with metadata including `csv_file`.
2. **Filter**: only sessions with `end_time != null` (completed) and `csv_file != null`.
3. **Diff against Room**: compare by `id`. Identify sessions not yet in Room.
4. **For each new session**:
   a. Extract filename from `csv_file` path (e.g. `data/sessions/foo.csv` → `foo.csv`).
   b. Download CSV: `GET /api/logs/{filename}`.
   c. Parse CSV into `track_points` rows. Compute aggregates (duration, distance, avg/max BSP, avg TWS, avg VMG, avg VMC).
   d. Fetch maneuvers: `GET /api/sessions/{id}/maneuvers`.
   e. Insert session + track_points + maneuvers into Room in a single transaction.
   f. Pre-download OSM tiles for the track bounding box (zoom 10-15).
5. Show toast: "N sessioni sincronizzate".

### Error Handling

- If Pi disconnects mid-sync, skip the current session and stop. Already-synced sessions remain intact (each is a complete transaction).
- Failed CSV downloads are logged and skipped; the session will be retried on next connection.

### CSV Format

CSV header after backend changes:

```
Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG
```

Column mapping to `track_points`:
- `Timestamp` → `timestamp`
- `Lat` → `lat`
- `Lon` → `lon`
- `BSP` → `bsp_kt`
- `SOG` → `sog_kt`
- `COG` → `cog_deg`
- `Heading` → `hdg_deg`
- `TWA` → `twa_deg`
- `TWS` → `tws_kt`
- `Perf` → `perf_pct`
- `BRG` → `brg_deg` (empty = null)

### Aggregate Calculations

- **Duration**: last timestamp - first timestamp
- **Distance**: sum of haversine(point[i], point[i+1]) for all consecutive points
- **Avg/Max BSP**: mean and max of `bsp_kt` column
- **Avg TWS**: mean of `tws_kt` column
- **Avg VMG**: mean of `abs(BSP * cos(TWA))` across all track points where TWA is available
- **Avg VMC**: mean of `SOG * cos(COG - BRG)` across track points where BRG is available. Null if no points have BRG.

### Track Point Decimation

For rendering on the map, if a session has more than 5000 track points, decimate to every Nth point to keep the polyline under 5000 segments. All points are stored in Room; decimation is only for rendering.

## Screens

### Session List (SessionListScreen)

Scrollable list of cards, ordered by `start_time` descending.

Each card shows:
- Date and time (e.g. "28 Mar 2026 — 14:30")
- Duration (e.g. "2h 15m")
- Distance (e.g. "12.3 nm")
- Avg wind (e.g. "TWS 14 kt")
- Mini performance badge (avg perf%)

Pull-to-refresh triggers a manual re-sync (if Pi is reachable).

Empty state: "Nessuna sessione. Connettiti al Pi per sincronizzare."

### Session Detail (SessionDetailScreen)

#### Stats Section
Row of compact cards:
- **Durata**: 2h 15m
- **Distanza**: 12.3 nm
- **BSP**: 5.2 avg / 7.8 max kt
- **VMG**: 4.1 kt avg
- **VMC**: 3.8 kt avg (shown only when available)
- **Vento**: TWS 14 kt avg

#### Maneuvers Section
Card with:
- Tack count + Gybe count
- Avg recovery time (seconds)
- Avg VMG loss per maneuver (nm)
- Avg VMC loss per maneuver (nm) — shown only when available

If no maneuvers recorded, show "Nessuna manovra registrata."

#### Map Section
osmdroid MapView (wrapped in `AndroidView` for Compose) showing:
- **Track polyline** colored by performance:
  - Green (#4CAF50): perf >= 90%
  - Yellow (#FFC107): perf 70-89%
  - Red (#FF5722): perf < 70%
  - Gray (#9E9E9E): perf data unavailable
- **Tack markers**: upward triangle, blue
- **Gybe markers**: downward triangle, orange
- Auto zoom-to-fit the track bounding box with padding
- **Tile pre-download**: during sync, compute the bounding box of the session's track points and pre-download OSM tiles at zoom levels 10-15 for that area. This ensures the base map (lake boundaries, land, roads) is available offline. osmdroid's tile cache stores them locally; subsequent views of the same area are instant.
- Tiles outside pre-downloaded areas may be unavailable offline

## Navigation

### Bottom Navigation Bar
Two items with icons:
- **Live** (icon: `sensors`) — shows the WebView
- **Sessioni** (icon: `history`) — shows the sessions nav graph

### Sessions Nav
- `SessionListScreen` → tap card → `SessionDetailScreen(sessionId)`
- Back button returns to list

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | Jetpack Compose + Material 3 |
| Navigation | Compose Navigation |
| Database | Room |
| Map | osmdroid (OpenStreetMap) |
| Async | Kotlin Coroutines + Flow |
| HTTP | HttpURLConnection (already used, keep simple) |
| CSV parsing | Manual line-by-line (no extra dependency) |

## Project Structure

```
com.aquarela.viewer/
├── MainActivity.kt              (updated: hosts BottomNav + NavHost)
├── live/
│   └── LiveTab.kt               (WebView + Pi discovery, extracted from current MainActivity)
├── data/
│   ├── AppDatabase.kt           (Room database, version 1)
│   ├── SessionDao.kt
│   ├── TrackPointDao.kt
│   ├── ManeuverDao.kt
│   ├── Session.kt               (Room entity)
│   ├── TrackPoint.kt            (Room entity)
│   └── Maneuver.kt              (Room entity)
├── sync/
│   └── SyncManager.kt           (download + parse + insert logic)
├── sessions/
│   ├── SessionListViewModel.kt
│   ├── SessionListScreen.kt
│   ├── SessionDetailViewModel.kt
│   ├── SessionDetailScreen.kt
│   └── TrackMapView.kt          (osmdroid wrapped in AndroidView)
└── util/
    ├── Haversine.kt              (distance calc)
    └── CsvParser.kt              (parse CSV into track points + aggregates)
```

## Permissions

No new permissions needed. Existing: INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, CHANGE_NETWORK_STATE.

## Out of Scope

- Cross-session aggregate statistics (season totals, trends)
- Editing or deleting sessions from the app
- Exporting data from the app
- Polar data review
- Trim book review
