"""Decode NMEA 2000 PGN data bytes into typed Python dicts.

Each decoder function returns a dict whose keys match BoatState raw_* fields.
Unit conversions (radians→degrees, m/s→knots, Kelvin→Celsius) are applied here
so downstream code always works in human-friendly units.

PGN field layouts from: Aquarela Njord CSV Spec / canboat PGN database.
"""

import math
import struct
from typing import Any, Dict

# ── Constants ──────────────────────────────────────────────────────────
MS_TO_KT = 1.94384
RAD_TO_DEG = 180.0 / math.pi

# PGN numbers
PGN_VESSEL_HEADING = 127250
PGN_MAGNETIC_VARIATION = 127258
PGN_BATTERY_STATUS = 127508
PGN_SPEED_WATER = 128259
PGN_WATER_DEPTH = 128267
PGN_POSITION_RAPID = 129025
PGN_COG_SOG_RAPID = 129026
PGN_GNSS_POSITION = 129029
PGN_WIND_DATA = 130306
PGN_ATTITUDE = 127257
PGN_ENVIRONMENTAL = 130310
PGN_ENVIRONMENTAL_2 = 130311
PGN_SYSTEM_TIME = 126992
PGN_DISTANCE_LOG = 128275
PGN_GNSS_SATS = 129540

# Sentinel values indicating "not available" in NMEA 2000
_NA_U16 = 0xFFFF
_NA_I32 = 0x7FFFFFFF
_NA_U32 = 0xFFFFFFFF


def decode_pgn(pgn: int, data: bytes) -> Dict[str, Any]:
    """Decode a single PGN's data bytes into a dict of named fields.

    Returns empty dict for unknown PGNs.  Values are in display units:
    heading/angles in degrees, speeds in knots, depth in meters, temp in °C.
    """
    if pgn == PGN_VESSEL_HEADING:
        return _decode_heading(data)
    elif pgn == PGN_SPEED_WATER:
        return _decode_speed_water(data)
    elif pgn == PGN_WATER_DEPTH:
        return _decode_depth(data)
    elif pgn == PGN_POSITION_RAPID:
        return _decode_position(data)
    elif pgn == PGN_COG_SOG_RAPID:
        return _decode_cog_sog(data)
    elif pgn == PGN_WIND_DATA:
        return _decode_wind(data)
    elif pgn == PGN_ENVIRONMENTAL:
        return _decode_environmental(data)
    elif pgn == PGN_ENVIRONMENTAL_2:
        return _decode_environmental_2(data)
    elif pgn == PGN_ATTITUDE:
        return _decode_attitude(data)
    elif pgn == PGN_MAGNETIC_VARIATION:
        return _decode_mag_variation(data)
    elif pgn == PGN_SYSTEM_TIME:
        return _decode_system_time(data)
    elif pgn == PGN_DISTANCE_LOG:
        return _decode_distance_log(data)
    elif pgn == PGN_GNSS_POSITION:
        return _decode_gnss_position(data)
    elif pgn == PGN_GNSS_SATS:
        return _decode_gnss_sats(data)
    return {}


# ── Individual PGN decoders ────────────────────────────────────────────

def _decode_heading(data: bytes) -> Dict[str, Any]:
    """PGN 127250 — Vessel Heading.

    Byte layout: [SID(1)] [heading(2)] [deviation(2)] [variation(2)] [ref(1)]
    heading/deviation/variation: radians × 10000, unsigned 16-bit.
    """
    if len(data) < 4:
        return {}
    heading_raw = struct.unpack_from("<H", data, 1)[0]
    if heading_raw == _NA_U16:
        return {}
    heading_deg = (heading_raw * 0.0001) * RAD_TO_DEG
    return {"raw_heading_mag": heading_deg}


def _decode_speed_water(data: bytes) -> Dict[str, Any]:
    """PGN 128259 — Speed, Water Referenced.

    Byte layout: [SID(1)] [speed_wrt(2)] [speed_gnd(2)] [type(1)]
    speed: m/s × 100, unsigned 16-bit.
    """
    if len(data) < 3:
        return {}
    speed_raw = struct.unpack_from("<H", data, 1)[0]
    if speed_raw == _NA_U16:
        return {}
    return {"raw_bsp_kt": (speed_raw * 0.01) * MS_TO_KT}


def _decode_depth(data: bytes) -> Dict[str, Any]:
    """PGN 128267 — Water Depth.

    Byte layout: [SID(1)] [depth(4)] [offset(2)] [range(1)]
    depth: meters × 100, unsigned 32-bit.
    """
    if len(data) < 5:
        return {}
    depth_raw = struct.unpack_from("<I", data, 1)[0]
    if depth_raw == _NA_U32:
        return {}
    return {"raw_depth_m": depth_raw * 0.01}


