# Wind Upwash Correction System — Design Spec

**Date:** 2026-04-09
**Boat:** Nitro 80, Lake Lugano
**Status:** Approved

---

## 1. Purpose

Apply corrections for sail-induced upwash, mast heel error, and mechanical alignment to raw wind data from the masthead anemometer. Produce corrected wind values for both the Aquarela app and the NMEA 2000 bus (GNX displays).

## 2. Decisions

| Decision | Choice |
|---|---|
| Architecture | Three separate modules (B): correction, learning, CAN writer |
| Upwash model | Hybrid: literature-based initial values + conservative auto-learning |
| Sail inventory | 2 mains, 1 jib, 1 genoa, 2 gennakers |
| Upwash tables | 6 tables: 2 mains x 3 headsail categories (jib, genoa, gennaker) |
| Table persistence | Separate file: `data/upwash-tables.json` |
| Learning strategy | Conservative — only clean tacks/gybes in stable wind |
| CAN writer | Developed from day one, off + dry-run by default |

## 3. Correction Chain

Corrections apply in sequence. Order matters — each stage depends on the previous output.

```
raw_awa_deg, raw_aws_kt (PGN 130306)
    |
    v
[existing] Calibration: awa_deg = raw_awa_deg - awa_offset  (calibration.py)
    |
    v
[existing] Damping: heel_deg smoothed (4s moving average)
    |
    v
[new] Stage 2 — Heel correction (geometric projection)
    |
    v
[new] Stage 3 — Upwash correction (2D table lookup + bilinear interpolation)
    |
    v
awa_corrected_deg, aws_corrected_kt
    |
    v
[modified] Stage 4 — True wind calculation (uses corrected values)
```

### 3.1 Stage 1 — Mechanical alignment

Already implemented in `calibration.py`. Single scalar offset.

```
awa_deg = raw_awa_deg - awa_offset
```

No changes needed.

### 3.2 Stage 2 — Heel correction

The masthead sensor is fixed to the mast. When the boat heels, the sensor's rotation plane tilts. This introduces errors in both angle and speed.

```
awa_heel = atan2(sin(awa_deg), cos(awa_deg) * cos(heel))
aws_heel = aws_kt * sqrt(cos²(heel) * cos²(awa_deg) + sin²(awa_deg))
```

The speed formula derives from projecting the wind vector `(aws*cos(awa), aws*sin(awa), 0)` from the tilted mast frame back to the horizontal plane via rotation about the longitudinal axis by the heel angle.

Input: `heel_deg` from PGN 127257, smoothed with a dedicated `HeelDamper` (see Section 8.1).

Pitch is assumed negligible (monohull). If pitch becomes relevant, extend to full 3D rotation matrix.

### 3.3 Stage 3 — Upwash correction

Compensates airflow deflection caused by the sail plan (primarily the mainsail).

```
upwash_offset = bilinear_interpolate(table, abs(awa_heel), abs(heel))
awa_corrected = awa_heel + sign(awa_heel) * upwash_offset
aws_corrected = aws_heel  (no speed correction from upwash)
```

The upwash is symmetric: the table covers 0-180 degrees, the sign of the offset follows the sign of AWA.

### 3.4 Stage 4 — True wind calculation

Existing `calc_true_wind()` modified to use corrected values when available, with fallback to uncorrected values.

The existing implementation uses the Cartesian decomposition form:

```
tw_x = AWS_c * cos(AWA_c) - BSP
tw_y = AWS_c * sin(AWA_c)
TWS = sqrt(tw_x² + tw_y²)
TWA = atan2(tw_y, tw_x)
TWD = HDG + TWA  (normalized 0-360)
```

No formula change needed — only the input values change from `(awa_deg, aws_kt)` to `(awa_corrected_deg, aws_corrected_kt)`.

**Field routing:** `apply_wind_correction()` writes to the new `state.awa_corrected_deg` and `state.aws_corrected_kt` fields, preserving the pre-correction values in `state.awa_deg` and `state.aws_kt`. `calc_true_wind()` is modified to read `awa_corrected_deg` if not None, otherwise falls back to `awa_deg`. Same for AWS. This preserves both values for logging and A/B comparison.

## 4. Data Model: UpwashTable

### 4.1 Table structure

Each table is a 2D lookup grid:

- **AWA axis:** 20 to 180 degrees, step 5 degrees — 33 breakpoints
- **Heel axis:** 0 to 35 degrees, step 5 degrees — 8 breakpoints
- **Each cell:** offset in degrees, observation count

