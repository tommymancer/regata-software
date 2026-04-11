"""Tests for PGN decoder — round-trip encode/decode accuracy."""

import math
import struct

import pytest

from aquarela.nmea.pgn_decoder import (
    decode_pgn,
    PGN_VESSEL_HEADING,
    PGN_SPEED_WATER,
    PGN_WATER_DEPTH,
    PGN_POSITION_RAPID,
    PGN_COG_SOG_RAPID,
    PGN_WIND_DATA,
    PGN_ENVIRONMENTAL,
    PGN_MAGNETIC_VARIATION,
)

DEG_TO_RAD = math.pi / 180.0
KT_TO_MS = 1.0 / 1.94384


class TestHeadingDecoder:
    def test_heading_round_trip(self):
        heading_deg = 222.0
        raw = int((heading_deg * DEG_TO_RAD) / 0.0001) & 0xFFFF
        data = bytes([0xFF]) + struct.pack("<H", raw) + bytes(5)
        result = decode_pgn(PGN_VESSEL_HEADING, data)
        assert "raw_heading_mag" in result
        assert abs(result["raw_heading_mag"] - heading_deg) < 0.1

    def test_heading_zero(self):
        raw = int(0)
        data = bytes([0xFF]) + struct.pack("<H", raw) + bytes(5)
        result = decode_pgn(PGN_VESSEL_HEADING, data)
        assert abs(result["raw_heading_mag"]) < 0.01

    def test_heading_na(self):
        data = bytes([0xFF]) + struct.pack("<H", 0xFFFF) + bytes(5)
        result = decode_pgn(PGN_VESSEL_HEADING, data)
        assert result == {}

    def test_heading_short_data(self):
        result = decode_pgn(PGN_VESSEL_HEADING, bytes(2))
        assert result == {}


class TestSpeedWaterDecoder:
    def test_bsp_round_trip(self):
        bsp_kt = 5.5
        raw = int((bsp_kt * KT_TO_MS) / 0.01) & 0xFFFF
        data = bytes([0xFF]) + struct.pack("<H", raw) + bytes(5)
        result = decode_pgn(PGN_SPEED_WATER, data)
        assert abs(result["raw_bsp_kt"] - bsp_kt) < 0.05

    def test_bsp_na(self):
        data = bytes([0xFF]) + struct.pack("<H", 0xFFFF) + bytes(5)
        result = decode_pgn(PGN_SPEED_WATER, data)
        assert result == {}


class TestDepthDecoder:
    def test_depth_round_trip(self):
        depth_m = 15.0
        raw = int(depth_m / 0.01) & 0xFFFFFFFF
        data = bytes([0xFF]) + struct.pack("<I", raw) + bytes(3)
        result = decode_pgn(PGN_WATER_DEPTH, data)
        assert abs(result["raw_depth_m"] - depth_m) < 0.05

    def test_depth_na(self):
        data = bytes([0xFF]) + struct.pack("<I", 0xFFFFFFFF) + bytes(3)
        result = decode_pgn(PGN_WATER_DEPTH, data)
        assert result == {}


class TestPositionDecoder:
    def test_position_lake_lugano(self):
        lat, lon = 46.002, 8.963
        lat_raw = int(lat * 1e7)
        lon_raw = int(lon * 1e7)
        data = struct.pack("<ii", lat_raw, lon_raw)
        result = decode_pgn(PGN_POSITION_RAPID, data)
        assert abs(result["lat"] - lat) < 1e-5
        assert abs(result["lon"] - lon) < 1e-5
        assert result["gps_fix"] is True


class TestCogSogDecoder:
    def test_cog_sog_round_trip(self):
        cog_deg = 180.0
        sog_kt = 6.0
        cog_raw = int((cog_deg * DEG_TO_RAD) / 0.0001) & 0xFFFF
        sog_raw = int((sog_kt * KT_TO_MS) / 0.01) & 0xFFFF
        data = bytes([0xFF, 0xFF]) + struct.pack("<HH", cog_raw, sog_raw) + bytes(2)
        result = decode_pgn(PGN_COG_SOG_RAPID, data)
        assert abs(result["raw_cog_deg"] - cog_deg) < 0.1
        assert abs(result["raw_sog_kt"] - sog_kt) < 0.05


class TestWindDecoder:
    def test_apparent_wind_starboard(self):
        aws_kt = 12.0
        awa_deg = 42.0  # starboard
        aws_raw = int((aws_kt * KT_TO_MS) / 0.01) & 0xFFFF
        awa_raw = int((awa_deg * DEG_TO_RAD) / 0.0001) & 0xFFFF
        data = bytes([0xFF]) + struct.pack("<HH", aws_raw, awa_raw) + bytes([2, 0xFF, 0xFF])
        result = decode_pgn(PGN_WIND_DATA, data)
        assert abs(result["raw_aws_kt"] - aws_kt) < 0.05
        assert abs(result["raw_awa_deg"] - awa_deg) < 0.1

    def test_apparent_wind_port(self):
        """Port wind: encoder uses 360-|awa|, decoder converts >180 to negative."""
        aws_kt = 10.0
        awa_deg = -42.0
        aws_raw = int((aws_kt * KT_TO_MS) / 0.01) & 0xFFFF
        awa_norm = awa_deg + 360  # 318 degrees
        awa_raw = int((awa_norm * DEG_TO_RAD) / 0.0001) & 0xFFFF
        data = bytes([0xFF]) + struct.pack("<HH", aws_raw, awa_raw) + bytes([2, 0xFF, 0xFF])
        result = decode_pgn(PGN_WIND_DATA, data)
        assert abs(result["raw_awa_deg"] - awa_deg) < 0.2

    def test_non_apparent_ignored(self):
        """Only reference=2 (apparent) should be decoded."""
        data = bytes([0xFF]) + struct.pack("<HH", 100, 100) + bytes([0, 0xFF, 0xFF])
        result = decode_pgn(PGN_WIND_DATA, data)
        assert result == {}


class TestEnvironmentalDecoder:
    def test_water_temp_round_trip(self):
        temp_c = 12.5
        temp_k = temp_c + 273.15
        temp_raw = int(temp_k / 0.01) & 0xFFFF
        data = bytes([0xFF]) + struct.pack("<H", temp_raw) + bytes(5)
        result = decode_pgn(PGN_ENVIRONMENTAL, data)
        assert abs(result["raw_water_temp_c"] - temp_c) < 0.05


class TestMagVariationDecoder:
    def test_mag_variation_east(self):
        var_deg = 2.5
        var_raw = int((var_deg * DEG_TO_RAD) / 0.0001)
        data = bytes([0xFF, 0xFF]) + struct.pack("<HH", 0, var_raw) + bytes(2)
        # Re-encode with proper layout: [SID(1)][source(1)][age_days(2)][variation(2)]
        data = bytes([0xFF, 0xFF, 0xFF, 0xFF]) + struct.pack("<h", var_raw)
        result = decode_pgn(PGN_MAGNETIC_VARIATION, data)
        assert abs(result["magnetic_variation"] - var_deg) < 0.1


class TestUnknownPGN:
    def test_unknown_pgn_returns_empty(self):
        result = decode_pgn(99999, bytes(8))
        assert result == {}
