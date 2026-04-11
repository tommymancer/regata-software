---
title: "Aquarela Session 2025-02-25 — Vakaros Export Analysis"
created: 2026-02-25
updated: 2026-02-25
type: insight
status: active
domain: aquarela
tags:
  - type/insight
  - domain/sailing
  - domain/electronics
  - project/aquarela
  - vakaros
  - nmea2000
  - data-quality
related:
  - "[[Aquarela Performance System]]"
  - "[[Aquarela Electronics Inventory]]"
  - "[[Aquarela Njord CSV Spec]]"
summary: "Vakaros Atlas 2 export (CSV + VKX) confirmed missing wind data despite displaying it on screen. Export includes external NMEA data (depth, water temp from Airmar) but omits wind PGN 130306 from gWind. STW logged as 0.00 — transducer was not connected. Confirms the Pi logger is needed to capture complete sailing data."
---

## Summary

Analyzed the Vakaros Atlas 2 data export from today's session on Lake Lugano. Wind data was visible on the Atlas 2 screen during sailing but is completely absent from both the CSV and VKX export files. This empirically confirms the gap identified in [[Aquarela Performance System]]: the Vakaros drops wind PGNs in export.

## Session Details

- **Date**: 2026-02-25
- **Location**: Lake Lugano
- **Duration**: ~38 minutes (2,315 data rows at 1 Hz)
- **Export files**: `vakaros 2-25-2026.csv` (CSV), `vakaros 2-25-2026.vkx` (binary, 236 KB)
- **Transducer status**: Airmar Smart TRI was NOT physically connected during this session

## CSV Export — Columns Present

| Category | Columns | Source |
|----------|---------|--------|
| GPS/Nav | timestamp, latitude, longitude, sog_kts, cog, altitude_m | Atlas 2 internal GNSS |
| IMU/Orientation | hdg_true, heel, trim, declination, q_w, q_x, q_y, q_z | Atlas 2 internal IMU |
| Paddlewheel | stw_forward_kts, stw_horizontal_kts | External — Airmar 20-633-01 (PGN 128259) |
| Depth/Temp | depth_m, water_temp_c | External — Airmar 20-633-01 (PGNs 128267, 130310) |

**Total: 18 columns. Zero wind columns (no TWS, TWD, TWA, AWS, AWA).**

## Key Findings

### 1. Vakaros exports external NMEA data — selectively

The Airmar transducer was not connected, yet depth and water_temp columns contain realistic, varying values (depth 10.68–10.83m, water temp 11.38–11.51°C). This data came from the NMEA 2000 bus via the NavLink Blue BLE gateway. The Vakaros is clearly capable of logging external sensor data — it just doesn't include wind.

### 2. Depth/temp are real sensor readings, not cached

Values fluctuate naturally across the session — small depth variations and gradual temperature changes. These are live NMEA values being received and logged, not stale cached data.

### 3. STW confirms transducer was disconnected

`stw_forward_kts` and `stw_horizontal_kts` are 0.00 for the entire session. This is consistent with the paddlewheel not being in the water. The columns exist because the Vakaros logs the PGN structure even when the sensor reports zero.

### 4. Wind was on screen but not in export

During this session, wind data was visible on the Atlas 2 display. The gWind masthead unit transmits PGN 130306 (Wind Data) on the N2K bus, and the NavLink Blue bridges it to the Atlas 2 via BLE. The Vakaros receives and displays it — but its CSV/VKX export firmware does not include wind fields.

### 5. VKX binary format also lacks wind

Searched the VKX file for any wind-related strings (wind, TWS, TWD, TWA, AWS, AWA, gust) — none found. The binary structure appears to contain the same data channels as the CSV, just in a packed format.

## Implications

This confirms the Vakaros Atlas 2 cannot be relied on as a complete data logger. The [[Aquarela Performance System]] Raspberry Pi project remains essential for capturing wind data (PGN 130306) alongside all other sailing data.

## Possible Actions

- **Contact Vakaros support**: Request wind fields be added to CSV export. The infrastructure is there (they already export depth/temp from external NMEA sources). Include this session as evidence.
- **Proceed with Pi logger**: This finding reinforces the priority of the Raspberry Pi + CAN HAT system as the primary data capture solution.
- **Workaround**: Until Pi is installed, a separate NMEA logger on the bus could capture wind data for merging with Vakaros CSV by timestamp.

## Connections

- Confirms the "Vakaros missing wind data" row in [[Aquarela Performance System#Problems Solved]]
- Relevant to [[Aquarela Njord CSV Spec]] — Njord requires wind columns that Vakaros cannot provide
- NavLink Blue gateway (see [[Aquarela Electronics Inventory]]) bridges N2K→BLE correctly; the gap is in Vakaros export firmware, not the data path