Total per table: 33 x 8 = 264 cells.

Between grid points, bilinear interpolation is applied.

### 4.2 Initial values

Pre-populated from literature. Representative values:

| AWA | Heel 0 | Heel 5 | Heel 15 | Heel 25 | Heel 35 |
|---|---|---|---|---|---|
| 20 (close-hauled) | +2.0 | +3.0 | +4.0 | +5.0 | +5.5 |
| 45 (close reach) | +1.5 | +2.0 | +3.0 | +3.5 | +4.0 |
| 90 (beam reach) | +0.5 | +0.5 | +1.0 | +1.0 | +1.0 |
| 135 (broad reach) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 180 (run) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

Intermediate values linearly interpolated to fill all 264 cells.

### 4.3 File format: `data/upwash-tables.json`

```json
{
  "version": "1.0",
  "boat": "Nitro 80",
  "updated": "2026-04-09T14:30:00",
  "sail_configs": {
    "main_1__jib": {
      "main": "main_1",
      "headsail_category": "jib",
      "awa_breakpoints": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175, 180],
      "heel_breakpoints": [0, 5, 10, 15, 20, 25, 30, 35],
      "offsets": [
        [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
        "... one row per AWA breakpoint"
      ],
      "observations": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        "... one row per AWA breakpoint"
      ],
      "last_updated": "2026-04-09T14:30:00"
    },
    "main_1__genoa": {},
    "main_1__gennaker": {},
    "main_2__jib": {},
    "main_2__genoa": {},
    "main_2__gennaker": {}
  }
}
```

### 4.4 Six table keys

| Key | Main | Headsail category |
|---|---|---|
| `main_1__jib` | main_1 | jib |
| `main_1__genoa` | main_1 | genoa |
| `main_1__gennaker` | main_1 | gennaker |
| `main_2__jib` | main_2 | jib |
| `main_2__genoa` | main_2 | genoa |
| `main_2__gennaker` | main_2 | gennaker |

## 5. Auto-Learning (`pipeline/upwash_learning.py`)

### 5.1 Principle

In stable wind, TWD must be the same on both tacks. Every tack/gybe is a calibration opportunity. The systematic TWD difference between the two tacks is attributed to residual upwash error.

### 5.2 Tack/gybe detection

A maneuver is detected when `awa_corrected_deg` changes sign. The maneuver is "complete" when AWA stabilizes on the new side (variance < 3 degrees for 30 seconds).

### 5.3 Validity filter (conservative)

A maneuver contributes to learning only if ALL of these criteria are met:

| Criterion | Threshold |
|---|---|
| TWD stable pre-maneuver | sigma(TWD) < 5 degrees over last 2 minutes |
| TWD stable post-maneuver | sigma(TWD) < 5 degrees over next 2 minutes |
| Sufficient BSP | > 3 kt |
| No sail config change | same sail_config before and after |
| Window duration | at least 2 minutes pre and post |

If any criterion fails, the maneuver is discarded. Logged for debug but does not contribute to the table.

### 5.4 Residual calculation

```
twd_pre  = mean(TWD over 2 min before maneuver)
twd_post = mean(TWD over 2 min after maneuver)
residual = (twd_post - twd_pre) / 2
```

Divided by 2 because the upwash error acts in opposite directions on the two tacks.

### 5.5 Table update

The residual is attributed to the cell corresponding to `(mean_AWA, mean_heel)` of the pre-maneuver window:

```
cell.offset += learning_rate * residual
cell.n_observations += 1
```

**Learning rate:** 0.1 — each valid observation moves the table 10% toward the new value. After approximately 20 observations on the same cell, the value converges. Configurable.

### 5.6 Rolling buffer

3-minute circular buffer of `(timestamp, twd, awa_corrected, heel, bsp)`. The main loop runs at 10 Hz, but `learning_check()` only appends to the buffer once per second (downsampling internally). This yields approximately 180 samples over 3 minutes. Negligible memory impact.

### 5.7 Persistence

- Table saved to `data/upwash-tables.json` after each update
- Also saved on clean shutdown
- On startup, loads existing file or generates tables with initial values

### 5.8 Boundaries

- Does not modify data in real time — only updates the table, used by the next correction cycle
- Does not learn during races (future flag, for now always learns)
- Updates only the nearest cell — bilinear interpolation during correction handles the rest. Future improvement: distribute updates to the 4 surrounding cells weighted by bilinear coefficients for smoother convergence.

