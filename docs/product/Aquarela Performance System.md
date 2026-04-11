---
title: "Aquarela Performance System"
created: 2026-02-24
type: project
status: active
domain: aquarela
tags:
  - type/project
  - domain/sailing
  - domain/electronics
  - project/aquarela
  - nmea2000
  - raspberry-pi
  - njord-analytics
related:
  - "[[Aquarela Njord CSV Spec]]"
summary: "Raspberry Pi-based NMEA 2000 data logger replacing the Actisense W2K-1, providing clean CSV logging, WiFi dashboard, and Njord Analytics integration for the Nitro 80 Aquarela."
---

## Summary

Replace the unreliable Actisense W2K-1 WiFi gateway with a dedicated Raspberry Pi 4 + CAN HAT that connects directly to the NMEA 2000 bus. The Pi logs all sailing data (wind, speed, heading, position, depth) to clean CSV files, serves a mobile dashboard over WiFi, and exports sessions to Njord Analytics for post-race analysis. This eliminates corrupt .ebl files, data gaps, and proprietary format headaches.

## Status

**Current Phase**: Phase 2 — Phone Dashboard (live on boat, tested March 2026)
**Health**: 🟢 On Track

### What's working (as of March 2026)
- Full NMEA 2000 PGN decoding (15 PGNs including fast-packet)
- Live data on phone via WiFi hotspot + Android WebView app
- Multi-page dashboard: upwind, downwind, wind rose, regatta, sensors, system, etc.
- Session CSV logging with download from phone
- SIM/BOAT source switching from the UI
- Direct ethernet Mac→Pi connection (auto-DHCP fallback)
- One-command deploy (`./deploy.sh`)

## Key Links

- [[Aquarela Njord CSV Spec]] — Exact column headers, PGN mapping, calibration pipeline
- Calibration Wizard: React app for compass, speed, wind, and depth calibration procedures

## Problems Solved

| Problem | Cause | Pi Solution |
|---------|-------|-------------|
| Corrupt .ebl files | W2K-1 SD card write issues | Pi logs clean CSV directly from N2K bus |
| Slow/unreliable SD download | Actisense proprietary format | Direct file access via Pi WiFi or USB |
| Data gaps in recordings | W2K-1 reliability | Pi reads CAN bus directly — no middleman |
| Vakaros missing wind data | Atlas 2 drops wind PGNs | Pi captures ALL PGNs including 130306 |
| No post-session analysis tool | No integrated workflow | Njord Analytics via CSV upload |

## Onboard Network

### NMEA 2000 Devices

| Device | Model | Role | Key PGNs |
|--------|-------|------|----------|
| GPS / Heading | Garmin GPS 24xd | Position + heading at 10 Hz | 126992, 127250, 127258, 129025, 129026, 129029, 129540 |
| Main Display | Garmin GNX 20 | Primary data display | Consumer |
| Wind Display | Garmin GNX Wind | Wind angle/speed | Consumer |
| Race Tactical | Vakaros Atlas 2 | Start line, race display | Consumer + partial logger |
| Speed/Depth/Temp | Airmar Smart TRI (20-633-01) | BSP + depth + temp through-hull | 128259, 128267, 128275, 130310, 130311 |
| Wind Transducer | Garmin gWind | Masthead AWA/AWS | 130306 |
| N2K-BLE Gateway | Digital Yacht NavLink Blue Vakaros Ed. | Bridges N2K to Atlas 2 via BLE | 128259, 128267, 130306, 130310 |
| **Data Logger** | **Raspberry Pi 4 + CAN HAT** | **Full data capture** | **All PGNs** |

### Data Flow

```
[gWind] ──┐
[Airmar 20-633-01] ──┤── N2K Bus ──┬── GNX 20 (display)
[GPS 24xd] ──┤            ├── GNX Wind (display)
              │            ├── Vakaros Atlas 2 (race tactical)
              │            └── Pi 4 + CAN HAT (headless logger)
                                 │
                                 ├── Status LED (green = logging)
                                 ├── CSV log files → Njord Analytics
                                 └── WiFi hotspot → phone dashboard
```

