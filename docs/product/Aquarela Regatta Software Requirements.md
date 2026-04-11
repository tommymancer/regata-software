---
title: "Aquarela Regatta Software — Feature Analysis & Requirements"
created: 2026-02-27
type: project
status: draft
domain: aquarela
tags:
  - type/project
  - domain/sailing
  - domain/software
  - project/aquarela
  - raspberry-pi
  - regatta
related:
  - "[[Aquarela Electronics Inventory]]"
  - "[[Aquarela Performance System]]"
  - "[[Aquarela Nitro 80 Reference]]"
  - "[[Aquarela Njord CSV Spec]]"
summary: "Requirements for a Raspberry Pi-based regatta support software replacing Garmin GNX 20, GNX Wind displays and blending features from Vakaros Atlas 2. Purpose-built for Lake Lugano racing and training aboard the Nitro 80 Aquarela."
---

# Aquarela Regatta Software — Feature Analysis & Requirements

## Part 1: Feature Inventory of Existing Devices

### 1.1 Garmin GNX 20 — Instrument Display

**Category: Data Display**
- Single / dual / triple numeric display modes
- Gauge mode (graphical: wind, depth, speed)
- Graph mode (trend history: wind, depth, speed)
- 4 user profiles (Powerboat, Sail Cruise, Sail Race, Custom)
- Auto-scroll through pages
- Adjustable data damping/filtering (0–9 per data type)
- Configurable alarms (shallow depth, anchor drag, etc.)

**Category: Data Fields (50+)**
- Speed: BSP, SOG, AVG, VMG, VMG-upwind (WND)
- Performance: PBS% (polar boat speed %), TBS% (target boat speed %)
- Wind: AWA, AWS, TWA, TWS, TWD, GWD, GWS, TAWA, TTWA
- Navigation: COG, HDG, BTW, DTW, XTE, CTS
- Environment: Depth, Sea temp, Air temp, Barometer, Humidity
- System: Battery voltage, Rudder angle, Trip, Log, UTC

**Category: Race Features**
- Countdown/countup race timer with sync-to-minute
- Quick access to race timer (hold Menu)
- Virtual start line (requires GPSMAP chartplotter — NOT standalone)
- Sail Race profile preset

**Category: Connectivity**
- NMEA 2000 native (receive all standard PGNs)
- NMEA 0183 input (one device, receive only, optional cable)

---

### 1.2 Garmin GNX Wind + gWind Transducer

**Category: Wind Measurement (gWind hardware)**
- 3-blade propeller: accurate in light air (0.8–90 kn range)
- Twin-fin design: stable angle readings
- Speed accuracy: ±3%, Angle accuracy: ±1.5°
- Wireless model (gWind Wireless 2): ANT protocol, solar-charged NiMH battery

**Category: Wind Data (computed by display/network)**
- Apparent: AWA, AWS (measured directly)
- True: TWA, TWS, TWD (computed from AWA/AWS + BSP + heading)
- Ground: GWD, GWS
- Target angles: TAWA, TTWA (optimal VMG angles from polars)
- Performance: PBS%, TBS%, VMG

**Category: GNX Wind Display Modes**
- True & Apparent Wind Rose (dual needles)
- Close-Hauled Wind Rose (zoomed sector for upwind sailing)
- Wind Direction Rose (TWD relative to north)
- 2 customizable data fields alongside rose

**Category: Steer-Pilot Mode**
- Enter target wind angle → visual steering guide
- AWA mode (wind sensor only) or TWA mode (+ speed sensor)
- Memory function: stores port (MEM1) and starboard (MEM2) tack angles
- Auto-updates tack memory on each tack

**Category: SailAssist (requires GPSMAP chartplotter — NOT standalone)**
- Enhanced wind rose on chartplotter
- Laylines on chart
- Start line guidance with countdown
- Time to burn
- Polar visualization
- Set and drift display

---

### 1.3 Vakaros Atlas 2 — Race Tactical Display

