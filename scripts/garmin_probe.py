#!/usr/bin/env python3
"""Garmin GNX Wind PGN 126720 reverse-engineering probe.

Sends Garmin proprietary PGN 126720 fast-packet messages on the CAN bus
with different proprietary command IDs and payload layouts to discover
which format drives the target TWA/TAWA markers on the GNX Wind display.

Usage:
    python3 scripts/garmin_probe.py [--interface can0] [--source-addr 100]

The script is interactive — it sends a probe, then asks you to check
the GNX Wind screen before continuing.

Known facts:
  - PGN 126720 = manufacturer proprietary fast-packet
  - Garmin manufacturer code = 229 → first 2 bytes = 0xE5 0x80
  - Known display PGN uses proprietary ID: DE 05 05 05
  - Sailing target PGN uses an UNKNOWN proprietary ID
  - Angles likely encoded as 0.0001 rad units (standard NMEA 2000)
  - Speeds likely encoded as 0.01 m/s units (standard NMEA 2000)
"""

import argparse
import struct
import time
from math import radians
from typing import List, Optional

try:
    import can
except ImportError:
    print("ERROR: python-can not installed. Run: pip install python-can")
    raise SystemExit(1)

# ── Constants ──────────────────────────────────────────────────────────

GARMIN_MFG_HEADER = bytes([0xE5, 0x80])  # manufacturer 229 + marine industry 4
KT_TO_MS = 1.0 / 1.94384
PGN_126720 = 0x1EF00


def encode_angle(degrees: float) -> bytes:
    """Encode angle as unsigned 16-bit, 0.0001 radian units."""
    angle_deg = degrees % 360.0
    raw = int(round(radians(angle_deg) * 10000))
    return struct.pack("<H", raw)


def encode_angle_signed(degrees: float) -> bytes:
    """Encode angle as signed 16-bit, 0.0001 radian units."""
    raw = int(round(radians(degrees) * 10000))
    return struct.pack("<h", raw)


def encode_speed_kt(knots: float) -> bytes:
    """Encode speed as unsigned 16-bit, 0.01 m/s units."""
    raw = int(round(knots * KT_TO_MS * 100))
    return struct.pack("<H", raw)


def build_can_id(source_addr: int, dest: int = 0xFF, priority: int = 6) -> int:
    """Build 29-bit CAN ID for PGN 126720 (PDU1, addressed)."""
    dp = 1  # data page
    pf = 0xEF  # PDU format
    return (priority << 26) | (dp << 24) | (pf << 16) | (dest << 8) | source_addr


def send_fast_packet(bus: can.Bus, can_id: int, payload: bytes, seq: int = 0):
    """Send a payload as NMEA 2000 fast-packet frames."""
    frames = []

    # Frame 0: [seq<<5 | 0], [total_length], [up to 6 data bytes]
    first = bytes([(seq << 5) | 0, len(payload)]) + payload[:6]
    frames.append(first.ljust(8, b"\xff"))

    offset = 6
    frame_num = 1
    while offset < len(payload):
        chunk = payload[offset:offset + 7]
        frame = bytes([(seq << 5) | frame_num]) + chunk
        frames.append(frame.ljust(8, b"\xff"))
        offset += 7
        frame_num += 1

    for frame_data in frames:
        msg = can.Message(
            arbitration_id=can_id,
            data=frame_data,
            is_extended_id=True,
        )
        bus.send(msg)
        time.sleep(0.002)  # small gap between frames


# ── Probe definitions ─────────────────────────────────────────────────

# Test values: TWA=40°, TWS=12kt, BSP=6.5kt (typical upwind)
TEST_TWA_DEG = 40.0
TEST_TWS_KT = 12.0
TEST_BSP_KT = 6.5
TEST_AWA_DEG = 28.0  # approximate apparent for 40° true at 6.5kt/12kt

TWA_ENC = encode_angle(TEST_TWA_DEG)
TWS_ENC = encode_speed_kt(TEST_TWS_KT)
BSP_ENC = encode_speed_kt(TEST_BSP_KT)
AWA_ENC = encode_angle(TEST_AWA_DEG)
TWA_SIGNED = encode_angle_signed(TEST_TWA_DEG)
AWA_SIGNED = encode_angle_signed(TEST_AWA_DEG)

# Percentage values (target boat speed %)
TBS_PCT = struct.pack("<H", 9500)  # 95.00%
PBS_PCT = struct.pack("<H", 10000)  # 100.00%
TBS_PCT_BYTE = bytes([95])  # simpler 0-100 encoding


