---
title: "Aquarela Electronics Inventory"
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
  - inventory
  - nmea2000
related:
  - "[[Aquarela Nitro 80 Reference]]"
  - "[[Aquarela Performance System]]"
  - "[[Aquarela Njord CSV Spec]]"
  - "[[Aquarela Shopping List]]"
  - "[[Aquarela Hull Maintenance]]"
  - "[[Aquarela Gennaker Procedures]]"
summary: "Complete inventory of all electronic devices on board the Nitro 80 Aquarela, permanently moored on Lake Lugano. Covers NMEA 2000 network, power system, navigation lights, and planned upgrades."
---

## Summary

Complete electronics inventory for Aquarela (Nitro 80), moored on Lake Lugano. Last verified: February 2026. Serial numbers to be recorded during next boat visit.

**Total devices on board: 13** (10 installed + 3 lights)
**Planned additions: 4** (Raspberry Pi system + energy upgrade)

---

## NMEA 2000 Network — Sensors

| # | Device | Manufacturer | Model / Part No. | Role | Location | Key PGNs | Serial No. | Purchase Date | Firmware | Replacement Cost | Notes |
|---|--------|-------------|-------------------|------|----------|----------|------------|---------------|----------|-----------------|-------|
| 1 | GPS Antenna | Garmin | GPS 24xd | Position, COG/SOG, heading, magnetic variation | Stern rail / transom | 127250, 127258, 129025, 129026, 129029 | — | — | — | ~€200 | 10 Hz update rate, WAAS/EGNOS capable |
| 2 | Speed/Depth/Temp Transducer | Airmar | Smart TRI Multisensor (20-633-01) | BSP, water depth, water temperature | Through-hull | 128259, 128267, 130310 | — | — | — | ~€300 | 235 kHz, 5 Hz speed output, paddlewheel kit: Airmar 33-113 |
| 3 | Wind Transducer | Garmin | gWind (**likely Wireless** — see note) | Apparent wind angle + speed | Masthead | 130306 | — | — | — | ~€350 | **RSSI = 70 shown on GNX Wind menu 4.3 (2026-02-25) — implies wireless model, not wired.** Verify by inspecting masthead unit and checking for base station on N2K backbone. See [[Aquarela GNX Menu Analysis 2026-02-25]] |

## NMEA 2000 Network — Displays & Consumers

| # | Device | Manufacturer | Model / Part No. | Role | Location | Serial No. | Purchase Date | Firmware | Replacement Cost | Notes |
|---|--------|-------------|-------------------|------|----------|------------|---------------|----------|-----------------|-------|
| 4 | Main Display | Garmin | GNX 20 | Primary data display (BSP, depth, SOG, etc.) | Cockpit bulkhead | — | — | — | ~€250 | Monochrome, sunlight-readable |
| 5 | Wind Display | Garmin | GNX Wind | Wind angle + speed display | Cockpit bulkhead | — | — | — | ~€300 | Dedicated wind gauge format |
| 6 | Race Tactical Display | Vakaros | Atlas 2 | Start line, race data, GPS, compass, heel/trim | Cockpit (portable) | — | — | — | ~€500 | Built-in L1+L5 GNSS, solid-state compass, IMU (heel/trim), 100h battery, wireless charging |

## NMEA 2000 Network — Gateways & Loggers

| # | Device | Manufacturer | Model / Part No. | Role | Location | Serial No. | Purchase Date | Firmware | Replacement Cost | Notes |
|---|--------|-------------|-------------------|------|----------|------------|---------------|----------|-----------------|-------|
| 7 | N2K-to-Bluetooth Gateway | Digital Yacht | NavLink Blue Vakaros Edition (ZDIGNLINKVA) | Bridges N2K data to Atlas 2 via BLE | On N2K backbone | — | — | — | ~€340 | Self-powered from N2K bus, bidirectional, BLE range ~10-15m |
| 8 | WiFi Data Gateway | Actisense | W2K-1 | N2K to WiFi gateway + SD card logger | On N2K backbone | — | — | — | ~€300 | **TO BE REMOVED** — replaced by Raspberry Pi system. Sells second-hand ~€150-200 |

## Power System

| # | Device | Manufacturer | Model / Part No. | Role | Location | Serial No. | Purchase Date | Replacement Cost | Notes |
|---|--------|-------------|-------------------|------|----------|------------|---------------|-----------------|-------|
| 9 | Battery 1 | Bosch | LTX14-BS (Li-ion) | Primary 12V power | Battery compartment | — | — | ~€80 | 12V, 48Wh. Two batteries in parallel = 96Wh total, 8Ah |
| 10 | Battery 2 | Bosch | LTX14-BS (Li-ion) | Primary 12V power | Battery compartment | — | — | ~€80 | 12V, 48Wh. See above |

