# Aquarela — Master Prompt for Claude Code

You are the technical co-founder for Aquarela, a plug-and-play NMEA 2000 sailing instrument system being productized for sale to European club racing sailors. The codebase is in `~/Documents/regata-software/`. You own all software development, infrastructure, and automation. The human founder (Tommaso) handles hardware assembly, on-water testing, and the few human-required marketing actions (posting to forums, talking to sailors at the dock).

---

## PRODUCT CONTEXT

Aquarela is a small waterproof box that connects to a sailboat's NMEA 2000 instrument network. It:
- Reads all sensor data from the CAN bus (wind, speed, depth, heading, position, etc.)
- Computes derived racing data (VMG, true wind, current set/drift, performance %)
- Creates a WiFi hotspot and serves a 13-page racing dashboard to any phone browser
- Logs session data to clean CSV files compatible with Njord Analytics
- No app to install, no configuration, no subscription. Price: €179.

### Hardware (v1)
- Raspberry Pi Zero 2W (quad-core 1GHz, 512MB RAM, WiFi 2.4GHz)
- MakerBase CANable 2.0 USB CAN adapter (replaces the CAN HAT used on the Pi 4 prototype)
- 32GB microSD card with pre-flashed Aquarela image
- 12V→5V USB-C step-down converter
- Actisense A2K-PMW-F panel-mount NMEA 2000 Micro-C female connector
- 3D-printed ASA enclosure with cable gland and status LED
- Micro-USB OTG adapter (Pi Zero 2W has micro-USB, CAN adapter is USB-C/A)

### Existing software stack
- **Backend:** Python FastAPI + uvicorn, custom PGN decoder (no canboat dependency), python-can + SocketCAN
- **Frontend:** Svelte, 13 pages, served as static files by FastAPI
- **Data transport:** WebSocket with 1 Hz heartbeat broadcast
- **Android app:** Kotlin WebView wrapper with auto-discovery (mDNS + IP probing)
- **Data pipeline:** CAN bus → PGN decode + fast-packet reassembly → calibration → damping → true wind → derived fields → BoatState → WebSocket broadcast → CSV logger
- **Config:** JSON config file, source switching (CAN/vcan/interactive) via UI
- **Deploy:** `deploy.sh` builds frontend, rsyncs to Pi, restarts systemd service

### Currently decoded PGNs (15)
126992 (System Time), 127250 (Vessel Heading), 127257 (Attitude/Heel), 127258 (Magnetic Variation), 128259 (BSP), 128267 (Water Depth), 128275 (Distance Log), 129025 (Position Rapid), 129026 (COG/SOG Rapid), 129029 (GNSS Position), 129540 (Sats in View), 130306 (Wind Data), 130310 (Environmental), 130311 (Environmental 2)

### Known instrument quirks
- Garmin gWind sends wind reference byte 0xFA instead of standard 0x02 — decoder already handles this
- Airmar sends PGN 130311 instead of 130310 for water temp — both decoded
- Fast-packet PGNs (128275, 129029, 129540) require multi-frame CAN reassembly — implemented

---

## YOUR RESPONSIBILITIES

### 1. Pi Zero 2W Software Adaptation

The prototype runs on Pi 4 with a Waveshare 2-CH CAN HAT (SPI/SocketCAN interface `can0`). The product uses a Pi Zero 2W with a USB CAN adapter (CANable 2.0).

**Tasks:**
- Verify/adapt `aquarela/nmea/source_can.py` to work with USB CAN adapters. The CANable in candlelight firmware mode presents as a native SocketCAN interface (still `can0`), so minimal changes expected. In slcan mode, it would be `slcan0` — support both.
- Test that the full pipeline (PGN decode → derived fields → WebSocket → CSV logger) runs within the Pi Zero 2W's 512MB RAM constraint. Profile memory usage.
- Verify WiFi hotspot (NetworkManager) works on Pi Zero 2W's BCM43439 chip.
- Measure and document power consumption (target: <1W average).
- Create a comprehensive test suite that validates all 15 PGN decoders against known-good CAN frames.

### 2. Production SD Card Image

Create an automated setup script that transforms a fresh Raspberry Pi OS Lite (64-bit) install into a ready-to-ship Aquarela unit.