def build_probes() -> List[dict]:
    """Build the list of probe payloads to try."""
    probes = []

    # ── Phase 1: Try likely 2-byte proprietary IDs ──────────────
    # Garmin display uses DE 05. Sailing might use nearby values.

    # Hypothesis: sailing data uses a different function code
    for func_id in [0x01, 0x02, 0x03, 0x04, 0x10, 0x20, 0x30, 0x40,
                    0x50, 0x60, 0x70, 0x80, 0xA0, 0xC0, 0xD0, 0xDF,
                    0xE0, 0xE5, 0xF0, 0xFF]:
        # Layout A: [mfg] [func] [SID] [TWA u16] [TWS u16] [BSP u16]
        payload = GARMIN_MFG_HEADER + bytes([func_id, 0x00]) + TWA_ENC + TWS_ENC + BSP_ENC
        probes.append({
            "name": f"2-byte ID: {func_id:02X} 00 — layout A (TWA+TWS+BSP)",
            "payload": payload,
        })

    # ── Phase 2: Try 4-byte proprietary IDs (like display PGN) ──
    # The display PGN is DE 05 05 05. Try variations.

    four_byte_ids = [
        (0xDE, 0x05, 0x05, 0x01),  # variation of display ID
        (0xDE, 0x05, 0x05, 0x02),
        (0xDE, 0x05, 0x05, 0x03),
        (0xDE, 0x05, 0x05, 0x04),
        (0xDE, 0x05, 0x05, 0x06),
        (0xDE, 0x05, 0x05, 0x07),
        (0xDE, 0x05, 0x05, 0x08),
        (0xDE, 0x05, 0x05, 0x0A),
        (0xDE, 0x05, 0x05, 0x10),
        (0xDE, 0x05, 0x05, 0x20),
        (0xDE, 0x01, 0x01, 0x01),
        (0xDE, 0x02, 0x02, 0x02),
        (0xDE, 0x0A, 0x0A, 0x0A),
        (0x01, 0x00, 0x00, 0x00),
        (0x02, 0x00, 0x00, 0x00),
        (0x10, 0x00, 0x00, 0x00),
        (0x50, 0x00, 0x00, 0x00),  # 'P' for polar?
        (0x50, 0x4F, 0x4C, 0x41),  # "POLA" ascii
        (0x54, 0x57, 0x41, 0x00),  # "TWA\0" ascii
    ]

    for a, b, c, d in four_byte_ids:
        payload = GARMIN_MFG_HEADER + bytes([a, b, c, d]) + TWA_ENC + TWS_ENC + BSP_ENC
        probes.append({
            "name": f"4-byte ID: {a:02X} {b:02X} {c:02X} {d:02X} — TWA+TWS+BSP",
            "payload": payload,
        })

    # ── Phase 3: Different data layouts with common IDs ─────────
    # Maybe the ID is simple but the layout is different

    for func_id in [0x01, 0x10, 0x50, 0xDE]:
        # Layout B: [mfg] [func] [SID] [TTWA] [TAWA] [TargetBSP] [PolarBSP] [TBS%] [PBS%]
        payload = (GARMIN_MFG_HEADER + bytes([func_id, 0x00]) +
                   TWA_ENC + AWA_ENC + BSP_ENC + BSP_ENC + TBS_PCT + PBS_PCT)
        probes.append({
            "name": f"ID {func_id:02X} — layout B (TTWA+TAWA+BSP+Polar+TBS%+PBS%)",
            "payload": payload,
        })

        # Layout C: signed angles
        payload = (GARMIN_MFG_HEADER + bytes([func_id, 0x00]) +
                   TWA_SIGNED + AWA_SIGNED + BSP_ENC + TBS_PCT)
        probes.append({
            "name": f"ID {func_id:02X} — layout C (signed TWA+AWA+BSP+TBS%)",
            "payload": payload,
        })

        # Layout D: instance/type byte + minimal data
        for inst in [0x00, 0x01, 0x02, 0x03, 0xFF]:
            payload = (GARMIN_MFG_HEADER + bytes([func_id, inst]) +
                       TWA_ENC + BSP_ENC)
            probes.append({
                "name": f"ID {func_id:02X} inst={inst:02X} — layout D (TWA+BSP only)",
                "payload": payload,
            })

    # ── Phase 4: Single-frame PGN 61184 (proprietary single) ───
    # Maybe Garmin uses the single-frame version instead
    # These are marked separately and sent as PGN 61184 = 0xEF00

    for func_id in [0x01, 0x10, 0x50, 0xDE]:
        payload = GARMIN_MFG_HEADER + bytes([func_id]) + TWA_ENC + BSP_ENC
        probes.append({
            "name": f"PGN 61184 single-frame: ID {func_id:02X} — TWA+BSP",
            "payload": payload,
            "pgn": 61184,
        })

    return probes


