"""Performance targets — compute PERF% and VMG-PERF% from polar table.

Computes:
  - target_bsp:  polar BSP at current TWA/TWS
  - target_twa:  optimal VMG angle (upwind or downwind)
  - target_vmg:  polar VMG at optimal angle
  - perf_pct:    BSP / target_bsp × 100  (how well we sail vs polar)
  - vmg_perf_pct: VMG / target_vmg × 100 (how well we make ground)
"""

import math
from typing import Optional

from ..pipeline.state import BoatState
from .polar import PolarTable


def compute_targets(state: BoatState, polar: PolarTable) -> None:
    """Mutate *state* in-place with performance target fields.

    Requires calibrated twa_deg, tws_kt, bsp_kt to be present.
    """
    if state.twa_deg is None or state.tws_kt is None or state.bsp_kt is None:
        return

    twa = state.twa_deg
    tws = state.tws_kt
    abs_twa = abs(twa)

    # Target BSP from polar at current TWA/TWS
    target_bsp = polar.bsp(twa, tws)
    if target_bsp is not None and target_bsp > 0:
        state.target_bsp_kt = target_bsp
        state.perf_pct = (state.bsp_kt / target_bsp) * 100.0
    else:
        state.target_bsp_kt = None
        state.perf_pct = None

    # Determine if upwind or downwind, get optimal VMG targets
    is_upwind = abs_twa < 90

    if is_upwind:
        target = polar.target_upwind(tws)
    else:
        target = polar.target_downwind(tws)

    if target is not None:
        target_twa, target_bsp_opt, target_vmg = target

        # Target TWA (signed to match current tack/gybe)
        state.target_twa_deg = math.copysign(target_twa, twa) if twa != 0 else target_twa

        # Target VMG and VMG-PERF%. Convention: compare magnitudes.
        # Upwind VMG is positive (BSP·cos(TWA) with TWA<90), downwind is
        # negative (TWA>90); target_vmg from the polar is always magnitude.
        # We report % of the optimal VMG in absolute terms — direction is
        # implicit from the TWA sign / tack state.
        state.target_vmg_kt = target_vmg
        if state.vmg_kt is not None and target_vmg > 0:
            state.vmg_perf_pct = (abs(state.vmg_kt) / target_vmg) * 100.0
        else:
            state.vmg_perf_pct = None
    else:
        state.target_twa_deg = None
        state.target_vmg_kt = None
        state.vmg_perf_pct = None
