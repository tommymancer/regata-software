#!/usr/bin/env python3
"""Virtual CAN test — sends simulated NMEA 2000 frames on vcan0.

This lets you test the full CanSource → pipeline → WebSocket chain
on the Raspberry Pi without real instruments or a boat.

Setup (run once on the Pi):

    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set up vcan0

Then in one terminal, start this sender:

    source ~/aquarela/venv/bin/activate
    python scripts/vcan_test.py

In aquarela-config.json, set:

    "source": "vcan0"

Then restart Aquarela:

    sudo systemctl restart aquarela

Open http://10.42.0.1:8080 — you should see live data updating.
Press Ctrl+C to stop the sender.
"""

import math
import struct
import sys
import time

import can

# ── Constants ──────────────────────────────────────────────────────────
KT_TO_MS = 1.0 / 1.94384
DEG_TO_RAD = math.pi / 180.0
SOURCE_ADDR = 0x01  # simulated device address
HZ = 10


def pgn_to_can_id(pgn: int, priority: int = 2) -> int:
    """Build a 29-bit extended CAN ID from a PGN (PDU2 only)."""
    dp = (pgn >> 16) & 0x01
    pf = (pgn >> 8) & 0xFF
    ps = pgn & 0xFF
    return (priority << 26) | (dp << 24) | (pf << 16) | (ps << 8) | SOURCE_ADDR


def encode_and_send(bus: can.Bus, frames: list) -> None:
    """Send a list of (pgn, data_bytes) as CAN frames."""
    for pgn, data in frames:
        msg = can.Message(
            arbitration_id=pgn_to_can_id(pgn),
            data=data,
            is_extended_id=True,
        )
        bus.send(msg)


def make_frames(t: float) -> list:
    """Generate one step of NMEA 2000 frames for time t (seconds).

    Simulates a boat on starboard tack, upwind, with gentle oscillations.
    """
    # Simulated sailing state
    heading = 140.0 + 3.0 * math.sin(t * 0.05)   # magnetic heading ~140°
    bsp = 5.8 + 0.3 * math.sin(t * 0.1)           # boat speed ~5.8 kt
    awa = 32.0 + 2.0 * math.sin(t * 0.07)         # apparent wind angle ~32°
    aws = 12.5 + 0.5 * math.sin(t * 0.08)         # apparent wind speed ~12.5 kt
    depth = 15.0 + 1.0 * math.sin(t * 0.02)       # depth ~15 m
    water_temp = 18.5                               # lake temperature
    lat = 46.0020 + t * 0.000001                   # slow northward drift
    lon = 8.9627 + t * 0.000002                    # slow eastward drift
    sog = bsp * 0.95                                # SOG ≈ BSP
    cog = heading + 2.0                             # COG ≈ heading + leeway

    frames = []

    # PGN 127250: Vessel Heading
    hdg_raw = int((heading * DEG_TO_RAD) / 0.0001) & 0xFFFF
    frames.append((127250, bytes([0xFF]) + struct.pack("<H", hdg_raw) + bytes(5)))

    # PGN 128259: Speed, Water Referenced
    bsp_raw = int((bsp * KT_TO_MS) / 0.01) & 0xFFFF
    frames.append((128259, bytes([0xFF]) + struct.pack("<H", bsp_raw) + bytes(5)))

    # PGN 130306: Wind Data (apparent, reference=2)
    aws_raw = int((aws * KT_TO_MS) / 0.01) & 0xFFFF
    awa_norm = awa if awa >= 0 else awa + 360
    awa_raw = int((awa_norm * DEG_TO_RAD) / 0.0001) & 0xFFFF
    frames.append((130306, bytes([0xFF]) + struct.pack("<HH", aws_raw, awa_raw) + bytes([2, 0xFF, 0xFF])))

    # PGN 128267: Water Depth
    depth_raw = int(depth / 0.01) & 0xFFFFFFFF
    frames.append((128267, bytes([0xFF]) + struct.pack("<I", depth_raw) + bytes(3)))

    # PGN 129025: Position Rapid Update
    lat_raw = int(lat * 1e7)
    lon_raw = int(lon * 1e7)
    frames.append((129025, struct.pack("<ii", lat_raw, lon_raw)))

    # PGN 129026: COG/SOG Rapid Update
    cog_norm = cog % 360
    cog_raw = int((cog_norm * DEG_TO_RAD) / 0.0001) & 0xFFFF
    sog_raw = int((sog * KT_TO_MS) / 0.01) & 0xFFFF
    frames.append((129026, bytes([0xFF, 0xFF]) + struct.pack("<HH", cog_raw, sog_raw) + bytes(2)))

    # PGN 130310: Environmental Parameters
    temp_k = water_temp + 273.15
    temp_raw = int(temp_k / 0.01) & 0xFFFF
    frames.append((130310, bytes([0xFF]) + struct.pack("<H", temp_raw) + bytes(5)))

    return frames


def main():
    interface = sys.argv[1] if len(sys.argv) > 1 else "vcan0"
    print(f"Sending NMEA 2000 frames on {interface} at {HZ} Hz")
    print("Simulating: starboard tack, ~140° heading, ~5.8 kt BSP, ~12.5 kt AWS")
    print("Press Ctrl+C to stop.\n")

    bus = can.Bus(channel=interface, interface="socketcan")
    dt = 1.0 / HZ
    t = 0.0
    step = 0

    try:
        while True:
            frames = make_frames(t)
            encode_and_send(bus, frames)
            step += 1
            t += dt

            if step % (HZ * 5) == 0:
                print(f"  sent {step} steps ({t:.0f}s)")

            time.sleep(dt)
    except KeyboardInterrupt:
        print(f"\nStopped after {step} steps ({t:.1f}s)")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