**Category: Sensors (all built-in, no external needed)**
- Dual-band L1+L5 GNSS at 25 Hz (25 cm accuracy)
- 3-axis magnetometer (heading, 0.05° accuracy)
- 3-axis gyroscope (50 Hz motion fusion)
- 3-axis accelerometer
- Barometric pressure sensor
- Ambient light sensor

**Category: Core Measurements**
- Position, SOG, COG, Heading
- Heel angle, Pitch angle
- Leeway angle and velocity
- VMG (configurable averaging window)
- Barometric pressure

**Category: Race Start**
- Ping boat-end and pin-end of start line
- Line length display
- Perpendicular bearing
- Line bias (with shift tracking)
- Distance-to-Line (DTL) — accounts for bow offset
- Time-to-Line (TTL) — learning algorithm based on boat performance model
- Time-to-Burn (TTB)
- Countdown timer with sync
- Graphical starting layout
- Configurable Start Page / Home Page

**Category: Shift Tracking**
- Capture tacking angle, upwind bearing, average speed from short upwind leg
- Reference angles for wind shift detection
- Inferred wind direction (without external wind sensor)
- Line bias from shift data

**Category: Performance / Training**
- VMG with configurable averaging
- Tack/Gybe loss (meters lost/gained vs session average)
- LED feedback: green (above avg), red (below avg), purple (PB)
- Heel consistency tracking
- Stripchart view for trend analysis
- Real-time performance model (learns your boat, no polar setup needed)

**Category: Display**
- 4.4" transflective LCD (320×240, sunlight-readable)
- Up to 10 pages in carousel
- Up to 4 widgets per page (Layout Builder)
- Configurable LED bar (heel, TTL, TTB, shift, tack loss)
- Digits up to 90 mm tall

**Category: Data Logging**
- 256 MB storage, 1/2/5/10 Hz configurable
- 100+ hours capacity
- Logs position, velocity, heading, heel, pitch, barometer
- Export via Vakaros Connect app → SailViewer, Charted Sails, SailNjord

**Category: Connectivity**
- NMEA 2000 via NavLink Blue (receive: wind, BSP, depth, water temp)
- NMEA 2000 transmit planned Spring 2026 (compass, GPS, barometer)
- Bluetooth: Vakaros Connect app, Cyclops load sensors
- Cyclops SmartTune: standing rigging tension (±1% accuracy)
- Cyclops SmartLink: running rigging load (sheets, halyards)

**Category: Class Compliance**
- Per-class feature restrictions
- Tamper-proof audit log

---

## Part 2: Feature Gap Analysis

Features the GNX 20/Wind **cannot do standalone** (need a GPSMAP chartplotter):
- Laylines on chart
- Polar visualization
- Virtual start line guidance
- Time to burn
- Set and drift display
- Advanced wind gauges on chart

Features the Atlas 2 **lacks**:
- Chart/map display (no cartography)
- Built-in wind sensor data (needs NMEA 2000 external)
- Waypoint navigation / routing
- Depth display (needs NMEA 2000 external)
- AIS
- Traditional polar table import (uses learning algorithm instead)

Features **none of the three devices** provide:
- Laylines computed from actual polar data + current (only GPSMAP or dedicated software)
- Weather routing
- Post-race replay on-device
- Trim database / trim book
- Multi-session performance comparison
- Current set/drift computation
- Target speed from stored polars
- Performance % (actual vs polar target)
- Historical wind shift pattern analysis
- Mark rounding optimization

---

## Part 3: Software Landscape for Raspberry Pi

### Recommended Architecture: Custom Software on Signal K Stack

After evaluating all options:

| Software | RPi Native | Racing Features | Open Source | Verdict |
|----------|-----------|-----------------|-------------|---------|
| Expedition | No (Windows) | Gold standard | No ($1,295) | Cannot run on Pi |
| Adrena | No (Windows) | Excellent + TrimBook | No (expensive) | Cannot run on Pi |
| OpenCPN + Tactics | Yes | Good (laylines, polars, VMG) | Yes (free) | Chartplotter, not ideal as primary racing display |
| qtVlm | Yes | Basic start line, routing | Free | Routing tool, not racing display |
| Signal K + plugins | Yes | Basic (signalk-racer) | Yes (free) | Middleware, not complete solution |
| Tactiqs | No (iOS) | Excellent (62 metrics) | No | Cannot run on Pi |
| SailRacer | No (mobile) | Good start features | Partial | Companion, not primary |

