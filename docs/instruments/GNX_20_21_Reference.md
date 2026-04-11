# Garmin GNX 20/21 — Quick Reference

*Based on Owner's Manual, March 2016 (190-01659-00_0C)*

---

## Overview

The GNX 20/21 is a marine instrument display that shows data from sensors via NMEA 0183 networks. It can also receive data from Nexus instruments and sensors using a GND 10 bridge device (sold separately). Certain functions require appropriate sensors to be connected.

---

## Button Controls

| Button | Action |
|--------|--------|
| ☰ (menu) | Return to previous menu or instrument page |
| ▶ | View menu for an instrument page |
| ◀ / ▶ | Scroll through instrument pages and menus |
| ☀ (display) | View display settings (press once) / backlight (press twice) |
| ☀ (hold) | Power-off settings |

---

## Profiles

Profiles are collections of instrument pages grouped around a use case. You can switch profiles at any time.

### Available Profiles

| Profile | Default Instruments |
|---------|-------------------|
| **POWERBOAT** | GPS speed, GPS course, depth, bearing to waypoint, distance to next waypoint, water temperature |
| **SAIL CRUISE** | True wind speed, GPS speed, GPS course, bearing to waypoint, distance to next waypoint, true wind angle, depth |
| **SAIL RACE** | GPS speed, true wind speed, true wind angle, heading, bearing to waypoint, distance to next waypoint |
| **CUSTOM** | Speed over ground (default); fully customizable |

### How to Select a Profile

`☰ → SETUP → PROFILES → [select profile]`

### Reset Profiles to Factory Defaults

`☰ → SETUP → PROFILES → RESET DEFAULTS → CURRENT PROFILE / ALL PROFILES`

---

## Instrument Pages

### Cycling Through Pages

Press ◀ or ▶ from the home page.

### Auto Scroll

`☰ → SETUP → AUTO SCROLL → [set time interval]`

Setting the time to zero disables auto scroll.

### Configuring Data Fields

`☰ → CONFIGURE DATA FIELDS`

### Configuring Graph Data Fields

`☰ → CONFIGURE DATA FIELDS → GRAPH SETTINGS`

- **GRAPH DURATION** — how long data is displayed on the graph
- **GRAPH SCALE** — the scale of values shown

### Changing Page Layout

Each page can display up to 3 data fields.

`☰ → EDIT CURRENT PAGE → CHANGE LAYOUT → [select number of fields] → [assign data to each field] → DONE`

### Adding a Page

`☰ → ADD/REMOVE PAGE → ADD PAGE → [ONE / TWO / THREE FUNCTION] → [select collection] → [select instrument]`

### Removing a Page

Navigate to the page, then: `☰ → ADD/REMOVE PAGE → REMOVE PAGE → YES`

---

## Race Timer

The race timer counts down to a race start and then measures race duration. It can be added as a data field on any page.

**Quick access:** Hold ☀ from a main page.

### Controls (via ☰ → CONFIGURE DATA FIELDS → RACE TIMER SETTINGS)

| Mode | Available Actions |
|------|-------------------|
| **Pre-race, stopped** | RESET, START, SETUP |
| **Pre-race, running** | Sync to next minute up/down, STOP |
| **Race mode, counting up** | Sync back to 0:00, STOP |

---

## Device Configuration

### Resolving a Combined Network

If the device was previously on another vessel's network, it detects the conflict on startup.

`☰ → SETUP → COMBINED NETWORKS DETECTED`

- **NO** — sync existing network instruments to this device
- **YES** — sync this device to existing network instruments

### System Settings

`☰ → SETUP → SYSTEM`

| Setting | Description |
|---------|-------------|
| **UNITS** | Units of measure |
| **HEADING** | North reference and variance for heading calculation |
| **BEEPER** | Audible key-press sounds |
| **GPS POSITION** | Position format and map datum |
| **AUTO POWER** | Auto-on when NMEA network powers on |
| **LANGUAGE** | On-screen language |
| **TIME** | Time format, time zone, daylight saving |
| **SYSTEM INFORMATION** | Software version info |
| **FACTORY DEFAULT** | Full factory reset |

### Heading Type

`☰ → SETUP → SYSTEM → HEADING → NORTH REFERENCE`