def _decode_position(data: bytes) -> Dict[str, Any]:
    """PGN 129025 — Position, Rapid Update.

    Byte layout: [latitude(4)] [longitude(4)]
    Both: degrees × 1e7, signed 32-bit.
    """
    if len(data) < 8:
        return {}
    lat_raw = struct.unpack_from("<i", data, 0)[0]
    lon_raw = struct.unpack_from("<i", data, 4)[0]
    result: Dict[str, Any] = {}
    if lat_raw != _NA_I32:
        result["lat"] = lat_raw * 1e-7
    if lon_raw != _NA_I32:
        result["lon"] = lon_raw * 1e-7
    if result:
        result["gps_fix"] = True
    return result


def _decode_cog_sog(data: bytes) -> Dict[str, Any]:
    """PGN 129026 — COG & SOG, Rapid Update.

    Byte layout: [SID(1)] [ref(1)] [COG(2)] [SOG(2)] [reserved(2)]
    COG: radians × 10000, unsigned 16-bit.
    SOG: m/s × 100, unsigned 16-bit.
    """
    if len(data) < 6:
        return {}
    cog_raw = struct.unpack_from("<H", data, 2)[0]
    sog_raw = struct.unpack_from("<H", data, 4)[0]
    result: Dict[str, Any] = {}
    if cog_raw != _NA_U16:
        result["raw_cog_deg"] = (cog_raw * 0.0001) * RAD_TO_DEG
    if sog_raw != _NA_U16:
        result["raw_sog_kt"] = (sog_raw * 0.01) * MS_TO_KT
    return result


def _decode_wind(data: bytes) -> Dict[str, Any]:
    """PGN 130306 — Wind Data.

    Byte layout: [SID(1)] [speed(2)] [angle(2)] [reference(1)]
    speed: m/s × 100.  angle: radians × 10000.
    reference: 0=True ground, 1=Mag ground, 2=Apparent, 3=True boat, 4=True water.
    We only consume reference=2 (Apparent) since true wind is computed by our pipeline.
    """
    if len(data) < 6:
        return {}
    ws_raw = struct.unpack_from("<H", data, 1)[0]
    wa_raw = struct.unpack_from("<H", data, 3)[0]
    ref = data[5]

    # Accept ref=2 (apparent) or ref>=100 (some instruments send 0xFA
    # with valid apparent wind data in the speed/angle fields)
    if ref not in (2,) and ref < 100:
        return {}
    if ws_raw == _NA_U16 or wa_raw == _NA_U16:
        return {}

    ws_kt = (ws_raw * 0.01) * MS_TO_KT
    wa_deg = (wa_raw * 0.0001) * RAD_TO_DEG

    # Convert 0–360 to signed: >180 means port (negative)
    if wa_deg > 180:
        wa_deg -= 360

    return {"raw_awa_deg": wa_deg, "raw_aws_kt": ws_kt}


def _decode_attitude(data: bytes) -> Dict[str, Any]:
    """PGN 127257 — Attitude (yaw, pitch, roll).

    Byte layout: [SID(1)] [yaw(2)] [pitch(2)] [roll(2)] [reserved(1)]
    All angles: radians × 10000, signed 16-bit.
    Roll = heel (positive = starboard), Pitch = trim (positive = bow up).
    """
    if len(data) < 7:
        return {}
    result: Dict[str, Any] = {}
    pitch_raw = struct.unpack_from("<h", data, 3)[0]
    roll_raw = struct.unpack_from("<h", data, 5)[0]
    if pitch_raw != -32768:
        result["trim_deg"] = (pitch_raw * 0.0001) * RAD_TO_DEG
    if roll_raw != -32768:
        result["heel_deg"] = (roll_raw * 0.0001) * RAD_TO_DEG
    return result


def _decode_environmental(data: bytes) -> Dict[str, Any]:
    """PGN 130310 — Environmental Parameters.

    Byte layout: [SID(1)] [water_temp(2)] [outside_temp(2)] [pressure(2)]
    Temps: Kelvin × 100, unsigned 16-bit.
    """
    if len(data) < 3:
        return {}
    temp_raw = struct.unpack_from("<H", data, 1)[0]
    if temp_raw == _NA_U16:
        return {}
    return {"raw_water_temp_c": (temp_raw * 0.01) - 273.15}