## 6. CAN Writer (`nmea/can_writer.py`)

### 6.1 Address claim (PGN 60928)

On startup the Pi announces itself on the bus with a unique 64-bit NAME:

| Field | Value |
|---|---|
| Unique Number | Hash of first 4 bytes of Pi MAC address |
| Manufacturer Code | 2047 (reserved for non-certified devices) |
| Device Instance | 0 |
| Device Function | 130 (Atmospheric) |
| Device Class | 75 (External Environment) |
| Industry Group | 4 (Marine) |
| Self-configurable | 1 (can negotiate address) |

**Initial address:** 100 (range 100-127, conventionally used for custom devices).

**Negotiation:** if another device contests the address, the Pi increments and retries. If the range is exhausted, logs an error and disables writing.

### 6.2 Published PGNs

Single PGN: **130306 (Wind Data)** at **1 Hz**.

Two distinct messages with different Wind Reference fields:

| Reference | Value | Content |
|---|---|---|
| True (water referenced) | 4 | TWA, TWS computed from STW |
| True (ground referenced) | 3 | TWA, TWS computed from SOG |

The Wind Reference field in PGN 130306 distinguishes the data type. We do NOT publish corrected AWA/AWS — only the final true wind product.

### 6.3 Safety controls

```python
can_writer_enabled: bool = False   # off by default
can_writer_dry_run: bool = True    # logs what it would write, does not call bus.send()
```

**First activation procedure:**

1. Start in dry-run mode, verify logs
2. Enable writing with water-referenced data only
3. Verify on GNX that data appears as a separate source
4. If OK, enable both references

### 6.4 Error handling

- **Bus unavailable:** if `can0` is not configured or CAN HAT is unresponsive, the writer disables silently and logs a warning. Rest of system works normally.
- **Address conflict:** retries with next address, max 28 attempts (100-127 inclusive). If all fail, disables.
- **Data unavailable:** if `awa_corrected_deg` is None, skips that cycle. Never publishes partial or stale data.

### 6.5 Implementation

Uses python-can (already a dependency). CAN bus is full-duplex — reading and writing on the same SocketCAN socket is supported. The writer runs on a separate 1 Hz timer, not in the main 10 Hz loop.

## 7. Configuration Changes

### 7.1 New fields in `AquarelaConfig`

```python
# Sail inventory
sails: dict = {
    "mains": ["main_1", "main_2"],
    "headsails": {
        "jib": ["jib_1"],
        "genoa": ["genoa_1"],
        "gennaker": ["gennaker_1", "gennaker_2"]
    }
}

# Active sail configuration (selected by user in frontend)
active_main: str = "main_1"
active_headsail: str = "genoa_1"

# Upwash learning
upwash_learning_rate: float = 0.1
upwash_learning_enabled: bool = True

# CAN writer
can_writer_enabled: bool = False
can_writer_dry_run: bool = True
```

The headsail category (jib/genoa/gennaker) is derived automatically from the `headsails` structure. Changing `active_headsail` to "gennaker_2" selects the table `main_1__gennaker`.

The old `sail_type` field is deprecated but kept for backward compatibility. On load, if `sails` is absent, it is generated from `sail_type` with default mapping.

### 7.2 New fields in `BoatState`

```python
# Wind correction output
awa_corrected_deg: float | None = None
aws_corrected_kt: float | None = None
upwash_offset_deg: float | None = None
heel_correction_deg: float | None = None

# Active sail config (for frontend and logging)
active_sail_config: str | None = None  # e.g. "main_1__genoa"

# Learning status
upwash_learning_status: str | None = None  # "waiting", "pre_tack", "post_tack", "updated", "rejected"
```

### 7.3 Heel damping

The existing `DampingFilters.apply()` runs all damping fields in a single pass after true wind calculation. Heel needs to be smoothed *before* wind correction. Rather than restructuring the existing class, we add a **standalone `HeelDamper`** — a single `AngleBuffer` (not `ScalarBuffer`, since heel is a signed angle that could cross zero) with a 4-second window. This runs in `main.py` between calibration and wind correction.

The existing damping pass remains unchanged.

```python
# Standalone, runs before wind correction
heel_damper = AngleBuffer(window_s=4.0, sample_rate_hz=10)

# Existing DampingFilters, runs after true wind (unchanged)
"tws_kt": 5.0, "twd_deg": 10.0, "bsp_kt": 2.0, "vmg_kt": 3.0
```