## Hardware

### Essential Components (~€155-160)

| Item | Spec | Est. Price |
|------|------|-----------|
| Raspberry Pi 4 Model B | 4GB RAM | ~€55 |
| MicroSD Card | 64GB, Class A2 | ~€12 |
| CAN Bus HAT | Waveshare 2-CH or PiCAN2 | ~€25 |
| NMEA 2000 Connector | Micro-C (M12 5-pin) to bare wires | ~€15 |
| 12V→5V Step-Down | Marine grade, USB-C, 3A+ | ~€15 |
| Waterproof Enclosure | IP67, small | ~€15-20 |
| 12V Power Cable | 2m, inline 3A fuse | ~€10 |
| Status LED | Green/Red visible through enclosure | ~€5 |

### CAN HAT Wiring to N2K

- **CAN-H** (pin 4, blue) → HAT CAN-H
- **CAN-L** (pin 5, white) → HAT CAN-L
- **Shield/GND** (pin 1) → HAT GND
- **+12V and GND** (pins 2-3) → NOT connected (Pi powered separately via step-down)

### SocketCAN Setup

```bash
sudo ip link set can0 up type can bitrate 250000  # NMEA 2000 = 250 kbps
candump can0  # test — see raw frames
```

## Software Stack

- **Backend**: Python FastAPI + uvicorn, custom PGN decoder (no canboat dependency)
- **Frontend**: Svelte (13 pages), served as static files by FastAPI
- **Data transport**: WebSocket with 1 Hz heartbeat broadcast
- **CAN interface**: python-can + SocketCAN, with fast-packet reassembly for multi-frame PGNs
- **Android app**: Kotlin WebView wrapper with auto-discovery (mDNS + IP probing)
- **WiFi Hotspot**: NetworkManager hotspot, SSID "Aquarela", dashboard at http://10.42.0.1:8080
- **Data Logger**: Session CSV writer + SQLite metadata
- **Njord Export**: CSV files matching [[Aquarela Njord CSV Spec]]
- **Deploy**: `deploy.sh` — builds frontend, rsyncs to Pi, restarts service

## Derived Data (Computed by Pi)

- **VMG** — from BSP + TWA
- **True Wind** (TWA, TWS, TWD) — from AWS, AWA, BSP, heading
- **Current Set/Drift** — from BSP vs SOG, heading vs COG
- **Target BSP** — comparison against stored polar table (Phase 4)
- **Performance %** — actual BSP vs target BSP at given TWA/TWS (Phase 4)

## Phases

### Phase 1 — Njord-Compatible Data Pipeline ✅
CSV spec validated, test dataset uploaded and accepted by Njord. Spec covers column headers, PGN mapping, sign conventions, calibration corrections.

### Phase 2 — Phone Dashboard ✅ (in progress — core complete)
Mobile-first Svelte dashboard served over WiFi hotspot. 13 pages including upwind, downwind, wind rose, regatta, sensors, system, navigation, performance, polar, map, trim, race timer, course setup. Android WebView app with auto-discovery. Session logging with download. SIM/BOAT source switching. Tested on boat March 2026.

### Phase 3 — Pi Hardware Setup & Installation
Flash Pi OS, install CAN HAT, wire to N2K bus, remove W2K-1, install canboat, mount in enclosure, configure hotspot, end-to-end test.

### Phase 4 — Advanced Features
Stored polars, performance %, current set/drift, auto-upload to Njord on home WiFi, race replay, Vakaros start line integration.

## Usage Workflow

**Before sailing:** Turn on 12V → Pi boots → LED goes green → logging starts automatically.

**While sailing:** GNX 20 + GNX Wind + Vakaros = live displays. Optionally connect phone to "Aquarela" WiFi for extra data/VMG.

**After sailing:** Connect phone to "Aquarela" WiFi → download session CSV → upload to Njord Analytics → instant reports (polars, maneuvers, gain/loss, fleet comparison).

## Cost Recovery

Sell the removed Actisense W2K-1 second-hand (~€150-200) → system essentially pays for itself.

---

*Spec version 1.0 — February 2026*
