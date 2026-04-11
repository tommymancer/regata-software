---
title: "Aquarela GNX Menu Analysis — 2026-02-25"
created: 2026-02-25
updated: 2026-02-25
type: reference
status: active
domain: aquarela
tags:
  - type/reference
  - domain/sailing
  - domain/electronics
  - project/aquarela
  - calibration
  - nmea2000
  - garmin
related:
  - "[[Aquarela Electronics Inventory]]"
  - "[[Aquarela Performance System]]"
  - "[[Aquarela Njord CSV Spec]]"
summary: "Complete submenu dump of Garmin GNX Wind (firmware 2.60) and partial GNX 20, photographed 2026-02-25 at dock. Wind angle offset = 10°, BSP calibration = 0%, AWA damping = 1, all other filters at 0. RSSI = 70 on gWind — indicates wireless transducer (contradicts inventory listing it as wired). GPS position/SOG/COG usage by displays is NOT confirmed from these menus: true wind and VMG can be computed from paddlewheel BSP + gWind + heading alone."
---

## Summary

Photographed full submenu tree of the Garmin GNX Wind and one screen from the GNX 20, dockside on Aquarela, 2026-02-25. This documents every current setting for calibration baseline, and raises an open question about whether the GPS 24xd's position/SOG/COG data is actually being consumed by the displays.

## GNX Wind — Firmware 2.60

### Menu 2.x — Data Fields & Damping Filters

These control which data fields appear on the display pages and how much smoothing is applied. F:00 = no damping, higher = more smoothing (adds lag).

| Menu | Field | Filter | Notes |
|------|-------|--------|-------|
| 2.1 | TWS (True Wind Speed) | F:00 | Computed from AWA + AWS + BSP |
| 2.2 | AWS (Apparent Wind Speed) | F:00 | Direct from gWind transducer |
| 2.3 | TWA (True Wind Angle) | F:00 | Computed from AWA + AWS + BSP |
| 2.4 | AWA (Apparent Wind Angle) | F:01 | Direct from gWind — **only field with damping applied** |
| 2.5 | TWD (True Wind Direction) | F:00 | = Heading + TWA — requires heading source |
| 2.6 | BSP (Boat Speed) | F:00 | From Airmar paddlewheel (PGN 128259) |
| 2.7 | VMG (Velocity Made Good) | F:00 | = BSP × cos(TWA) — paddlewheel + wind only |
| 2.8 | STR (Steer) | F:00 | Heading-to-steer function |
| 2.9 | ALOG (Analog) | F:00 | Close-hauled angle log |

### Menu 4.x — Wind Transducer Calibration

| Menu | Setting | Value | Notes |
|------|---------|-------|-------|
| 4.1 | WIND | On | Wind source enabled |
| 4.2 | ANGL | 10 | **Wind angle offset = 10°** — mechanical alignment correction |
| 4.3 | RSSI | 70 | **Signal strength indicator — implies wireless gWind** (see below) |

### Menu 6.x — System / Display

| Menu | Setting | Value | Notes |
|------|---------|-------|-------|
| 6.1 | LGHT | 0 | Backlight off |
| 6.2 | COLR | C:01 | Color scheme 1 |
| 6.3 | BEEP | OFF | Beeper disabled |
| 6.4 | POWR | Aut | Auto power — follows N2K bus on/off |
| 6.5 | PGES | 4 | 4 data pages configured |
| 6.6 | SCRL | OFF | No auto-scroll between pages |
| 6.7 | DFLT | — | Factory reset option (not activated) |
| 6.8 | VER | 2.60 | Firmware version |

## GNX 20 — Partial

Only one submenu screen was captured:

| Menu | Setting | Value | Notes |
|------|---------|-------|-------|
| 4.4 | BSP% | 0 | **Boat speed calibration factor = 0%** — no correction applied to paddlewheel |

**Missing**: GNX 20 menus 1.x–3.x, 5.x, 6.x were not photographed. These would show depth offset, speed units, data source selection, and whether SOG/COG pages are configured.

## Open Question: Is GPS Position/SOG/COG Being Used?

### What we know

The GPS 24xd broadcasts several PGNs on the N2K bus: 127250 (Heading), 127258 (Magnetic Variation), 129025 (Position Rapid), 129026 (COG/SOG Rapid), 129029 (GNSS Position).

### What the displays need for their computed fields

- **TWA, TWS**: AWA + AWS + BSP. All from gWind + Airmar paddlewheel. **No GPS needed.**
- **TWD**: = Heading + TWA. Heading comes from GPS 24xd (PGN 127250), but this is the magnetic heading output, **not position/SOG/COG**.
- **VMG**: = BSP × cos(TWA). Paddlewheel + wind only. **No GPS needed** for this formula. (An alternative VMG formula uses SOG × cos(COG − TWD), which would require GPS, but we don't know which formula the GNX Wind uses.)
- **STR**: Requires heading (from GPS 24xd heading output) and a waypoint/course — unclear if configured.

### Conclusion

**From these menu photos alone, we cannot confirm that GPS position or SOG/COG data is being consumed by either display.** The GNX Wind's true wind and VMG calculations can run entirely on paddlewheel speed + wind data + heading. The heading does come from the GPS 24xd, but that's a compass/heading output (PGN 127250), not the position fix.

To determine if SOG/COG is actually being displayed, we would need to:
1. Photograph the GNX 20's data pages to see if SOG or COG fields are configured
2. Check the GNX 20's full menu tree (especially source selection settings)
3. Compare BSP vs SOG readings while sailing — if they differ, the GPS is providing independent speed data

## Finding: gWind Appears to Be Wireless

The RSSI reading in menu 4.3 (value = 70) is a **Received Signal Strength Indicator**. This metric only exists for wireless communication between the transducer and the display/network. A hardwired gWind connected via mast cable directly to N2K would not report RSSI.

**This suggests the masthead unit is a Garmin gWind Wireless**, not the standard wired gWind listed in [[Aquarela Electronics Inventory]]. The wireless model communicates via 868/915 MHz to a base station connected to the N2K bus.

**Confidence**: Medium-high. The RSSI field strongly implies wireless, but it's possible (unlikely) that this menu item shows N2K bus signal quality on some firmware versions. Verify by visually inspecting the masthead unit and checking for a separate base station on the N2K backbone.

**Action**: Update [[Aquarela Electronics Inventory]] to flag this as "likely wireless — verify on next boat visit."

## Calibration Baseline — Current State

| Parameter | Current Value | How to Calibrate |
|-----------|--------------|------------------|
| Wind angle offset (ANGL) | 10° | Sail close-hauled both tacks, average AWA. If port AWA = starboard AWA (absolute), offset is correct. |
| BSP calibration (BSP%) | 0% | Compare BSP to GPS SOG on flat water, no current, multiple runs both directions. Adjust % until they match. |
| AWA damping (F:) | 1 | Acceptable for racing. Increase to 2-3 if readings are too jumpy in choppy conditions. |
| All other damping | 0 | Fine for racing. Consider F:01 on TWD if it oscillates too much. |

## Connections

- Updates [[Aquarela Electronics Inventory]] — gWind may be wireless model, not wired
- Relevant to [[Aquarela Performance System]] — calibration values affect all derived data (TWS, TWA, VMG) that the Pi logger will compute
- Complements [[Aquarela Session 2025-02-25]] — same dock visit, different analysis focus