Optional: `awa_deg` damping (1.5s) can be added to the existing `DampingFilters` pass if needed after testing, but is not required for the correction chain.

### 7.4 New API endpoints

**`POST /api/sails`** — change active sail configuration:

```json
{"active_main": "main_2", "active_headsail": "gennaker_1"}
```

**`GET /api/upwash`** — return current upwash table for active sail config (for frontend visualization).

**`POST /api/upwash/reset`** — reset a specific table to initial values (optional, for re-learning).

The existing `/api/calibration` endpoint is extended to accept `upwash_learning_rate`, `upwash_learning_enabled`, `can_writer_enabled`, and `can_writer_dry_run`.

## 8. Pipeline Integration

### 8.1 Modified loop in `main.py`

```
PGN decode
    -> apply_calibration()           [existing]
    -> heel_damper.smooth(heel_deg)  [NEW: standalone AngleBuffer, 4s window]
    -> apply_wind_correction()       [NEW: writes awa_corrected_deg, aws_corrected_kt]
    -> calc_true_wind()              [modified: reads awa_corrected_deg if available, fallback to awa_deg]
    -> calc_derived()                [existing]
    -> damping_filters.apply()       [existing: tws, twd, bsp, vmg — unchanged]
    -> calc_targets()                [existing]
    -> learning_check()              [NEW: appends to buffer 1x/sec, checks for completed maneuvers]
    -> broadcast()                   [existing]
```

CAN writer runs on a separate 1 Hz timer, reads the latest `BoatState`.

### 8.2 Graceful degradation

| Missing sensor | Behavior |
|---|---|
| Heel unavailable | Stage 2 skipped (heel=0), stage 3 uses heel=0 column |
| Upwash table not loaded | Stages 2 and 3 skipped, true wind calculated as today |
| CAN bus not writable | Writer disabled, everything else works |
| BSP unavailable | True wind not calculated (as today), learning does not collect data |

### 8.3 Logging

CSV logger extended with new columns: `awa_corrected_deg`, `aws_corrected_kt`, `upwash_offset_deg`, `heel_correction_deg`.

WebSocket broadcast includes all new `BoatState` fields automatically.

## 9. New Files

| File | Responsibility |
|---|---|
| `aquarela/pipeline/wind_correction.py` | Heel correction + upwash lookup. Pure function: data in, corrected data out. |
| `aquarela/pipeline/upwash_learning.py` | Tack detection, validity filter, residual calculation, table update. Stateful. |
| `aquarela/pipeline/upwash_table.py` | UpwashTable data class: load/save JSON, bilinear interpolation, initial value generation. |
| `aquarela/nmea/can_writer.py` | PGN 130306 encoding, address claim, bus writing, toggle/dry-run. |
| `data/upwash-tables.json` | Persistent upwash tables (generated on first run). |
| `tests/test_wind_correction.py` | Heel correction, upwash lookup, full chain. |
| `tests/test_upwash_learning.py` | Tack detection, validity filter, residual calc, table update. |
| `tests/test_upwash_table.py` | Bilinear interpolation, JSON load/save, initial values. |
| `tests/test_can_writer.py` | PGN encoding, address claim, toggle, error handling. |

## 10. Testing Strategy

### 10.1 Unit tests

- **wind_correction**: heel=0 produces no change; known heel+AWA combos produce geometrically expected values; upwash lookup with test table returns interpolated values.
- **upwash_learning**: tack detection on sign change; conservative filter rejects unstable conditions; residual math is correct; learning rate applies correctly; JSON round-trip.
- **upwash_table**: bilinear interpolation at grid points, between points, and at edges; initial value generation fills all cells monotonically.
- **can_writer**: PGN 130306 encoding matches spec; address claim builds correct NAME; dry-run does not call bus.send(); disabled mode produces no output.

### 10.2 Integration tests

- Pipeline end-to-end: raw values through correction chain produce reasonable TWA/TWS.
- Simulator extension: inject known upwash, verify learning converges after N simulated tacks.

## 11. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Correction latency | < 1 ms per cycle (trig + lookup) |
| CAN publish jitter | 1 Hz +/- 10 ms |
| Learning buffer memory | ~180 samples x 5 fields = negligible |
| Startup time | Tables loaded in < 100 ms |
| Backward compatibility | System works with no upwash-tables.json (generates defaults) |
