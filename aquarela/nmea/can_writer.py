"""CAN bus NMEA 2000 writer — publishes calibrated data as NMEA 2000 PGNs.

Sends calibrated sensor values onto the NMEA 2000 CAN bus so that
downstream instruments (displays, autopilot) use corrected data:
  - PGN 130306: True wind (upwash-corrected)
  - PGN 127250: Vessel heading (compass offset applied)
  - PGN 128259: Boat speed (speed factor applied)
  - PGN 128267: Water depth (depth offset applied)

The ``import can`` is deferred to method bodies so the module can be
imported on development machines where python-can is not installed.
"""

import hashlib
import logging
import struct
import uuid
from math import pi, radians
from typing import Optional

logger = logging.getLogger("aquarela.can_writer")

# ── PGN 130306  Wind Data ────────────────────────────────────────────────

_KT_TO_MS = 1.0 / 1.94384

WIND_REF_TRUE_GROUND = 3
WIND_REF_TRUE_WATER = 4


def encode_pgn_130306(twa_deg: float, tws_kt: float, reference: int) -> bytes:
    """Encode PGN 130306 (Wind Data) as an 8-byte CAN frame.

    Parameters
    ----------
    twa_deg : float
        True wind angle in degrees (signed, -180..+180 or 0..360).
    tws_kt : float
        True wind speed in knots.
    reference : int
        3 = true ground, 4 = true water.
    """
    # Speed: convert kt → m/s, then to 0.01 m/s units
    speed_ms = tws_kt * _KT_TO_MS
    speed_raw = int(round(speed_ms * 100))

    # Angle: normalise to 0..360, then convert to 0.0001-radian units
    angle_deg = twa_deg % 360.0
    angle_rad = radians(angle_deg)
    angle_raw = int(round(angle_rad * 10000))

    sid = 0
    return struct.pack("<BHHBbb", sid, speed_raw, angle_raw, reference,
                       -1, -1)  # bytes 6-7 = 0xFF (reserved)


# ── PGN 127250  Vessel Heading ───────────────────────────────────────────

def encode_pgn_127250(heading_deg: float, magnetic: bool = True) -> bytes:
    """Encode PGN 127250 (Vessel Heading) as an 8-byte CAN frame.

    Byte layout:
      0:     SID
      1-2:   Heading (unsigned 16-bit, 0.0001 rad units)
      3-4:   Deviation (0xFFFF = not available)
      5-6:   Variation (0xFFFF = not available)
      7:     Reference (bits 0-1: 0=true, 1=magnetic)
    """
    angle_rad = radians(heading_deg % 360.0)
    angle_raw = int(round(angle_rad * 10000))
    ref = 1 if magnetic else 0
    return struct.pack("<BHHHb", 0, angle_raw, 0xFFFF, 0xFFFF, ref)


# ── PGN 128259  Speed, Water Referenced ─────────────────────────────────

def encode_pgn_128259(speed_kt: float) -> bytes:
    """Encode PGN 128259 (Speed, Water Referenced) as an 8-byte CAN frame.

    Byte layout:
      0:     SID
      1-2:   Speed water referenced (unsigned 16-bit, 0.01 m/s units)
      3-4:   Speed ground referenced (0xFFFF = not available)
      5:     Speed water ref type (0 = paddle wheel, 1 = pitot, etc.)
      6-7:   Reserved (0xFF)
    """
    speed_ms = speed_kt * _KT_TO_MS
    speed_raw = int(round(speed_ms * 100))
    return struct.pack("<BHHB", 0, speed_raw, 0xFFFF, 0) + b"\xff\xff"


# ── PGN 128267  Water Depth ─────────────────────────────────────────────

def encode_pgn_128267(depth_m: float) -> bytes:
    """Encode PGN 128267 (Water Depth) as an 8-byte CAN frame.

    Byte layout:
      0:     SID
      1-4:   Depth (unsigned 32-bit, 0.01 m units)
      5-6:   Offset (signed 16-bit, 0.001 m — set to 0)
      7:     Max range (0xFF = not available)
    """
    depth_raw = int(round(depth_m * 100))
    return struct.pack("<BIhb", 0, depth_raw, 0, -1)


# ── ISO 11783 NAME field (PGN 60928) ─────────────────────────────────────

