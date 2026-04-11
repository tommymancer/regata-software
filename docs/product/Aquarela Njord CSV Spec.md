---
title: "Aquarela Njord CSV Spec"
created: 2026-02-24
type: reference
status: active
domain: aquarela
tags:
  - type/reference
  - type/procedure
  - domain/sailing
  - domain/electronics
  - project/aquarela
  - njord-analytics
  - csv-format
  - nmea2000
  - pgn-decode
  - calibration
related:
  - "[[Aquarela Performance System]]"
summary: "Exact CSV column specification for the Raspberry Pi data logger to produce files accepted by Njord Analytics, including PGN mapping, unit conversions, sign conventions, calibration pipeline, and true wind calculation."
---

## Summary

This is the definitive CSV format the Pi must write so that Njord Analytics accepts the upload without conversion. Covers column headers (exact strings), NMEA 2000 PGN sources, unit conversions, sign conventions, and the calibration correction pipeline that runs before each value is written. Validated with a 4,692-row test dataset uploaded successfully to Njord in February 2026.

## CSV Header (exact string)

```
Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation
```

**Sample rate**: 2 Hz recommended
**Timestamp format**: ISO 8601 UTC — `2025-06-15T10:00:00.000Z`

## Column Mapping

| Column | Unit | N2K Source | PGN | Notes |
|---|---|---|---|---|
| **Timestamp** | ISO 8601 UTC | Pi system clock | — | Sync via GPS PPS or NTP |
| **Lat** | decimal degrees | GPS 24xd | 129029 | 7 decimal places (~1 cm) |
| **Lon** | decimal degrees | GPS 24xd | 129029 | 7 decimal places |
| **SOG** | knots | GPS 24xd | 129026 | Raw is m/s → ×1.94384 |
| **COG** | degrees true | GPS 24xd | 129026 | Raw is radians → convert to degrees, 0-360 |
| **Heading** | degrees magnetic | GPS 24xd | 127250 | Apply compass cal offset before writing |
| **BSP** | knots | Airmar 20-633-01 | 128259 | Apply speed cal factor before writing |
| **AWA** | degrees | gWind | 130306 | **Signed: negative = port, positive = starboard**. Apply AWA cal offset |
| **AWS** | knots | gWind | 130306 | Raw is m/s → convert |
| **TWA** | degrees | Pi calculated | — | **Signed: negative = port, positive = starboard** |
| **TWS** | knots | Pi calculated | — | Derived from BSP + AWA + AWS |
| **TWD** | degrees true | Pi calculated | — | Wind direction FROM, 0-360. Derived from TWA + Heading + MagVar |
| **Heel** | degrees | Atlas 2 IMU | — | **Signed: negative = port heel, positive = starboard heel** |
| **Trim** | degrees | Atlas 2 IMU | — | **Negative = bow down, positive = bow up** |
| **Depth** | meters | Airmar 20-633-01 | 128267 | Apply keel offset (−1.85 m) if depth-below-keel |
| **MagneticVariation** | degrees | GPS 24xd or config | 127258 | East positive. Lake Lugano ≈ +2.5° (2025) |

## Optional Columns (add when available)

| Column | Unit | Source | Notes |
|---|---|---|---|
| **Rudder** | degrees | Future sensor | Positive = starboard |
| **Leeway** | degrees | Pi estimated | Derive from heel via empirical model |
| **TimeToGun** | seconds | Atlas 2 start ping | Single row, countdown to race start |
| **Portlat/Portlon** | decimal degrees | Atlas 2 | Port end of start line |
| **Stbdlat/Stbdlon** | decimal degrees | Atlas 2 | Starboard end of start line |

## PGN Decode Reference

| PGN | Name | Key Fields | Raw Units | Conversion |
|---|---|---|---|---|
| 127250 | Vessel Heading | heading, reference | radians | × 180/π → degrees |
| 128259 | Speed, Water Referenced | speed_wrt | m/s | × 1.94384 → knots |
| 128267 | Water Depth | depth | meters | already meters |
| 129025 | Position, Rapid Update | lat, lon | deg × 10⁷ | ÷ 10⁷ → decimal degrees |
| 129026 | COG/SOG, Rapid Update | cog, sog | rad, m/s | cog: × 180/π; sog: × 1.94384 |
| 129029 | GNSS Position Data | lat, lon, alt | deg × 10⁷ | ÷ 10⁷ → decimal degrees |
| 130306 | Wind Data | wind_speed, wind_angle, reference | m/s, rad | speed: × 1.94384; angle: × 180/π |

## Calibration Pipeline (apply BEFORE writing CSV)

Apply these corrections to raw N2K values before writing each CSV row:

1. **Heading**: `corrected = raw_heading - compass_offset`
2. **BSP**: `corrected = raw_bsp × speed_factor`
3. **AWA**: `corrected = raw_awa - awa_offset`
4. **Depth**: `corrected = raw_depth - 1.85` (if depth-below-keel mode)
5. **True wind**: Calculate TWA, TWS, TWD from corrected BSP + corrected AWA + AWS

### Config File: `aquarela-config.json`

```json
{
  "calibration": {
    "compass": { "offset": 0.0 },
    "speed": { "factor": 1.0 },
    "wind": { 
      "awa_offset": 0.0,
      "tws_downwind_factor": 1.0
    },
    "depth": { "offset": -1.85 }
  },
  "magnetic_variation": 2.5,
  "sample_rate_hz": 2
}
```

## True Wind Calculation

```python
import math

def calc_true_wind(bsp_kt, awa_deg, aws_kt):
    """
    bsp_kt:  calibrated boat speed (knots)
    awa_deg: calibrated apparent wind angle (degrees, signed: - port, + stbd)
    aws_kt:  apparent wind speed (knots)
    Returns: (twa_deg, tws_kt) — both signed same convention as AWA
    """
    awa_rad = math.radians(awa_deg)
    aw_x = aws_kt * math.cos(awa_rad)  # along-boat
    aw_y = aws_kt * math.sin(awa_rad)  # cross-boat
    tw_x = aw_x - bsp_kt               # subtract boat speed
    tw_y = aw_y
    tws = math.sqrt(tw_x**2 + tw_y**2)
    twa = math.degrees(math.atan2(tw_y, tw_x))
    return twa, tws

def calc_twd(twa_deg, heading_mag, mag_var):
    """
    True Wind Direction (compass direction wind blows FROM), 0-360.
    heading_mag: magnetic heading (degrees)
    mag_var: magnetic variation (east positive)
    """
    heading_true = heading_mag - mag_var
    twd = (heading_true + twa_deg) % 360
    return twd
```

## Validation

Test dataset (`aquarela_test_session.csv`): 4,692 rows at 2 Hz simulating a 39-minute training session on Lake Lugano with upwind legs, tacks, reaches, downwind legs, gybes, and motor in/out segments. Successfully uploaded to Njord Analytics — all columns recognized, sign conventions accepted.

---

*Spec version 1.0 — February 2026*
*Sensor stack: GPS 24xd · gWind · Airmar 20-633-01 · Atlas 2 · Raspberry Pi*