**Conclusion:** No existing software delivers a complete, polished regatta racing display on Raspberry Pi. The best approach is a **custom application** built on top of:

1. **Signal K** — as the data middleware (NMEA 2000 → structured JSON)
2. **Custom web UI** — purpose-built racing dashboard (replaces GNX 20 + GNX Wind screens)
3. **Python/Node.js backend** — polar engine, race logic, data logging

This extends the existing [[Aquarela Performance System]] plan from a simple logger to a full racing instrument system.

---

## Part 4: Requirements Specification

### 4.0 Design Principles

- **Crew-first**: Information hierarchy optimized for a 5-person Nitro 80 crew
- **Glanceable**: Large digits, high contrast, readable at 2+ meters in sunlight
- **Lake Lugano context**: No ocean routing, no tides; focus on thermal wind patterns, short courses, and close racing
- **Complement Atlas 2**: The Pi display handles instrument data and performance; the Atlas 2 handles start line and shift tracking
- **Minimal interaction while racing**: Pages auto-cycle or are pre-configured before start; no fiddling with menus mid-race
- **Training-oriented**: Every session produces analyzable data; trim changes are recordable

---

### 4.1 Core Instrument Display (replaces GNX 20 + GNX Wind)

#### 4.1.1 Numeric Data Fields

All fields from GNX 20 + GNX Wind, computed on-device from raw NMEA 2000:

| Field | Abbr | Source | Priority |
|-------|------|--------|----------|
| Boat Speed (through water) | BSP | Airmar 128259 | Critical |
| Speed Over Ground | SOG | GPS 129026 | Critical |
| True Wind Angle | TWA | Computed: AWA + BSP + HDG | Critical |
| True Wind Speed | TWS | Computed: AWS + BSP + HDG | Critical |
| True Wind Direction | TWD | Computed: TWA + HDG | Critical |
| Apparent Wind Angle | AWA | gWind 130306 | Critical |
| Apparent Wind Speed | AWS | gWind 130306 | Critical |
| Heading (magnetic) | HDG | GPS 127250 | Critical |
| Course Over Ground | COG | GPS 129026 | Critical |
| VMG (to wind) | VMG | Computed: BSP × cos(TWA) | Critical |
| Depth | DPT | Airmar 128267 | High |
| Water Temperature | SEA | Airmar 130310 | Medium |
| Target TWA | TTWA | From polar table | High |
| Target BSP | TBSP | From polar table at current TWS/TWA | High |
| Polar Performance % | PERF% | BSP / TBSP × 100 | High |
| VMG Performance % | VMGP% | VMG / Target VMG × 100 | High |
| Leeway | LEE | Computed: HDG vs COG, or heel-based model | Medium |
| Current Set | SET | Computed: vector diff BSP/HDG vs SOG/COG | Medium |
| Current Drift | DRF | Computed: magnitude of current vector | Medium |
| Battery Voltage | BAT | NMEA 127508 (if available) | Low |
| Trip Distance | TRP | Accumulated from BSP or SOG | Low |

#### 4.1.2 Wind Rose Display

Replaces GNX Wind display with enhanced version:

- **Combined Wind Rose**: Apparent (filled needle) + True (outline needle) on single rose
- **Close-Hauled Mode**: Zoomed 60° sector for upwind legs, shows TWA and target TWA with visual delta
- **Downwind Mode**: Zoomed sector for VMG angles downwind
- **Wind Direction Mode**: TWD relative to north, with shift history indicator
- **Target angle markers**: Visual marks on rose showing TTWA from polar table
- **Port/starboard tack memory**: Display current tack angles with one-tap store/recall

#### 4.1.3 Graphical Displays

- **Speed strip chart**: BSP and SOG trend over configurable time window (2/5/10 min)
- **Wind trend chart**: TWS and TWD over configurable window
- **Performance gauge**: Circular gauge showing PERF% (0–120%), color-coded zones
- **Heel gauge**: Real-time heel from Atlas 2 IMU data (via NMEA 2000 when available)

