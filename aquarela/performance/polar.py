"""Polar table — load Aquarela polar JSON and interpolate target BSP.

The polar file (data/polars/2025_Polar.json) is exported from the Vakaros
Atlas 2 and contains BSP values at discrete TWA/TWS grid points.  This
module builds a lookup table and provides bilinear interpolation to get
the expected BSP at any TWA/TWS.
"""

import json
import math
from bisect import bisect_left
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PolarTable:
    """Interpolated polar lookup for the Nitro 80 'Aquarela'.

    Loaded from the Atlas 2 JSON format which contains:
      - polars[0].polarData: list of {tws, twa, metricValue (=BSP)}
      - targets: upwind/downwind optimal TWA, BSP, VMG per TWS

    Usage:
        polar = PolarTable.load("data/polars/2025_Polar.json")
        target_bsp = polar.bsp(twa=42, tws=10)  # → ~5.85
    """

    def __init__(
        self,
        tws_values: List[float],
        twa_values: List[float],
        bsp_grid: Dict[Tuple[float, float], float],
        upwind_targets: Dict[float, Tuple[float, float, float]],
        downwind_targets: Dict[float, Tuple[float, float, float]],
    ):
        self.tws_values = sorted(tws_values)
        self.twa_values = sorted(twa_values)
        self.bsp_grid = bsp_grid  # (tws, twa) → BSP
        # targets: tws → (twa, bsp, vmg)
        self.upwind_targets = upwind_targets
        self.downwind_targets = downwind_targets

    @classmethod
    def load(cls, path: str = "data/polars/2025_Polar.json") -> "PolarTable":
        """Load polar data from Atlas 2 JSON export."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Polar file not found: {path}")

        with open(p) as f:
            raw = json.load(f)

        # Parse polar grid
        bsp_grid: Dict[Tuple[float, float], float] = {}
        tws_set: set = set()
        twa_set: set = set()

        for entry in raw.get("polars", [{}])[0].get("polarData", []):
            tws = entry["tws"]
            twa = entry["twa"]
            bsp = entry["metricValue"]
            bsp_grid[(tws, twa)] = bsp
            tws_set.add(tws)
            twa_set.add(twa)

        # Parse targets
        upwind_twa: Dict[float, float] = {}
        upwind_bsp: Dict[float, float] = {}
        upwind_vmg: Dict[float, float] = {}
        downwind_twa: Dict[float, float] = {}
        downwind_bsp: Dict[float, float] = {}
        downwind_vmg: Dict[float, float] = {}

        for target in raw.get("targets", []):
            pos = target["pointOfSail"]
            metric = target["metric"]
            for entry in target["targetData"]:
                tws = entry["tws"]
                val = entry["metricValue"]
                if pos == "Upwind":
                    if metric == "TWA":
                        upwind_twa[tws] = val
                    elif metric == "BoatSpeed":
                        upwind_bsp[tws] = val
                    elif metric == "VMG":
                        upwind_vmg[tws] = val
                elif pos == "Downwind":
                    if metric == "TWA":
                        downwind_twa[tws] = val
                    elif metric == "BoatSpeed":
                        downwind_bsp[tws] = val
                    elif metric == "VMG":
                        downwind_vmg[tws] = val

        # Merge into (twa, bsp, vmg) tuples per TWS
        upwind_targets = {}
        for tws in upwind_twa:
            upwind_targets[tws] = (
                upwind_twa[tws],
                upwind_bsp.get(tws, 0.0),
                upwind_vmg.get(tws, 0.0),
            )

        downwind_targets = {}
        for tws in downwind_twa:
            downwind_targets[tws] = (
                downwind_twa[tws],
                downwind_bsp.get(tws, 0.0),
                downwind_vmg.get(tws, 0.0),
            )

        return cls(
            tws_values=list(tws_set),
            twa_values=list(twa_set),
            bsp_grid=bsp_grid,
            upwind_targets=upwind_targets,
            downwind_targets=downwind_targets,
        )

    def bsp(self, twa: float, tws: float) -> Optional[float]:
        """Interpolated polar BSP at given TWA and TWS.

        Uses |twa| (polars are symmetric port/stbd).
        Returns None if outside the polar range.
        """
        abs_twa = abs(twa)
        if not self.tws_values or not self.twa_values:
            return None
        if tws < self.tws_values[0] * 0.5 or abs_twa < 20:
            return None

        return self._bilinear(abs_twa, tws)

    def _bilinear(self, twa: float, tws: float) -> Optional[float]:
        """Bilinear interpolation on the (tws, twa) grid.

        The grid is irregular (different TWA values per TWS column),
        so we interpolate in TWS first, then TWA.
        """
        # Clamp TWS to table range
        tws = max(self.tws_values[0], min(self.tws_values[-1], tws))

        # Find bracketing TWS columns
        i = bisect_left(self.tws_values, tws)
        if i == 0:
            return self._interp_column(self.tws_values[0], twa)
        if i >= len(self.tws_values):
            return self._interp_column(self.tws_values[-1], twa)

        tws_lo = self.tws_values[i - 1]
        tws_hi = self.tws_values[i]

        bsp_lo = self._interp_column(tws_lo, twa)
        bsp_hi = self._interp_column(tws_hi, twa)

        if bsp_lo is None or bsp_hi is None:
            return bsp_lo if bsp_lo is not None else bsp_hi

        t = (tws - tws_lo) / (tws_hi - tws_lo) if tws_hi != tws_lo else 0.0
        return bsp_lo + t * (bsp_hi - bsp_lo)

    def _interp_column(self, tws: float, twa: float) -> Optional[float]:
        """Interpolate BSP at a given TWS column for arbitrary TWA."""
        # Get all TWA/BSP pairs for this TWS column
        pairs = []
        for (t_tws, t_twa), bsp in self.bsp_grid.items():
            if t_tws == tws:
                pairs.append((t_twa, bsp))

        if not pairs:
            return None

        pairs.sort()
        twas = [p[0] for p in pairs]
        bsps = [p[1] for p in pairs]

        # Clamp TWA to column range
        if twa <= twas[0]:
            return bsps[0]
        if twa >= twas[-1]:
            return bsps[-1]

        # Linear interpolation
        j = bisect_left(twas, twa)
        if j == 0:
            return bsps[0]

        twa_lo, bsp_lo = twas[j - 1], bsps[j - 1]
        twa_hi, bsp_hi = twas[j], bsps[j]

        t = (twa - twa_lo) / (twa_hi - twa_lo) if twa_hi != twa_lo else 0.0
        return bsp_lo + t * (bsp_hi - bsp_lo)

    def target_upwind(self, tws: float) -> Optional[Tuple[float, float, float]]:
        """Interpolated upwind target (twa, bsp, vmg) for given TWS."""
        return self._interp_target(self.upwind_targets, tws)

    def target_downwind(self, tws: float) -> Optional[Tuple[float, float, float]]:
        """Interpolated downwind target (twa, bsp, vmg) for given TWS."""
        return self._interp_target(self.downwind_targets, tws)

    def _interp_target(
        self, targets: Dict[float, Tuple[float, float, float]], tws: float
    ) -> Optional[Tuple[float, float, float]]:
        """Interpolate a target tuple across TWS values."""
        if not targets:
            return None

        tws_keys = sorted(targets.keys())
        tws = max(tws_keys[0], min(tws_keys[-1], tws))

        i = bisect_left(tws_keys, tws)

        if i == 0:
            return targets.get(tws_keys[0])
        if tws_keys[i - 1] == tws:
            return targets.get(tws_keys[i - 1])
        if i >= len(tws_keys):
            return targets[tws_keys[-1]]

        lo_tws = tws_keys[i - 1]
        hi_tws = tws_keys[i]
        lo = targets[lo_tws]
        hi = targets[hi_tws]

        t = (tws - lo_tws) / (hi_tws - lo_tws) if hi_tws != lo_tws else 0.0
        return (
            lo[0] + t * (hi[0] - lo[0]),
            lo[1] + t * (hi[1] - lo[1]),
            lo[2] + t * (hi[2] - lo[2]),
        )
