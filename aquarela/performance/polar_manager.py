"""PolarManager — holds one PolarTable per sail configuration.

Manages 6 independent polar tables (2 mains × 3 headsail categories).
All start from the same base polar and diverge as real sailing data is learned.
"""

from typing import Dict, Optional

from ..pipeline.upwash_table import SAIL_CONFIG_KEYS
from .polar import PolarTable

SAIL_CONFIGS: Dict[str, dict] = {
    "main_1__jib":       {"label": "Randa All + Fiocco All",       "short": "RA/FA"},
    "main_1__genoa":     {"label": "Randa All + Genoa Race",       "short": "RA/GR"},
    "main_1__gennaker":  {"label": "Randa All + Gennaker",         "short": "RA/GK"},
    "main_2__jib":       {"label": "Randa Race + Fiocco All",      "short": "RR/FA"},
    "main_2__genoa":     {"label": "Randa Race + Genoa Race",      "short": "RR/GR"},
    "main_2__gennaker":  {"label": "Randa Race + Gennaker",        "short": "RR/GK"},
}

# Human-readable names for individual sails (used in picker UI)
MAIN_LABELS: Dict[str, str] = {
    "main_1": "Randa All",
    "main_2": "Randa Race",
}
HEADSAIL_LABELS: Dict[str, str] = {
    "jib_1": "Fiocco All",
    "genoa_1": "Genoa Race",
    "gennaker_1": "Gennaker Blu",
    "gennaker_2": "Runner",
}


class PolarManager:
    """Holds a dict of PolarTable for all 6 sail configurations."""

    def __init__(self, base_polar: Optional[PolarTable] = None) -> None:
        self._base_polar = base_polar
        self._active_sail_type: str = "main_1__genoa"
        self._polars: Dict[str, Optional[PolarTable]] = {
            key: base_polar for key in SAIL_CONFIGS
        }

    @property
    def active_sail_type(self) -> str:
        return self._active_sail_type

    @active_sail_type.setter
    def active_sail_type(self, sail_type: str) -> None:
        if sail_type not in SAIL_CONFIGS:
            raise ValueError(f"Unknown sail config: {sail_type}")
        self._active_sail_type = sail_type

    @property
    def active_polar(self) -> Optional[PolarTable]:
        return self._polars.get(self._active_sail_type)

    @property
    def base_polar(self) -> Optional[PolarTable]:
        return self._base_polar

    def get_polar(self, sail_type: str) -> Optional[PolarTable]:
        return self._polars.get(sail_type)

    def set_polar(self, sail_type: str, polar: PolarTable) -> None:
        if sail_type not in SAIL_CONFIGS:
            raise ValueError(f"Unknown sail config: {sail_type}")
        self._polars[sail_type] = polar

    def reset_to_base(self, sail_type: str) -> None:
        if sail_type not in SAIL_CONFIGS:
            raise ValueError(f"Unknown sail config: {sail_type}")
        self._polars[sail_type] = self._base_polar