#### 4.1.4 Display Configuration

- **Configurable pages**: Up to 8 pages in swipeable carousel
- **Layout templates**: 1-field (huge digits), 2-field (split), 3-field (one large + two small), 4-field (quad), wind rose + 2 fields
- **Pre-race / Race / Downwind presets**: Auto-switch based on TWA or manual selection
- **Font sizes**: Primary field up to 80mm equivalent on 7" display, readable at 3m
- **Color themes**: Day mode (black on white), Night mode (red on black), High contrast
- **Auto-brightness**: Via ambient light or time-of-day

---

### 4.2 Performance Engine (new — not in any existing device standalone)

#### 4.2.1 Polar Table Management

- **Import polars**: CSV format (TWS columns × TWA rows → BSP values)
- **Manual polar entry**: For boats without published polars (Nitro 80)
- **Polar learning mode**: Record BSP at each TWA/TWS combination over multiple sessions; build empirical polar from real data
- **Polar envelope display**: Show polar diagram with current point plotted
- **Multiple polar sets**: Compare e.g. "old jib" vs "new jib", or "flat water" vs "chop"

#### 4.2.2 Target Speed & Angle Calculation

- **Optimal VMG upwind**: Target TWA and target BSP for current TWS
- **Optimal VMG downwind**: Target TWA and target BSP for current TWS
- **Interpolation**: Smooth interpolation between polar table entries
- **Performance %**: Instantaneous and averaged (configurable: 30s, 1 min, 5 min)
- **Delta displays**: Δ BSP (actual − target), Δ TWA (actual − optimal)

#### 4.2.3 Layline Computation

- **Upwind laylines**: Based on current TWD + target TWA + leeway + current
- **Downwind laylines**: Based on TWD + optimal downwind angle
- **Layline display on wind rose**: Visual markers showing when to tack/gybe
- **Overshoot/undershoot indicator**: How far past or short of layline

#### 4.2.4 Current Estimation

- **Set and drift**: Computed from BSP+HDG vs SOG+COG vectors
- **Running average**: Smoothed over configurable window (2–10 min)
- **Current-compensated laylines**: Laylines adjusted for measured current
- **Current display**: Arrow overlay showing direction and magnitude

---

### 4.3 Race Support

#### 4.3.1 Race Timer

- **Countdown timer**: 1–10 min configurable, default 5 min
- **Sync function**: Tap to sync to next full minute (up/down)
- **Audio signals**: Beeps at 5, 4, 3, 2, 1 min and at start (via Pi audio or BLE to phone)
- **Count-up after start**: Elapsed race time
- **Quick access**: Dedicated button/gesture from any page

#### 4.3.2 Start Line Support (complement to Atlas 2)

Note: Atlas 2 handles primary start line functions (DTL, TTL, TTB, line bias). The Pi software provides complementary data:

- **Line bearing display**: Show start line bearing and perpendicular
- **Favored end calculation**: Using TWD relative to line bearing
- **Speed check**: Real-time BSP readout in large digits for line approach
- **Pre-start page**: Auto-displays 2 min before start — BSP, countdown, TWA, HDG

#### 4.3.3 Mark Rounding

- **Mark waypoints**: Store lat/lon of race marks (manually or from predefined courses)
- **Distance/bearing to next mark**: BTW and DTW
- **Layline to mark**: When to tack/gybe for the mark, accounting for current
- **ETA to mark**: Based on current VMG or target speed

#### 4.3.4 Lake Lugano Course Database

- **Pre-stored courses**: Common regatta courses on Lake Lugano (CVLL, other clubs)
- **Mark positions**: Database of known racing marks
- **Quick course selection**: Select course before race → marks auto-loaded
- **Course leg display**: Current leg, next mark, bearing, distance

---

### 4.4 Training & Trim Analysis

#### 4.4.1 Session Management

