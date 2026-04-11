"""Pre-stored Lake Lugano racing marks.

Positions approximate the typical racing area in the
Lugano–Paradiso basin (Circolo Velico Lugano).

Prevailing winds:
  - Breva  (S/SW, afternoon thermal, 8–16 kt)
  - Tivano (N, morning drainage, 6–12 kt)
"""

from .marks import Mark

# fmt: off
LUGANO_MARKS = [
    # ── Start / Finish line ────────────────────────────────────
    Mark("RC Boat",      46.0000,  8.9615, "start"),
    Mark("Pin End",      46.0000,  8.9645, "start"),

    # ── Windward marks (~0.4 NM north of start) ───────────────
    Mark("Windward",     46.0065,  8.9630, "windward"),
    Mark("Offset",       46.0055,  8.9665, "offset"),

    # ── Leeward / Gate (~0.35 NM south of start) ──────────────
    Mark("Leeward",      45.9940,  8.9630, "leeward"),
    Mark("Gate Port",    45.9938,  8.9615, "gate"),
    Mark("Gate Stbd",    45.9938,  8.9645, "gate"),

    # ── Shore references ──────────────────────────────────────
    Mark("Paradiso",     45.9880,  8.9520, "reference"),
    Mark("Cassarate",    46.0050,  8.9580, "reference"),
    Mark("Gandria",      46.0150,  8.9720, "reference"),
    Mark("Campione",     45.9700,  8.9700, "reference"),
    Mark("Melide",       45.9580,  8.9490, "reference"),
]
# fmt: on