## Navigation Lights

| # | Device | Manufacturer | Model / Part No. | Role | Location | Serial No. | Purchase Date | Replacement Cost | Notes |
|---|--------|-------------|-------------------|------|----------|------------|---------------|-----------------|-------|
| 11 | Masthead Light | — | — | Tricolor navigation light | Top of mast | — | — | — | Verify make/model on next boat visit |
| 12 | Anchor Light | — | — | All-round white (at anchor) | Masthead or pulpit | — | — | — | Verify make/model on next boat visit |
| 13 | Deck Light | — | — | Cockpit / deck illumination | Cockpit area | — | — | — | Verify make/model on next boat visit |

---

## Planned Additions

These devices are part of the [[Aquarela Performance System]] and [[Aquarela Shopping List]] upgrades.

| # | Device | Manufacturer | Model / Part No. | Role | Est. Cost | Status |
|---|--------|-------------|-------------------|------|-----------|--------|
| P1 | Data Logger | Raspberry Pi Foundation | Raspberry Pi 4 Model B (4GB) + Waveshare 2-CH CAN HAT | Full N2K data capture, CSV logging, WiFi dashboard | ~€80 | Planned — Phase 3 |
| P2 | Status LED | — | 12V 8mm waterproof panel mount | Logging status indicator | ~€5 | Planned — Phase 3 |
| P3 | LiFePO4 Battery | TBD (WattCycle recommended) | 12V 20Ah LiFePO4 | Replace 2× Bosch LTX14-BS, 256Wh capacity | ~€60-80 | Planned — Energy upgrade |
| P4 | Solar Panel | TBD (BougeRV recommended) | CIGS 100W ETFE | Solar charging, marine walkable | ~€120-150 | Planned — Energy upgrade |
| P5 | Charge Controller | TBD (EIEVEY recommended) | PWM 10A 12V, LiFePO4 compatible | Solar panel to battery regulation | ~€15 | Planned — Energy upgrade |

---

## NMEA 2000 Network Topology

```
[Garmin gWind]         (masthead)
      │
[Airmar 20-633-01]     (through-hull)
      │
[Garmin GPS 24xd]      (stern)
      │
══════╪══════════════════════════════ N2K Backbone ═══════
      │         │         │         │         │
  [GNX 20]  [GNX Wind] [Atlas 2] [W2K-1]  [NavLink Blue]
  display   display    via BLE   *remove*  BLE→Atlas 2
                         ↑                      │
                         └──────────────────────┘
```

**After Pi upgrade:**
```
══════╪══════════════════════════════ N2K Backbone ═══════
      │         │         │              │
  [GNX 20]  [GNX Wind] [NavLink Blue]  [Pi 4 + CAN HAT]
  display   display    BLE→Atlas 2     CSV logger + WiFi
```

---

## Notes Not Present On Board

The following common electronics are **not installed** on Aquarela (confirmed February 2026):

- No VHF radio (fixed or handheld)
- No AIS transponder or receiver
- No radar
- No chartplotter (separate from instrument displays)
- No autopilot
- No engine instruments
- No bilge pump (or electric bilge pump)
- No battery monitor/shunt
- No USB charging outlets
- No entertainment system

---

## Maintenance Schedule

| Device | Maintenance Task | Frequency | Last Done | Next Due |
|--------|-----------------|-----------|-----------|----------|
| Airmar 20-633-01 | Clean paddlewheel, check valve | Annual (haul-out) | — | Spring 2026 |
| Garmin gWind | Inspect bearings, clean cups | Annual | — | Spring 2026 |
| Garmin GPS 24xd | Visual inspection, connector check | Annual | — | Spring 2026 |
| Bosch LTX14-BS ×2 | Charge level check, terminal corrosion | Monthly (in season) | — | — |
| Navigation lights | Bulb/LED check, lens cleaning | Pre-season | — | Spring 2026 |
| All N2K connectors | Inspect for corrosion, reseat | Annual | — | Spring 2026 |

---

## How to Update This Inventory

1. **Adding a new device**: Add a row to the appropriate section table
2. **Recording serial numbers**: Fill in the "Serial No." column during next boat visit
3. **Moving a planned device to installed**: Move the row from "Planned Additions" to the main section, assign a new number
4. **Removing a device**: Move to a "Removed" section (don't delete — keep history)

---

*Inventory version 1.0 — February 2026*
*Boat: Nitro 80 "Aquarela" — Lake Lugano*