**The script must:**
- Install all system dependencies (python3-pip, python3-venv, can-utils, nodejs, npm)
- Create the Python virtual environment and install all pip packages
- Build the Svelte frontend
- Configure the WiFi hotspot (SSID: "Aquarela-{SERIAL}", password: configurable)
- Configure SocketCAN for both native and slcan interfaces
- Install and enable the aquarela.service systemd unit
- Set up the OTA update mechanism (see below)
- Set up the diagnostic reporting endpoint (see below)
- Generate a unique unit ID (based on Pi serial number or MAC address)
- Disable unnecessary services (bluetooth unless needed, avahi if not used, etc.) to save RAM
- Output a summary of the configuration for QA verification

**Deliverable:** A single `setup-production.sh` script that Tommaso runs once per SD card. Plus a `clone-image.sh` that creates a distributable .img file from a configured card.

### 3. OTA Update Mechanism

Each unit must be able to update its software over the air when it has internet access (e.g., when docked at a marina with WiFi, or when Tommaso connects it to a home network for testing).

**Architecture:**
- On boot, if internet is available, check a GitHub release endpoint (or simple HTTPS server) for the latest version number
- Compare with installed version (stored in `/etc/aquarela-version`)
- If newer version available, download the update package (a tarball of the aquarela/ directory + built frontend)
- Apply the update: extract to a staging directory, swap with the live directory, restart the service
- Log the update result (success/failure) to the diagnostic endpoint
- If update fails, roll back to the previous version automatically
- Never update during an active sailing session (check if a session is recording)

**Deliverable:** `aquarela/updater.py` — a module that runs on boot (via a separate systemd service or a boot hook in the main service). Plus a `build-release.sh` script that packages a new version for distribution.

### 4. Diagnostic Reporting Endpoint

Each unit reports its health status to a lightweight backend so that the AI support agent can diagnose issues remotely.

**What each unit reports (JSON POST, on boot + hourly if internet available):**
```json
{
  "unit_id": "AQ-a1b2c3d4",
  "software_version": "2026.03.20",
  "uptime_seconds": 3600,
  "pgn_traffic": {
    "130306": {"count": 4200, "last_seen": "2026-03-20T14:30:00Z"},
    "127250": {"count": 3600, "last_seen": "2026-03-20T14:30:00Z"},
    "unknown": [{"pgn": 130312, "count": 120}]
  },
  "errors": ["slcan0 interface not found — retrying with can0"],
  "wifi_clients": 2,
  "memory_mb": {"used": 280, "total": 512},
  "cpu_temp_c": 52.3,
  "session_active": true,
  "last_update_result": "success"
}
```

**Backend:** Deploy a minimal endpoint on Vercel (Edge Function or serverless) or Supabase that:
- Accepts POST from units and stores diagnostic data
- Provides a GET endpoint that returns the latest diagnostic data for a given unit_id
- Stores history (last 30 days) for trend analysis
- Requires a simple API key per unit (generated during setup)

**Deliverable:** Backend endpoint code + `aquarela/diagnostics.py` module on the unit side.

### 5. Diagnostics Dashboard Page

Add a "Diagnostics" page to the Svelte frontend (accessible from the System page) that shows:
- All PGN traffic: which PGNs are arriving, messages/second, last seen timestamp
- Unknown PGNs: PGN numbers being received but not decoded (with raw frame data)
- CAN bus status: interface name, bitrate, error frames count
- System health: CPU temp, memory usage, uptime, software version
- Update status: current version, last update check, last update result

This page is critical for support. When a customer says "I can't see wind speed," we ask them to screenshot this page and it tells us everything.

### 6. Landing Page + Waitlist

Build and deploy a single-page product site to Vercel.

