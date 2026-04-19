"""CAN bus NMEA 2000 source — reads PGN frames from SocketCAN via python-can.

Connects to the Waveshare 2-CH CAN HAT (MCP2515) on the Raspberry Pi.
Extracts PGN numbers from CAN extended arbitration IDs and handles
fast-packet reassembly for multi-frame NMEA 2000 messages.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import AsyncIterator, Dict, Optional, Set, Tuple

import can

from .source_base import NmeaSource

logger = logging.getLogger("aquarela.can")

# PGNs the pipeline expects
EXPECTED_PGNS: Set[int] = {
    126992,  # System Time
    127250,  # Vessel Heading
    127257,  # Attitude (heel / trim)
    127258,  # Magnetic Variation
    128259,  # Speed, Water Referenced
    128267,  # Water Depth
    128275,  # Distance Log
    129025,  # Position, Rapid Update
    129026,  # COG & SOG, Rapid Update
    129029,  # GNSS Position Data (fast-packet)
    129540,  # GNSS Sats in View (fast-packet)
    130306,  # Wind Data
    130310,  # Environmental Parameters
    130311,  # Environmental Parameters (temp/humidity instance)
}

# PGNs that use fast-packet protocol (>8 bytes payload).
# The 7 core sailing PGNs are all single-frame, but we include
# common multi-frame PGNs for future-proofing.
FAST_PACKET_PGNS: Set[int] = {
    128275,  # Distance Log (14 bytes)
    129029,  # GNSS Position Data (51 bytes)
    129540,  # GNSS Sats in View
    126996,  # Product Information
    126998,  # Configuration Information
}


# ── CAN ID → PGN extraction ───────────────────────────────────────────

def extract_pgn(can_id: int) -> Tuple[int, int]:
    """Extract (pgn, source_address) from a 29-bit CAN arbitration ID.

    NMEA 2000 encoding (29-bit extended CAN ID):
        Bits 28-26: Priority (3 bits)
        Bit  25:    Reserved
        Bit  24:    Data Page (DP)
        Bits 23-16: PF — PDU Format
        Bits 15-8:  PS — PDU Specific
        Bits 7-0:   Source Address

    PDU1 (PF < 240): PGN = DP<<16 | PF<<8  (PS is destination, not part of PGN)
    PDU2 (PF >= 240): PGN = DP<<16 | PF<<8 | PS
    """
    source_addr = can_id & 0xFF
    ps = (can_id >> 8) & 0xFF
    pf = (can_id >> 16) & 0xFF
    dp = (can_id >> 24) & 0x01

    if pf < 240:
        pgn = (dp << 16) | (pf << 8)
    else:
        pgn = (dp << 16) | (pf << 8) | ps

    return pgn, source_addr


# ── Fast-packet reassembly ─────────────────────────────────────────────

class FastPacketBuffer:
    """Reassembly buffer for a single fast-packet PGN stream."""

    def __init__(self) -> None:
        self.expected_size: int = 0
        self.data: bytearray = bytearray()
        self.sequence_id: int = -1
        self.frame_count: int = 0
        self.last_frame_time: float = 0.0

    def reset(self) -> None:
        self.expected_size = 0
        self.data = bytearray()
        self.sequence_id = -1
        self.frame_count = 0
        self.last_frame_time = 0.0


# ── CanSource ──────────────────────────────────────────────────────────

class CanSource(NmeaSource):
    """Read NMEA 2000 PGN frames from a SocketCAN interface.

    Parameters
    ----------
    interface : str
        SocketCAN interface name, e.g. ``"can0"`` (default).
    bustype : str
        python-can bus type (default ``"socketcan"``).
    ignore_addresses : set
        Source addresses to ignore (e.g. our own CAN writer).
    """

    def __init__(
        self,
        interface: str = "can0",
        bustype: str = "socketcan",
        ignore_addresses: Optional[Set[int]] = None,
    ) -> None:
        self._interface = interface
        self._bustype = bustype
        self._ignore_addresses: Set[int] = ignore_addresses or set()
        self._bus: Optional[can.Bus] = None
        self._running = False
        self._fast_packet_buffers: Dict[Tuple[int, int], FastPacketBuffer] = \
            defaultdict(FastPacketBuffer)

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        """Open the CAN bus interface, retrying on failure."""
        max_retries = 60  # try for up to ~5 minutes
        for attempt in range(max_retries):
            try:
                self._bus = await asyncio.to_thread(
                    can.Bus, channel=self._interface, interface=self._bustype,
                )
                self._running = True
                if attempt > 0:
                    logger.info("CAN source connected on attempt %d", attempt + 1)
                logger.info("CAN source started on %s (%s)",
                            self._interface, self._bustype)
                return
            except (can.CanError, OSError) as exc:
                if attempt == 0:
                    logger.warning("CAN interface %s not available: %s — retrying",
                                   self._interface, exc)
                await asyncio.sleep(5)
        # All retries exhausted
        logger.error("CAN interface %s not available after %d attempts — "
                     "running without CAN (dashboard will show no sensor data)",
                     self._interface, max_retries)
        self._running = False

    async def stop(self) -> None:
        """Shut down the CAN bus."""
        self._running = False
        if self._bus is not None:
            try:
                await asyncio.to_thread(self._bus.shutdown)
            except Exception:
                logger.exception("Error shutting down CAN bus")
            self._bus = None
        logger.info("CAN source stopped")

    # ── stream ─────────────────────────────────────────────────────

    async def stream(self) -> AsyncIterator[Tuple[int, bytes]]:
        """Yield ``(pgn, data_bytes)`` tuples from the CAN bus.

        Uses ``asyncio.to_thread`` to bridge the synchronous python-can
        ``recv()`` call into the async pipeline.  A short timeout keeps
        the event loop responsive and allows clean shutdown.
        """
        if self._bus is None:
            # CAN not available — yield nothing, keep server alive
            logger.warning("CAN bus not connected — waiting for reconnect")
            while self._running:
                await asyncio.sleep(5)
                try:
                    self._bus = await asyncio.to_thread(
                        can.Bus, channel=self._interface, interface=self._bustype,
                    )
                    logger.info("CAN bus reconnected on %s", self._interface)
                    break
                except (can.CanError, OSError):
                    continue
            if self._bus is None:
                return

        while self._running:
            # ── read one CAN frame (non-blocking via thread) ──
            try:
                msg: Optional[can.Message] = await asyncio.to_thread(
                    self._bus.recv, timeout=0.1,
                )
            except can.CanError as exc:
                logger.warning("CAN read error: %s", exc)
                await asyncio.sleep(0.1)
                continue

            if msg is None:
                continue  # timeout, loop to check _running

            if not msg.is_extended_id:
                continue  # NMEA 2000 always uses 29-bit extended IDs

            if msg.is_error_frame:
                logger.debug("CAN error frame received")
                continue

            pgn, source_addr = extract_pgn(msg.arbitration_id)

            # Skip frames from our own CAN writer (avoid double correction)
            if source_addr in self._ignore_addresses:
                continue

            # Only yield PGNs the pipeline understands
            if pgn not in EXPECTED_PGNS:
                continue

            # Fast-packet vs single-frame
            if pgn in FAST_PACKET_PGNS:
                reassembled = self._reassemble_fast_packet(
                    pgn, source_addr, msg.data,
                )
                if reassembled is not None:
                    yield (pgn, reassembled)
            else:
                yield (pgn, bytes(msg.data))

    # ── fast-packet reassembly ─────────────────────────────────────

    def _reassemble_fast_packet(
        self,
        pgn: int,
        source_addr: int,
        data: bytes,
    ) -> Optional[bytes]:
        """Reassemble fast-packet frames.

        Returns the complete payload when all frames have been received,
        or ``None`` if more frames are expected.
        """
        if len(data) < 2:
            return None

        key = (pgn, source_addr)
        seq_id = (data[0] >> 5) & 0x07
        frame_counter = data[0] & 0x1F

        buf = self._fast_packet_buffers[key]
        now = time.monotonic()

        if frame_counter == 0:
            # First frame of a new fast-packet message
            buf.reset()
            buf.sequence_id = seq_id
            buf.expected_size = data[1]
            buf.data = bytearray(data[2:8])  # up to 6 payload bytes
            buf.frame_count = 1
            buf.last_frame_time = now
            return None

        # Continuation frame
        if buf.sequence_id != seq_id:
            buf.reset()
            return None

        if now - buf.last_frame_time > 0.75:
            # Stale buffer (>750 ms since last frame) — discard
            buf.reset()
            return None

        buf.data.extend(data[1:8])  # up to 7 payload bytes
        buf.frame_count += 1
        buf.last_frame_time = now

        if len(buf.data) >= buf.expected_size:
            result = bytes(buf.data[: buf.expected_size])
            buf.reset()
            return result

        return None