- **MAGNETIC** — auto-set magnetic declination from GPS
- **TRUE** — true north
- **GRID** — grid north (000°)

### Beeper

`☰ → SETUP → SYSTEM → BEEPER`

### Position Format

`☰ → SETUP → SYSTEM → GPS POSITION`

- **POSITION FORMAT** — coordinate display format
- **MAP DATUM** — coordinate system for the chart

> Do not change these unless your chart specifies a different format.

### Data Sources

`☰ → SETUP → DATA SOURCES → [select source] → [select instrument] → [configure]`

---

## Display Settings

`☰ → SETUP → DISPLAY`

| Setting | Description |
|---------|-------------|
| **BACKLIGHT** | Brightness level |
| **COLOR** | Screen color scheme |
| **NETWORK SHARING** | Share color/backlight with other NMEA 2000 or NMEA 0183 devices |

---

## NMEA Settings

`☰ → SETUP → NMEA 0183 / NMEA 2000 DEVICES`

- **DEVICE LIST** — view software version, serial number
- **LABEL DEVICES** — change device labels

Each NMEA-certified sensor provides unique data types. The data available on the display depends on which sensors are installed. See Garmin's Technical Reference for NMEA Products for full data-type requirements.

---

## Data Fields Reference

| Abbreviation | Meaning |
|-------------|---------|
| **ABS** | Absolute value (e.g., absolute humidity) |
| **AIR** | Air temperature |
| **AVG** | Average amount |
| **AWA** | Apparent wind angle (relative to bow) |
| **AWS** | Apparent wind speed (measured) |
| **BAR** | Barometric pressure (calibrated) |
| **BAT** | Battery voltage |
| **BSP** | Boat speed through water |
| **BTW** | Bearing to waypoint (requires active navigation) |
| **COG** | Course over ground |
| **CTS** | Course to steer (to return to original course line) |
| **DIS** | Distance traveled (current track/activity) |
| **DPT** | Water depth (requires depth-capable NMEA device) |
| **DRF** | Current speed (drift) |
| **DTW** | Distance to waypoint |
| **ELV** | Elevation above/below sea level |
| **ERR** | GPS position precision |
| **GWD** | Ground wind direction (referenced from north) |
| **GWS** | Ground wind speed |
| **HDG** | Heading (direction boat is pointing) |
| **HUM** | Humidity level |
| **MAX** | Maximum of another data field |
| **MIN** | Minimum of another data field |
| **ODO** | Odometer (cumulative, not reset with trip data) |
| **OTH** | Opposite tack heading |
| **POS** | Current vessel position |
| **RACE** | Race timer |
| **REF** | Steer pilot reference |
| **REL** | Relative value (e.g., relative humidity) |
| **RUD** | Rudder angle |
| **SEA** | Sea water temperature |
| **SOG** | Speed over ground |
| **STR** | Steer pilot |
| **TRP** | Trip distance (resets on demand) |
| **TWA** | True wind angle (relative to water, port/starboard 0–180°) |
| **TWD** | True wind direction (relative to north) |
| **TWS** | True wind speed (relative to vessel) |
| **UTC** | Coordinated Universal Time |
| **VMG** | Velocity made good to waypoint (requires active navigation) |
| **WND** | Velocity made good upwind |
| **XTE** | Cross-track error |

---

## Key Sailing Data Fields (Quick Lookup)

### Wind

- **AWA / AWS** — apparent wind (what you feel on deck)
- **TWA / TWS / TWD** — true wind (corrected for boat motion)
- **GWD / GWS** — ground wind (corrected for current)
- **WND** — VMG upwind

### Speed & Course

- **BSP** — boat speed through water
- **SOG / COG** — speed and course over ground
- **VMG** — velocity made good toward waypoint

### Navigation

- **BTW** — bearing to waypoint
- **DTW** — distance to waypoint
- **CTS** — course to steer
- **XTE** — cross-track error
- **HDG** — compass heading

### Environment

- **DPT** — depth
- **SEA** — water temperature
- **AIR** — air temperature
- **BAR** — barometric pressure
- **HUM** — humidity
- **DRF** — current speed

---

## Support

Registration: [my.garmin.com](http://my.garmin.com)
Support: [garmin.com/support](http://www.garmin.com/support)