- **Auto-start logging**: Begin recording when BSP > 1 kn (or manual start)
- **Auto-stop**: Stop after 5 min of BSP = 0 (or manual stop)
- **Session metadata**: Date, crew, wind conditions (avg TWS, TWD), lake conditions
- **Session notes**: Voice memo or text note (via phone companion) timestamped to session

#### 4.4.2 Trim Book (inspired by Adrena TrimBook)

- **Trim snapshot**: At any moment, crew can "bookmark" current trim settings
- **Recorded parameters**: Timestamp, TWS, TWA, BSP, PERF%, heel, plus:
  - Backstay tension (none on Nitro 80 — skip)
  - Cunningham
  - Outhaul
  - Vang/kicker
  - Jib sheet lead position
  - Jib halyard tension
  - Traveller position
  - Forestay tension (mast rake indicator)
- **Input method**: Quick-select values on phone companion (presets: 1-5 scale or specific detent positions)
- **Trim comparison**: Compare bookmarks — "at 12 kn TWS upwind, trim set A gave 5.8 kn BSP vs trim set B gave 5.6 kn"
- **Best trim recall**: Given current conditions, show the trim settings that produced the best PERF% historically

#### 4.4.3 Rig Tuning Support

- **Shroud tension recording**: Manual entry or Cyclops SmartTune integration
- **Mast rake measurement**: Derived from forestay length / halyard measurement, manual entry
- **Rig preset database**: Store named setups (e.g., "light air flat water", "heavy air chop")
- **Rig vs performance correlation**: Over multiple sessions, show which rig setup produced the best polars

#### 4.4.4 Maneuver Analysis

- **Tack detection**: Automatic detection from heading change > 60° in < 15s
- **Tack metrics**: Speed before, minimum speed during, speed recovery time, distance lost
- **Gybe detection**: Automatic from heading change on downwind leg
- **Gybe metrics**: Same as tack
- **Session tack/gybe summary**: Average loss, best, worst, trend over session
- **Comparison with Atlas 2**: Atlas 2 also logs tack/gybe loss — cross-reference data

#### 4.4.5 Performance Logging & Export

- **High-rate logging**: 1–10 Hz configurable (all NMEA data + computed fields)
- **CSV export**: Compatible with Njord Analytics (see [[Aquarela Njord CSV Spec]])
- **GPX export**: Track file for mapping tools
- **Polar scatter plot**: Post-session view of all BSP points plotted on polar diagram
- **Session comparison**: Overlay two sessions to see improvement
- **Trim correlation report**: Which trim changes moved PERF% and by how much

---

### 4.5 Data Infrastructure

#### 4.5.1 NMEA 2000 Interface

- **Hardware**: Waveshare 2-CH CAN HAT (or PiCAN-M) on Raspberry Pi 4
- **Protocol**: SocketCAN at 250 kbps
- **PGN decoding**: Via canboat or python-can + custom decoder
- **Supported PGNs (receive)**:

| PGN | Data | Source Device |
|-----|------|---------------|
| 127250 | Vessel Heading | GPS 24xd |
| 127258 | Magnetic Variation | GPS 24xd |
| 128259 | Water Speed (BSP) | Airmar Smart TRI |
| 128267 | Water Depth | Airmar Smart TRI |
| 129025 | Position Rapid Update | GPS 24xd |
| 129026 | COG/SOG Rapid Update | GPS 24xd |
| 129029 | GNSS Position Data | GPS 24xd |
| 130306 | Wind Data (AWA/AWS) | gWind |
| 130310 | Environmental (water temp) | Airmar Smart TRI |
| 127508 | Battery Status | (if available) |

- **Future (Atlas 2 NMEA transmit, Spring 2026)**:
  - Heading (magnetometer), heel, pitch from Atlas 2 IMU
  - High-accuracy GPS from Atlas 2 L1+L5

#### 4.5.2 Computed Data Pipeline

```
Raw NMEA → PGN Decode → Calibration Corrections → True Wind Calc → Performance Calc → Display + Log
                              ↑                         ↑
                        [Calibration DB]          [Polar Tables]
```