def build_can_id_61184(source_addr: int, dest: int = 0xFF, priority: int = 6) -> int:
    """Build 29-bit CAN ID for PGN 61184 (PDU1, single-frame)."""
    # PGN 61184 = 0xEF00 → DP=0, PF=0xEF
    return (priority << 26) | (0xEF << 16) | (dest << 8) | source_addr


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Garmin GNX Wind PGN probe")
    parser.add_argument("--interface", "-i", default="can0", help="CAN interface")
    parser.add_argument("--source-addr", "-s", type=int, default=100, help="Source address")
    parser.add_argument("--start", type=int, default=0, help="Start from probe N")
    parser.add_argument("--repeat", type=int, default=5, help="Times to repeat each probe")
    parser.add_argument("--auto", action="store_true",
                        help="Auto mode: send all probes with 3s gap, no pause")
    args = parser.parse_args()

    bus = can.Bus(channel=args.interface, interface="socketcan")
    can_id_126720 = build_can_id(args.source_addr)
    can_id_61184 = build_can_id_61184(args.source_addr)

    probes = build_probes()
    total = len(probes)

    print(f"Garmin GNX Wind PGN 126720 Probe")
    print(f"================================")
    print(f"Interface: {args.interface}, Source addr: {args.source_addr}")
    print(f"Test values: TWA={TEST_TWA_DEG}°, TWS={TEST_TWS_KT}kt, BSP={TEST_BSP_KT}kt")
    print(f"Total probes: {total}")
    print(f"Repeat each: {args.repeat}x (at ~2Hz)")
    print()

    if not args.auto:
        print("For each probe, watch the GNX Wind screen.")
        print("Press ENTER to send next probe.")
        print("Type 'hit' if something appeared on screen.")
        print("Type 'skip N' to jump to probe N.")
        print("Type 'quit' to exit.")
        print()

    seq_counter = 0
    hits = []

    for idx, probe in enumerate(probes):
        if idx < args.start:
            continue

        pgn = probe.get("pgn", 126720)
        name = probe["name"]
        payload = probe["payload"]

        print(f"[{idx+1}/{total}] {name}")
        print(f"  PGN: {pgn} | Payload ({len(payload)} bytes): {payload.hex(' ')}")

        # Send the probe multiple times
        for rep in range(args.repeat):
            if pgn == 61184:
                # Single-frame: send directly (max 8 bytes)
                msg = can.Message(
                    arbitration_id=can_id_61184,
                    data=payload[:8],
                    is_extended_id=True,
                )
                bus.send(msg)
            else:
                send_fast_packet(bus, can_id_126720, payload, seq=seq_counter % 8)
                seq_counter += 1
            time.sleep(0.5)  # ~2Hz

        if args.auto:
            time.sleep(2)
            continue

        response = input("  > ").strip().lower()
        if response == "quit":
            break
        elif response == "hit":
            hits.append((idx, name, payload.hex(' ')))
            print(f"  *** HIT RECORDED! ***")
            # Keep sending this one so you can observe
            print("  Sending continuously — press ENTER to stop...")
            try:
                while True:
                    if pgn == 61184:
                        msg = can.Message(
                            arbitration_id=can_id_61184,
                            data=payload[:8],
                            is_extended_id=True,
                        )
                        bus.send(msg)
                    else:
                        send_fast_packet(bus, can_id_126720, payload, seq=seq_counter % 8)
                        seq_counter += 1
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
            input("  Press ENTER to continue to next probe...")
        elif response.startswith("skip"):
            try:
                args.start = int(response.split()[1]) - 1
            except (IndexError, ValueError):
                print("  Usage: skip N")

    bus.shutdown()

    print()
    print("=" * 60)
    if hits:
        print(f"HITS FOUND: {len(hits)}")
        for idx, name, hex_data in hits:
            print(f"  [{idx+1}] {name}")
            print(f"       {hex_data}")
    else:
        print("No hits found in this session.")
    print()
    print("Next steps:")
    print("  - If no hits: try --auto mode while watching the display")
    print("  - If hits: note the probe number and refine the payload")


if __name__ == "__main__":
    main()
