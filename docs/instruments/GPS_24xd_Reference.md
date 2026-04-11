# Garmin GPS 24xd NMEA 2000 — Quick Reference

*Based on Installation Instructions, September 2023 (GUID-28CE8C25-CFD8-4C12-B6D0-AD9CDF4D5084 v6)*

---

## Overview

The GPS 24xd is a high-sensitivity GPS antenna with a built-in compass that provides position and magnetic heading data to an NMEA 2000 network. It requires an existing NMEA 2000 network (or you must install one). It comes packaged with an NMEA 2000 T-connector and a 6 m (20 ft.) drop cable.

---

## Specifications

| Parameter | Value |
|-----------|-------|
| **Dimensions** | 91.6 × 49.5 mm (3 19/32 × 1 15/16 in.) |
| **Weight** | 201 g (7.1 oz.) |
| **Drop cable length** | 6 m (19 ft. 8 in.) |
| **Temp range (white)** | −30° to 80°C (−22° to 176°F) |
| **Temp range (black)** | −30° to 65°C (−22° to 149°F) |
| **Case material** | Fully gasketed, high-impact plastic alloy |
| **Water rating** | IPX6 and IPX7 (submersible to 1 m for 30 min; jet-proof) |
| **Compass-safe distance** | 12.7 mm (0.5 in.) |
| **Input voltage** | 9–32 Vdc |
| **Max input current** | 200 mA @ 12 Vdc |
| **Typical input current** | 150 mA @ 12 Vdc |
| **NMEA 2000 LEN** | 3 (@ 9 Vdc) |
| **NMEA 2000 draw** | 150 mA |

---

## Tools Needed for Installation

- Drill with 3.2 mm (1/8 in.) drill bit
- 19 mm (3/4 in.) drill bit (pole-mount cable hole)
- 25 mm (1 in.) hole saw (surface-mount cable hole)
- Countersink bit (for fiberglass)
- Screws for under-deck mounting
- Appropriate screwdriver
- Marine sealant (optional)
- Additional NMEA 2000 network components as needed

---

## Mounting Options

### 1. Surface Mount

Uses the included surface-mount bracket. Steps:

1. Mark three pilot holes and trace cable hole using bracket as template.
2. Set bracket aside — do not drill through the bracket.
3. Drill 3.2 mm pilot holes.
4. Drill/cut 25 mm cable hole in the center.
5. Secure bracket with included M4 screws (use longer M4 screws if needed).
6. Route cable through center hole, connect to antenna.
7. Ensure large gasket is in place, seat antenna on bracket, twist clockwise to lock.
8. Secure with M3 set screw using 1.5 mm hex wrench.
9. Route cable away from EMI sources.

**Fiberglass tip:** Use a countersink bit to drill a clearance counterbore through the gel-coat layer only, to prevent cracking.

### 2. Pole Mount — Cable Outside

Uses the pole-mount adapter on a standard 1 in. OD, 14 TPI pipe-threaded pole (not included).

1. Route cable through pole-mount adapter; place cable in vertical slot.
2. Thread adapter onto pole — do not overtighten.
3. Connect cable to antenna.
4. Seat antenna on adapter, twist clockwise to lock.
5. Secure with M3 set screw (1.5 mm hex wrench).
6. Optionally fill remaining gap in vertical cable slot with marine sealant.
7. Attach pole to boat.
8. Route cable away from EMI sources.

### 3. Pole Mount — Cable Through Pole

1. Mark center of pole position; drill 19 mm hole for cable.
2. Fasten pole to boat.
3. Thread pole-mount adapter onto pole — do not overtighten.
4. Route cable through pole, connect to antenna.
5. Seat antenna on adapter, twist clockwise to lock.
6. Secure with M3 set screw (1.5 mm hex wrench).
7. Optionally fill vertical cable slot with marine sealant.
8. Route cable away from EMI sources.

### 4. Under-Deck Mount (White Model Only)

The antenna cannot acquire signals through metal — must be mounted under fiberglass only.