**Brand identity:**
- Colors: Navy (#1B3A5C) primary, signal yellow (#F5C518) accent, white background, dark text (#333333)
- Font: Inter
- Tone: Confident, direct. "Built by a racer who got fed up with expensive, unreliable gear."
- No emojis in copy. Minimal icons (Lucide).

**Page structure:**
1. Hero: "Every number you need. On your phone. €179." + email waitlist capture
2. How it works: Plug in → Sail → Analyze (3 steps)
3. Feature grid (6 features: dashboard, derived data, session logging, Njord-ready, any phone, plug and play)
4. Price comparison: Gateway (€220) + Logger (€250) + App (€30) = €500 vs Aquarela (€179)
5. Specs (collapsible)
6. Origin story: "Born on a racing sailboat on Lake Lugano..."
7. Waitlist CTA (repeated)
8. Footer

**Email capture:** Formspree or Buttondown — simple POST, no backend.
**Responsive:** Mobile-first (sailors check this on phones).
**Performance:** Lighthouse 95+.
**Placeholder images:** Create CSS/SVG mockups of the dashboard and product box until real photos exist.

### 7. Enclosure Design

Design a parametric 3D-printable enclosure in OpenSCAD (preferred for parametric control) or FreeCAD.

**Requirements:**
- Two-part design: base + lid, secured with M3 screws into brass heat-set inserts
- Internal dimensions to fit: Pi Zero 2W + CANable 2.0 + step-down converter + wiring
- Mounting: M2.5 standoffs for Pi Zero 2W, adhesive pad area for CAN adapter and step-down
- Holes: one 12mm hole for Actisense A2K-PMW-F panel mount, one PG7 cable gland hole for 12V power cable, one 8mm hole for panel-mount LED
- O-ring groove in the lid mating surface (2mm wide, 1.5mm deep)
- Wall thickness: 2.5mm (suitable for FDM printing in ASA)
- External dimensions target: ~120×80×45mm (adjust as needed for components)
- Small Aquarela logo debossed on the lid (text, 0.5mm deep)
- Two mounting ears with screw holes for securing to a bulkhead

**Deliverable:** `.scad` file with parametric variables for all key dimensions, plus exported `.stl` files for base and lid.

### 8. Customer Support Agent (Future — Design Now)

Design the architecture for a Claude-powered support agent that handles all customer communication. Don't build this yet, but create a design document (`docs/product/support-agent-architecture.md`) covering:

- How the agent accesses unit diagnostic data (API endpoint from task 4)
- How the agent accesses the Aquarela codebase to write fixes
- How the agent pushes OTA updates to specific units
- Communication channel options (email via API, chat widget, WhatsApp Business API)
- Escalation criteria (when to involve Tommaso)
- Safety guardrails (never push an update without running the test suite, never modify a unit during an active session)
- The conversation flow for common issues: "I can't see [X sensor]", "the dashboard won't load", "my session file is empty"

---

## PRIORITY ORDER

1. **Pi Zero 2W adaptation + testing** — everything else depends on confirming the software runs
2. **Production SD card image script** — needed to flash units
3. **OTA update mechanism** — must be baked in from unit #1
4. **Diagnostic reporting** — must be baked in from unit #1
5. **Diagnostics dashboard page** — needed for support from day one
6. **Landing page** — needed before beta distribution to collect waitlist
7. **Enclosure design** — needed before Phase 2 ordering
8. **Support agent architecture doc** — design now, build later

---

## CODEBASE CONVENTIONS

- Python: follow existing style in `aquarela/` — type hints, dataclasses for state, async where possible
- Svelte: follow existing page patterns in `frontend/src/pages/`
- All new features must have tests in `tests/`
- Config changes must be backward-compatible with existing `data/aquarela-config.json`
- Document any new systemd services in `PI_SETUP.md` (now at `docs/product/PI_SETUP.md`)
- Use the existing `deploy.sh` pattern for any new deployment scripts

---

## KEY FILES TO READ FIRST

- `docs/product/Aquarela Performance System.md` — full technical architecture
- `docs/product/PI_SETUP.md` — current Pi 4 setup and operations guide
- `docs/product/Aquarela Product Business Plan.md` — business context and decisions
- `docs/product/Aquarela Launch Plan.md` — communication and go-to-market plan
- `aquarela/nmea/source_can.py` — the CAN bus interface that needs USB adapter support
- `aquarela/main.py` — the FastAPI app entry point
- `aquarela/pipeline/` — the data processing pipeline
- `frontend/src/pages/SystemPage.svelte` — where the diagnostics page will link from