- **Calibration**: Speed factor, depth offset, wind angle offset, heading deviation (see existing calibration wizard)
- **True wind calculation**: Standard formulas using AWA, AWS, BSP, HDG
- **Damping/filtering**: Configurable per field (moving average window 1–30s)
- **Derived fields**: VMG, leeway, current, performance %, target angles

#### 4.5.3 Data Storage

- **Session database**: SQLite for metadata, trim entries, marks, courses
- **Time-series log**: CSV or lightweight time-series DB (InfluxDB optional)
- **Polar database**: JSON/CSV polar tables with versioning
- **Configuration**: YAML/JSON for all user preferences, page layouts, alarm thresholds

#### 4.5.4 Connectivity

- **WiFi hotspot**: SSID "Aquarela", password-protected
- **Web dashboard**: Accessible at http://aquarela.local from any phone/tablet
- **WebSocket**: Real-time data streaming to browser clients
- **USB**: Direct file access for CSV download
- **Future**: Signal K server for interoperability with other marine apps

---

### 4.6 Hardware & Display

#### 4.6.1 Display Options

| Option | Size | Resolution | Sunlight | Touch | Notes |
|--------|------|-----------|----------|-------|-------|
| Official RPi 7" Touchscreen | 7" | 800×480 | Moderate | Yes | Low cost (~€70), moderate sunlight readability |
| Waveshare 7" IPS | 7" | 1024×600 | Good | Yes | Better resolution, IPS viewing angles |
| Waveshare 10.1" IPS | 10.1" | 1280×800 | Good | Yes | Larger, better for multi-field layouts |
| Sunlight-readable industrial | 7-10" | Various | Excellent | Optional | Expensive (~€200-400) but race-grade visibility |

**Recommendation**: Start with 7" IPS touchscreen; upgrade to sunlight-readable if needed after testing.

#### 4.6.2 Enclosure

- IP67 waterproof enclosure with clear window for display
- Mounting: cockpit bulkhead (replacing or adjacent to GNX 20/Wind positions)
- Physical buttons: 3-4 waterproof buttons for page navigation and race timer (touchscreen unreliable with wet hands)
- Status LED: visible green (logging), red (error), blue (WiFi active)

#### 4.6.3 Power

- 12V from boat battery via fused connection
- 12V → 5V step-down converter (3A+, USB-C to Pi)
- Power consumption: Pi 4 (~5W) + display (~3W) = ~8W total
- Battery impact: 8W / 12V = 0.67A → manageable on 96Wh battery for ~12h racing day

---

### 4.7 User Interface Architecture

#### 4.7.1 Technology Stack

- **Frontend**: Web-based (HTML5/CSS/JS) served from Pi, rendered in Chromium kiosk mode
- **Framework**: React or Svelte for reactive updates
- **Backend**: Python (FastAPI) or Node.js
- **Data protocol**: WebSocket for real-time instrument data (10-20 Hz update)
- **Phone companion**: Same web UI, responsive design, accessed via WiFi

#### 4.7.2 Screen Hierarchy

```
[Boot] → [Instrument Dashboard] ← swipe/button → [Pages]
                                                    ├── Page 1: Upwind (TWA, BSP, PERF%, VMG, target TWA)
                                                    ├── Page 2: Wind Rose (combined AWA/TWA + targets)
                                                    ├── Page 3: Downwind (TWA, BSP, SOG, VMG)
                                                    ├── Page 4: Navigation (HDG, COG, BTW, DTW)
                                                    ├── Page 5: Performance (polar gauge, strip chart)
                                                    ├── Page 6: Race Timer (countdown + BSP + TWA)
                                                    ├── Page 7: Trim Entry (quick-select interface)
                                                    └── Page 8: System (battery, GPS status, logging status)

[Phone Companion] → same pages + session management + trim book + file download
```

#### 4.7.3 Interaction Model

- **On-screen (Pi display)**: Swipe left/right for pages, physical buttons for race timer
- **On phone**: Full touch interface, session start/stop, trim entry, notes, file management
- **Voice (future)**: Announce key data changes (wind shift > 10°, performance drop, mark approach)

---

### 4.8 Alarms & Notifications