1. Place adhesive pads on under-deck mounting bracket.
2. Place antenna in bracket.
3. Adhere bracket to mounting surface.
4. Secure bracket with screws (verify screws don't penetrate through the surface).
5. Connect cable to antenna.
6. Route cable away from EMI sources.

---

## Mounting Location Guidelines

**Do:**
- Mount where the antenna has a clear, unobstructed 360° view of the sky.
- Mount above the path of any radar if present.
- Test the location with a handheld compass (boat, motors, and devices must be ON during test). If the compass needle moves at the planned location, magnetic interference is present — choose another spot.
- Use only stainless steel or brass mounting hardware (test with compass for magnetic fields).

**Don't:**
- Mount where superstructure, radome, or mast shades the antenna.
- Mount near engines or other EMI sources.
- Mount near ferrous metal objects (toolbox, compass, etc.).
- Mount directly in the path of a radar beam.
- Mount within 1 m (3 ft.) of a VHF antenna or radar path.

### Testing the Location

1. Temporarily secure antenna and test for correct operation.
2. If interference occurs, relocate and retest.
3. Repeat until full/acceptable signal strength is achieved.
4. Permanently mount.

---

## NMEA 2000 Network Connection

Connect the antenna to your backbone using the included T-connector and 6 m drop cable. A shorter drop cable or backbone extension can be used per NMEA 2000 guidelines.

```
GPS 24xd antenna
      │
 Drop cable (6 m)
      │
 T-connector
      │
 NMEA 2000 backbone
```

---

## Heading Calibration

After installation the compass must be calibrated and heading aligned to get magnetic heading data. Two methods are available depending on your setup.

### Method 1: Menu-Based Calibration (with Garmin Chartplotter)

Requires a compatible Garmin chartplotter on the same NMEA 2000 network.

1. `Menu → Settings → Communications → NMEA 2000 Setup → Device List`
2. Select GPS 24xd → `Review → Compass Cal. → Begin`
3. Follow on-screen instructions — keep the boat steady and level (no listing).
4. When complete, a calibration value appears near Compass Cal. setting. A value near **100 = ideal**; closer to **0 = poor magnetic environment** (consider relocating antenna).
5. Select `Auto Heading Alignment → Begin`
6. Follow on-screen instructions to complete heading alignment.

#### Fine Heading Alignment (Optional)

Must be done under open skies.

1. `Settings → Communications → NMEA 2000 Setup → Device List`
2. Select GPS 24xd → `Review → Fine Heading Alignment`
3. Using a landmark or known-good compass, determine boat heading.
4. Adjust until it matches → `Done`

### Method 2: Basic Calibration (No Chartplotter / Third-Party Device)

Requirements: ability to view heading data on network; remove all other heading sources; boat must reach at least 6.4 km/h (4 mph) for heading alignment.

1. Go to calm, open water.
2. Set display to show heading data from the antenna (not COG).
3. Disconnect antenna or power off NMEA 2000 network.
4. Wait for boat to be level and stationary.
5. Power on antenna; wait for heading data to appear.
6. **Within 3 minutes**, complete **two full, slow, tight circles** — keep boat steady and level.
7. When heading data disappears: compass is calibrating. Continue turning in the same direction for approximately **1½ more rotations** until heading data reappears. Compass is now calibrated.
8. Choose one:
   - **To align heading:** Continue turning for ~10 seconds until heading disappears again, then straighten and drive straight at cruising speed (≥ 6.4 km/h / 4 mph) until heading reappears. Calibration and alignment are complete.
   - **To skip alignment:** Stop turning, keep stationary for ~2 minutes until heading disappears and reappears. No heading offset is applied.
9. Test results; repeat if necessary.

---

## Disabling Magnetic Heading Data

If you can't mount the antenna in a suitable location for magnetic heading, you can disable it (the device will still output GPS Course Over Ground).

**Via chartplotter:** Perform a factory reset from the antenna configuration menu.

**Via basic method (no chartplotter):**

1. Go to calm, open water; set display to show heading.
2. Disconnect/power off NMEA 2000, then power on antenna.
3. Wait for heading data to appear.
4. Within 3 minutes, complete two full slow tight circles.
5. Heading disappears (calibration detected).
6. **Stop the boat completely.** Remain stationary for 2 minutes.
7. Heading reappears with a fixed value of **123°** — confirming heading will be disabled on next power cycle.
8. Power cycle the antenna; verify heading is disabled.

---

## Antenna Configuration

From a Garmin chartplotter: `NMEA 2000 Device List → GPS 24xd → Review`

| Option | Description |
|--------|-------------|
| **Auto Locate** | Clears existing satellite data and forces new acquisition (only available when no position fix) |
| **Factory Defaults** | Resets all settings to factory values; all custom configuration is lost |

---

## NMEA 2000 PGN Data

### Transmitted PGNs

| PGN | Description |
|-----|-------------|
| 059392 | ISO acknowledgment |
| 059904 | ISO request |
| 060928 | ISO address claim |
| 126208 | NMEA request group function |
| 126464 | Transmit PGNs group function |
| 126992 | System time |
| 126993 | Heartbeat |
| 126996 | Product information |
| 126998 | Configuration information |
| 127250 | **Vessel heading** |
| 127257 | **Attitude data** |
| 127258 | **Magnetic variation** |
| 129025 | **Position, rapid update** |
| 129026 | **COG and SOG, rapid update** |
| 129029 | **GNSS position data** |
| 129539 | GNSS DOPs |
| 129540 | GNSS satellites in view |

### Received PGNs

| PGN | Description |
|-----|-------------|
| 059392 | ISO acknowledgment |
| 059904 | ISO request |
| 060928 | ISO address claim |
| 126208 | NMEA request group function |
| 126993 | Heartbeat |
| 126996 | Product information |

---

## Maintenance

Clean the outer casing with a cloth dampened with mild detergent solution. Wipe dry. Avoid chemical cleaners and solvents that can damage plastic.

---

## Compliance

- EU Directive 2014/53/EU — full declaration at garmin.com/compliance
- FCC Part 15 Class B
- Innovation, Science and Economic Development Canada (licence-exempt RSS)

## Support

- Software updates: update chartplotter software when installing this device (see chartplotter manual at support.garmin.com)
- Warranty: garmin.com/support/warranty