def _decode_environmental_2(data: bytes) -> Dict[str, Any]:
    """PGN 130311 — Environmental Parameters (temperature/humidity instance).

    Byte layout: [SID(1)] [temp_src+hum_src(1)] [temp(2)] [humidity(2)] [pressure(2)]
    temp_src (bits 0-5): 0=Sea, 1=Outside, 2=Inside, ...
    temp: Kelvin × 100, unsigned 16-bit.
    """
    if len(data) < 4:
        return {}
    temp_src = data[1] & 0x3F
    temp_raw = struct.unpack_from("<H", data, 2)[0]
    if temp_raw == _NA_U16:
        return {}
    temp_c = (temp_raw * 0.01) - 273.15
    # temp_src=0 is sea water temperature
    if temp_src == 0:
        return {"raw_water_temp_c": temp_c}
    return {}


def _decode_mag_variation(data: bytes) -> Dict[str, Any]:
    """PGN 127258 — Magnetic Variation.

    Byte layout: [SID(1)] [source(1)] [age_days(2)] [variation(2)]
    variation: radians × 10000, signed 16-bit (east positive).
    """
    if len(data) < 6:
        return {}
    var_raw = struct.unpack_from("<h", data, 4)[0]
    if var_raw == -32768:  # 0x8000 = not available
        return {}
    return {"magnetic_variation": (var_raw * 0.0001) * RAD_TO_DEG}


def _decode_system_time(data: bytes) -> Dict[str, Any]:
    """PGN 126992 — System Time.

    Byte layout: [SID(1)] [source(1)] [days_since_epoch(2)] [seconds(4)]
    days: unsigned 16-bit (days since 1970-01-01).
    seconds: unsigned 32-bit, seconds × 10000 since midnight.
    """
    if len(data) < 8:
        return {}
    source = data[1]
    days = struct.unpack_from("<H", data, 2)[0]
    secs_raw = struct.unpack_from("<I", data, 4)[0]
    if days == _NA_U16 or secs_raw == _NA_U32:
        return {}
    secs = secs_raw * 0.0001
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    # Full UTC timestamp from GPS epoch (days since 1970-01-01)
    gps_epoch_secs = days * 86400 + int(secs)
    return {
        "gps_time": f"{h:02d}:{m:02d}:{s:02d}",
        "gps_epoch_secs": gps_epoch_secs,
    }


def _decode_distance_log(data: bytes) -> Dict[str, Any]:
    """PGN 128275 — Distance Log.

    Byte layout: [days(2)] [seconds(4)] [trip_log(4)] [total_log(4)]
    trip_log / total_log: meters, unsigned 32-bit.
    """
    if len(data) < 14:
        return {}
    result: Dict[str, Any] = {}
    trip_raw = struct.unpack_from("<I", data, 6)[0]
    total_raw = struct.unpack_from("<I", data, 10)[0]
    if trip_raw != _NA_U32:
        result["trip_log_nm"] = trip_raw / 1852.0
    if total_raw != _NA_U32:
        result["total_log_nm"] = total_raw / 1852.0
    return result


def _decode_gnss_position(data: bytes) -> Dict[str, Any]:
    """PGN 129029 — GNSS Position Data (fast-packet, 51 bytes).

    Provides higher-precision lat/lon than 129025, plus altitude and satellite count.
    Byte layout: [SID(1)] [days(2)] [seconds(4)] [lat(8)] [lon(8)] [alt(8)]
                 [type(4bits)] [method(4bits)] [integrity(2bits)] [reserved(6bits)]
                 [num_svs(1)] [hdop(2)] [pdop(2)] ...
    lat/lon: degrees × 1e16, signed 64-bit.
    """
    if len(data) < 35:
        return {}
    result: Dict[str, Any] = {}
    lat_raw = struct.unpack_from("<q", data, 7)[0]
    lon_raw = struct.unpack_from("<q", data, 15)[0]
    if lat_raw != 0x7FFFFFFFFFFFFFFF:
        result["lat"] = lat_raw * 1e-16
    if lon_raw != 0x7FFFFFFFFFFFFFFF:
        result["lon"] = lon_raw * 1e-16
    if result:
        result["gps_fix"] = True
    # Number of satellites referenced
    if len(data) >= 34:
        num_svs = data[33]
        if num_svs != 0xFF:
            result["gps_num_sats"] = num_svs
    return result


def _decode_gnss_sats(data: bytes) -> Dict[str, Any]:
    """PGN 129540 — GNSS Sats in View (fast-packet).

    Byte layout: [SID(1)] [mode(2bits)+reserved(6bits)] [num_sats(1)] ...
    We just extract the satellite count.
    """
    if len(data) < 3:
        return {}
    num_sats = data[2]
    if num_sats == 0xFF:
        return {}
    return {"gps_num_sats": num_sats}