def build_name_field(unique_number: Optional[int] = None) -> bytes:
    """Build the 64-bit ISO 11783 NAME for address claim (PGN 60928).

    Layout (bit 0 = LSB of first byte):
        Bits  0-20 : Unique Number          (21 bits)
        Bits 21-31 : Manufacturer Code      (11 bits) = 2047
        Bits 32-39 : Device Instance         (8 bits) = 0
        Bits 40-47 : Device Function         (8 bits) = 130  (Atmospheric)
        Bit  48    : Reserved                (1 bit)  = 0
        Bits 49-55 : Device Class            (7 bits) = 75   (External Env.)
        Bits 56-59 : System Instance         (4 bits) = 0
        Bits 60-62 : Industry Group          (3 bits) = 4    (Marine)
        Bit  63    : Self-configurable       (1 bit)  = 1

    Returns 8 bytes in little-endian order.
    """
    if unique_number is None:
        # Derive a stable 21-bit number from this machine's UUID.
        machine_hash = hashlib.md5(uuid.getnode().to_bytes(6, "big")).digest()
        unique_number = int.from_bytes(machine_hash[:3], "little") & 0x1FFFFF

    manufacturer_code = 2047
    device_instance = 0
    device_function = 130
    device_class = 75
    system_instance = 0
    industry_group = 4
    self_configurable = 1

    name = 0
    name |= (unique_number & 0x1FFFFF)
    name |= (manufacturer_code & 0x7FF) << 21
    name |= (device_instance & 0xFF) << 32
    name |= (device_function & 0xFF) << 40
    name |= (0 & 0x1) << 48                  # reserved
    name |= (device_class & 0x7F) << 49
    name |= (system_instance & 0xF) << 56
    name |= (industry_group & 0x7) << 60
    name |= (self_configurable & 0x1) << 63

    return name.to_bytes(8, "little")


# ── CanWriter ─────────────────────────────────────────────────────────────

