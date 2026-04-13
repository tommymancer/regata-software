#!/usr/bin/env python3
"""Smoke test: read CAN frames and report which NMEA 2000 PGNs are on the bus.

Run on the Raspberry Pi with the CAN HAT connected to the NMEA 2000 backbone:

    source ~/aquarela/venv/bin/activate
    python scripts/test_can.py

Press Ctrl+C to stop early.
"""

import sys
import time

import can

# Inline PGN extraction so this script has no internal dependencies
def extract_pgn(can_id: int):
    source_addr = can_id & 0xFF
    ps = (can_id >> 8) & 0xFF
    pf = (can_id >> 16) & 0xFF
    dp = (can_id >> 24) & 0x01
    if pf < 240:
        pgn = (dp << 16) | (pf << 8)
    else:
        pgn = (dp << 16) | (pf << 8) | ps
    return pgn, source_addr


EXPECTED_PGNS = {
    127250: "Vessel Heading",
    127257: "Attitude",
    128259: "Speed Water Ref",
    128267: "Water Depth",
    129025: "Position Rapid",
    129026: "COG & SOG Rapid",
    130306: "Wind Data",
    130310: "Environmental",
}

INTERFACE = sys.argv[1] if len(sys.argv) > 1 else "can0"
MAX_FRAMES = 500

print(f"Listening on {INTERFACE} for {MAX_FRAMES} frames …")
print("Press Ctrl+C to stop early.\n")

bus = can.Bus(channel=INTERFACE, interface="socketcan")
seen: dict[int, int] = {}
sources: dict[int, set] = {}
count = 0
t0 = time.monotonic()

try:
    for _ in range(MAX_FRAMES):
        msg = bus.recv(timeout=2.0)
        if msg is None:
            print("(timeout — no CAN traffic)")
            continue
        if not msg.is_extended_id or msg.is_error_frame:
            continue
        pgn, src = extract_pgn(msg.arbitration_id)
        seen[pgn] = seen.get(pgn, 0) + 1
        sources.setdefault(pgn, set()).add(src)
        count += 1
except KeyboardInterrupt:
    pass
finally:
    bus.shutdown()

elapsed = time.monotonic() - t0
print(f"\n{'='*55}")
print(f"  {count} frames in {elapsed:.1f}s ({count/max(elapsed,0.01):.0f} fps)")
print(f"{'='*55}\n")
print(f"  {'PGN':>6}  {'Count':>5}  {'Sources':>10}  Name")
print(f"  {'---':>6}  {'-----':>5}  {'-------':>10}  ----")

for pgn in sorted(seen.keys()):
    name = EXPECTED_PGNS.get(pgn, "")
    marker = " <-- EXPECTED" if pgn in EXPECTED_PGNS else ""
    src_list = ",".join(f"0x{s:02X}" for s in sorted(sources[pgn]))
    print(f"  {pgn:>6}  {seen[pgn]:>5}  {src_list:>10}  {name}{marker}")

missing = set(EXPECTED_PGNS.keys()) - set(seen.keys())
if missing:
    print(f"\n  Missing expected PGNs: {sorted(missing)}")
else:
    print(f"\n  All expected PGNs found!")
