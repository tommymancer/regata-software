"""Tests for CAN writer — PGN encoding, NAME field, and CanWriter class."""

import struct
import sys
from math import pi, radians
from unittest.mock import MagicMock, patch

import pytest

# Ensure the lazy "import can" inside can_writer methods resolves to a mock.
mock_can_module = MagicMock()
sys.modules.setdefault("can", mock_can_module)

from aquarela.nmea.can_writer import (
    CanWriter,
    WIND_REF_TRUE_GROUND,
    WIND_REF_TRUE_WATER,
    build_name_field,
    encode_pgn_130306,
)


# ── PGN 130306 encoding ──────────────────────────────────────────────────

class TestEncodePGN130306:
    """Verify PGN 130306 (Wind Data) encoding."""

    def test_water_reference_45deg_12kt(self):
        """TWA=45 deg, TWS=12 kt, water-referenced → correct bytes, ref=4."""
        data = encode_pgn_130306(twa_deg=45.0, tws_kt=12.0,
                                  reference=WIND_REF_TRUE_WATER)
        assert len(data) == 8

        sid = data[0]
        assert sid == 0

        # Speed: 12 kt → m/s → raw 0.01 m/s units
        speed_raw = struct.unpack_from("<H", data, 1)[0]
        speed_ms = speed_raw / 100.0
        expected_ms = 12.0 / 1.94384
        assert abs(speed_ms - expected_ms) < 0.02  # within 0.02 m/s

        # Angle: 45° → radians → 0.0001 rad units
        angle_raw = struct.unpack_from("<H", data, 3)[0]
        angle_rad = angle_raw / 10000.0
        assert abs(angle_rad - radians(45.0)) < 0.001

        # Reference byte
        assert data[5] == WIND_REF_TRUE_WATER  # 4

        # Reserved bytes
        assert data[6] == 0xFF
        assert data[7] == 0xFF

    def test_ground_reference(self):
        """Ground-referenced wind → ref byte = 3."""
        data = encode_pgn_130306(twa_deg=90.0, tws_kt=8.0,
                                  reference=WIND_REF_TRUE_GROUND)
        assert data[5] == WIND_REF_TRUE_GROUND  # 3

    def test_negative_angle_normalised(self):
        """Negative TWA (e.g. -45°) normalised to 315°."""
        data = encode_pgn_130306(twa_deg=-45.0, tws_kt=10.0,
                                  reference=WIND_REF_TRUE_WATER)
        angle_raw = struct.unpack_from("<H", data, 3)[0]
        angle_rad = angle_raw / 10000.0
        assert abs(angle_rad - radians(315.0)) < 0.001


# ── NAME field ────────────────────────────────────────────────────────────

class TestBuildNameField:
    """Verify ISO 11783 NAME for address claim (PGN 60928)."""

    def test_length_is_8_bytes(self):
        name = build_name_field(unique_number=42)
        assert len(name) == 8

    def test_industry_group_marine(self):
        """Industry group (bits 60-62) must be 4 (Marine)."""
        name = build_name_field(unique_number=0)
        value = int.from_bytes(name, "little")
        industry_group = (value >> 60) & 0x07
        assert industry_group == 4

    def test_self_configurable_set(self):
        """Bit 63 must be 1 (self-configurable)."""
        name = build_name_field(unique_number=0)
        value = int.from_bytes(name, "little")
        self_config = (value >> 63) & 0x01
        assert self_config == 1

    def test_device_function_atmospheric(self):
        """Device function (bits 40-47) must be 130."""
        name = build_name_field(unique_number=0)
        value = int.from_bytes(name, "little")
        func = (value >> 40) & 0xFF
        assert func == 130

    def test_manufacturer_code(self):
        """Manufacturer code (bits 21-31) must be 2047."""
        name = build_name_field(unique_number=0)
        value = int.from_bytes(name, "little")
        mfr = (value >> 21) & 0x7FF
        assert mfr == 2047


# ── CanWriter class ───────────────────────────────────────────────────────

class TestCanWriterDisabled:
    """When enabled=False the writer must do nothing."""

    def test_disabled_does_not_send(self):
        writer = CanWriter(enabled=False, dry_run=False)
        writer._address_claimed = True

        mock_bus = MagicMock()
        writer._bus = mock_bus

        writer.update(twa_water=45.0, tws_water=12.0,
                      twa_ground=50.0, tws_ground=11.0)

        mock_bus.send.assert_not_called()


class TestCanWriterDryRun:
    """When dry_run=True the writer must log but not send."""

    def test_dry_run_does_not_send(self):
        writer = CanWriter(enabled=True, dry_run=True)
        writer._address_claimed = True

        mock_bus = MagicMock()
        writer._bus = mock_bus

        writer.update(twa_water=45.0, tws_water=12.0,
                      twa_ground=50.0, tws_ground=11.0)

        mock_bus.send.assert_not_called()


class TestCanWriterEnabled:
    """When enabled and not dry-run, the writer must send messages."""

    def test_sends_two_messages(self):
        writer = CanWriter(enabled=True, dry_run=False)
        writer._address_claimed = True

        mock_bus = MagicMock()
        writer._bus = mock_bus

        writer.update(twa_water=45.0, tws_water=12.0,
                      twa_ground=50.0, tws_ground=11.0)

        assert mock_bus.send.call_count == 2

    def test_sends_only_water_when_ground_missing(self):
        writer = CanWriter(enabled=True, dry_run=False)
        writer._address_claimed = True

        mock_bus = MagicMock()
        writer._bus = mock_bus

        writer.update(twa_water=45.0, tws_water=12.0)

        assert mock_bus.send.call_count == 1

    def test_no_send_when_address_not_claimed(self):
        writer = CanWriter(enabled=True, dry_run=False)
        writer._address_claimed = False

        mock_bus = MagicMock()
        writer._bus = mock_bus

        writer.update(twa_water=45.0, tws_water=12.0)

        mock_bus.send.assert_not_called()