class CanWriter:
    """Publish corrected wind onto the NMEA 2000 CAN bus.

    Parameters
    ----------
    enabled : bool
        Master enable switch.  When *False* nothing happens at all.
    dry_run : bool
        When *True* the CAN frames are logged but **not** sent.
    interface : str
        SocketCAN interface name (e.g. ``"can0"``).
    address : int
        Preferred NMEA 2000 source address (100-127).
    """

    def __init__(
        self,
        enabled: bool = False,
        dry_run: bool = True,
        interface: str = "can0",
        address: int = 100,
    ) -> None:
        self._enabled = enabled
        self._dry_run = dry_run
        self._interface = interface
        self._address = address
        self._bus = None  # type: ignore[assignment]
        self._address_claimed = False

    # ── lifecycle ──────────────────────────────────────────────────

    def start(self) -> None:
        """Open the CAN bus and perform address claim."""
        if not self._enabled:
            logger.info("CAN writer disabled — skipping start")
            return
        import can  # lazy import

        if not self._dry_run:
            self._bus = can.Bus(channel=self._interface, interface="socketcan")
            # Filter to only receive ISO Request (PGN 59904, PF=0xEA)
            self._bus.set_filters([{
                "can_id": 0x00EA0000,
                "can_mask": 0x00FF0000,
                "extended": True,
            }])
            logger.info("CAN writer opened %s", self._interface)
        else:
            logger.info("CAN writer dry-run mode — bus not opened")

        self._claim_address()

    def stop(self) -> None:
        """Shut down the CAN bus."""
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                logger.exception("Error shutting down CAN writer bus")
            self._bus = None
        self._address_claimed = False
        logger.info("CAN writer stopped")

    # ── address claim ─────────────────────────────────────────────

    def _claim_address(self) -> None:
        """Send PGN 60928 address claim, trying addresses 100-127."""
        import can  # lazy import

        name_data = build_name_field()
        # PGN 60928 = 0x00EE00 — PDU1 with destination 0xFF (global)
        # CAN ID: priority(6)=6 | PGN area | source address
        # For address claim: priority 6, PGN 60928
        # PF=0xEE (238), PS=0xFF (global broadcast)
        for attempt_addr in range(self._address, 128):
            can_id = (6 << 26) | (0x0EE << 16) | (0xFF << 8) | attempt_addr

            if not self._dry_run and self._bus is not None:
                msg = can.Message(
                    arbitration_id=can_id,
                    data=name_data,
                    is_extended_id=True,
                )
                try:
                    self._bus.send(msg)
                except Exception:
                    logger.warning("Address claim failed on %d", attempt_addr)
                    continue

            self._address = attempt_addr
            self._address_claimed = True
            logger.info("CAN address claimed: %d", attempt_addr)
            return

        # All 28 addresses exhausted
        logger.error("CAN address claim failed — all addresses 100-127 busy")
        self._enabled = False

    # ── ISO request handling ────────────────────────────────────

    def _check_iso_requests(self) -> None:
        """Check for ISO Request (PGN 59904) and respond with address claim."""
        if self._bus is None or self._dry_run:
            return
        import can
        while True:
            msg = self._bus.recv(timeout=0)
            if msg is None:
                break
            # PGN 59904 (ISO Request) = PF 0xEA, destination in PS
            pgn_area = (msg.arbitration_id >> 8) & 0x1FFFF
            pf = (pgn_area >> 8) & 0xFF
            ps = pgn_area & 0xFF
            if pf != 0xEA:
                continue
            # Check if request is for us (broadcast 0xFF or our address)
            if ps != 0xFF and ps != self._address:
                continue
            if len(msg.data) < 3:
                continue
            # Requested PGN (little-endian 3 bytes)
            requested_pgn = msg.data[0] | (msg.data[1] << 8) | (msg.data[2] << 16)
            if requested_pgn == 60928:
                self._send_address_claim()
            elif requested_pgn == 126996:
                self._send_product_info()

    def _send_address_claim(self) -> None:
        """Send PGN 60928 address claim."""
        import can
        name_data = build_name_field()
        can_id = (6 << 26) | (0xEE << 16) | (0xFF << 8) | self._address
        msg = can.Message(arbitration_id=can_id, data=name_data, is_extended_id=True)
        try:
            self._bus.send(msg)
            logger.debug("Sent address claim")
        except Exception:
            logger.exception("Failed to send address claim")

    def _send_product_info(self) -> None:
        """Send PGN 126996 (Product Information) as fast-packet.

        Fields (134 bytes total):
          - NMEA 2000 version (2 bytes)
          - Product code (2 bytes)
          - Model ID (32 bytes, padded)
          - Software version (32 bytes, padded)
          - Model version (32 bytes, padded)
          - Model serial (32 bytes, padded)
          - Certification level (1 byte)
          - Load equivalency (1 byte)
        """
        import can

        model_id = b"Aquarela Calibrated" + b"\xff" * 13  # 32 bytes
        sw_version = b"3.0" + b"\xff" * 29               # 32 bytes
        model_version = b"1.0" + b"\xff" * 29            # 32 bytes
        serial = b"AQ-100" + b"\xff" * 26                # 32 bytes

        payload = struct.pack("<HH", 2100, 9999)         # NMEA version, product code
        payload += model_id + sw_version + model_version + serial
        payload += struct.pack("<BB", 1, 1)              # cert level, load equiv

        # Fast-packet: PGN 126996 = 0x1F014
        can_id = (6 << 26) | (0x1F014 << 8) | self._address
        seq_id = 0  # sequence counter

        # First frame: [seq_counter | frame_counter=0], [total_bytes], [data 0-5]
        frames = []
        first = bytes([(seq_id << 5) | 0, len(payload)]) + payload[:6]
        frames.append(first.ljust(8, b"\xff"))
        offset = 6
        frame_num = 1
        while offset < len(payload):
            chunk = payload[offset:offset + 7]
            frame = bytes([(seq_id << 5) | frame_num]) + chunk
            frames.append(frame.ljust(8, b"\xff"))
            offset += 7
            frame_num += 1

        for frame_data in frames:
            msg = can.Message(
                arbitration_id=can_id,
                data=frame_data,
                is_extended_id=True,
            )
            try:
                self._bus.send(msg)
            except Exception:
                logger.exception("Failed to send product info frame")
        logger.debug("Sent product info (%d frames)", len(frames))

    # ── publish ───────────────────────────────────────────────────

    def update(
        self,
        twa_water: Optional[float] = None,
        tws_water: Optional[float] = None,
        twa_ground: Optional[float] = None,
        tws_ground: Optional[float] = None,
        heading_mag: Optional[float] = None,
        bsp_kt: Optional[float] = None,
        depth_m: Optional[float] = None,
    ) -> None:
        """Publish calibrated PGNs onto the NMEA 2000 bus."""
        if not self._enabled:
            return
        if not self._address_claimed:
            return

        self._check_iso_requests()

        # Collect (can_id, data) pairs to send
        frames: list[tuple[int, bytes]] = []
        sa = self._address

        # PGN 130306 — Wind Data
        if twa_water is not None and tws_water is not None:
            can_id = (2 << 26) | (0x1FD02 << 8) | sa
            frames.append((can_id, encode_pgn_130306(twa_water, tws_water, WIND_REF_TRUE_WATER)))

        if twa_ground is not None and tws_ground is not None:
            can_id = (2 << 26) | (0x1FD02 << 8) | sa
            frames.append((can_id, encode_pgn_130306(twa_ground, tws_ground, WIND_REF_TRUE_GROUND)))

        # PGN 127250 — Vessel Heading
        if heading_mag is not None:
            can_id = (2 << 26) | (0x1F112 << 8) | sa
            frames.append((can_id, encode_pgn_127250(heading_mag, magnetic=True)))

        # PGN 128259 — Speed, Water Referenced
        if bsp_kt is not None:
            can_id = (2 << 26) | (0x1F503 << 8) | sa
            frames.append((can_id, encode_pgn_128259(bsp_kt)))

        # PGN 128267 — Water Depth
        if depth_m is not None:
            can_id = (2 << 26) | (0x1F50B << 8) | sa
            frames.append((can_id, encode_pgn_128267(depth_m)))

        if self._dry_run:
            for can_id, data in frames:
                logger.info("CAN dry-run 0x%08X: %s", can_id, data.hex())
            return

        import can  # lazy import

        for frame_can_id, data in frames:
            msg = can.Message(
                arbitration_id=frame_can_id,
                data=data,
                is_extended_id=True,
            )
            try:
                self._bus.send(msg)
            except Exception:
                logger.exception("Failed to send CAN frame 0x%08X", frame_can_id)