| Alarm | Trigger | Output |
|-------|---------|--------|
| Shallow water | Depth < configurable threshold | Visual flash + audio beep |
| Wind shift | TWD change > 10° in 2 min | Visual indicator on wind rose |
| Performance drop | PERF% < 80% sustained 30s | Color change on performance field |
| Layline reached | Approaching tack/gybe point | Visual flash on bearing display |
| Low battery | Battery < 11.5V | System page warning |
| Race timer | 5, 4, 3, 2, 1 min + start | Audio sequence |
| GPS loss | No position fix for 10s | System page warning |
| Sensor loss | Any NMEA source missing > 30s | Affected field shows "---" |

---

## Part 5: Development Phases

### Phase 1: Data Pipeline & Basic Display (MVP)
- NMEA 2000 → CAN HAT → PGN decode → computed fields
- Single-page numeric display (BSP, TWA, TWS, VMG, HDG, SOG)
- CSV logging (Njord-compatible)
- WiFi hotspot + web access
- **Replaces**: Actisense W2K-1 logger
- **Timeline target**: First on-water test

### Phase 2: Full Instrument Display
- Multi-page carousel with configurable layouts
- Wind rose display (AWA + TWA + targets)
- Strip charts (speed, wind trends)
- Day/night color modes
- Physical button support
- **Replaces**: GNX 20 and GNX Wind displays (can be kept as backup)

### Phase 3: Performance Engine
- Polar table import/management
- Target speed and angle computation
- Performance % display
- Layline indicators
- Current set/drift estimation
- Polar learning mode (build empirical polars from session data)

### Phase 4: Race Support
- Race countdown timer with audio
- Mark waypoint database
- Lake Lugano course database
- BTW/DTW to next mark
- Layline to mark with current compensation
- Pre-start page auto-switch

### Phase 5: Training & Trim
- Trim book interface (phone companion)
- Rig setup database
- Tack/gybe detection and loss metrics
- Session comparison tools
- Trim vs performance correlation
- Best trim recall for current conditions
- Cyclops load sensor integration (when available)

### Phase 6: Polish & Advanced
- Voice announcements
- Session auto-upload to Njord on home WiFi
- Signal K server for third-party app compatibility
- Performance report generation (PDF/HTML summary per session)
- Multi-session trend analysis dashboard
- Integration with Atlas 2 NMEA transmit (heel, pitch, high-accuracy GPS)

---

## Part 6: Lake Lugano Specific Considerations

- **Thermal winds**: Lake Lugano has predictable thermal wind patterns (morning calm → afternoon southerly "Breva" or northerly "Tivano"). Wind shift tracking is critical.
- **Short courses**: Regatta courses are typically short (windward-leeward or triangle), so response time matters more than routing.
- **Flat water → chop transition**: Wind builds with chop on the lake; different polars may apply. Consider chop-adjusted polar sets.
- **No tides or significant current**: Current computation is less critical but still useful for detecting localised flows near shore.
- **Depth**: Lake is deep (> 200m in places); depth alarm mainly relevant near shore/marks.
- **Known mark positions**: CVLL and local club marks are fixed or semi-permanent; store in database.
- **Short sailing days**: Racing is typically afternoons; system must boot fast and be ready quickly.
- **Limited power budget**: 96Wh battery (planned upgrade to 256Wh). Every watt matters. System should be as lean as possible.

---

## Part 7: Success Criteria

The software succeeds when:

1. **The crew can read BSP, TWA, TWS, VMG, and PERF% at a glance from 2 meters away** — matching or exceeding GNX 20/Wind readability
2. **Target angles from polars are always visible** — every tack and gybe is informed by data, not guesswork
3. **Every session produces a complete, clean dataset** — uploadable to Njord within 2 minutes of docking
4. **Trim changes are recorded and correlated** — after 10 sessions, the crew knows the optimal trim for any condition on Lake Lugano
5. **The system boots and is operational within 60 seconds** of power-on
6. **The Atlas 2 remains the primary start line tool** — the Pi complements, not duplicates, its strengths

---

*Document version 1.0 — 27 February 2026*
*Boat: Nitro 80 "Aquarela" — Lake Lugano*
