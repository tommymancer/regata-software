"""Configuration management — loads/saves aquarela-config.json."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class AquarelaConfig:
    """Runtime configuration loaded from aquarela-config.json.

    Calibration offsets match the pipeline defined in Aquarela Njord CSV Spec.
    """

    # Calibration (from Njord CSV Spec)
    compass_offset: float = 0.0
    speed_factor: float = 1.0
    awa_offset: float = 0.0
    depth_offset: float = -1.85       # keel depth on Nitro 80
    tws_downwind_factor: float = 1.0
    magnetic_variation: float = 2.5   # Lake Lugano ≈ +2.5° east (2025)

    # Sail inventory
    sails: dict = field(default_factory=lambda: {
        "mains": ["main_1", "main_2"],
        "headsails": {
            "jib": ["jib_1"],
            "genoa": ["genoa_1"],
            "gennaker": ["gennaker_1", "gennaker_2"],
        },
    })
    active_main: str = "main_1"
    active_headsail: str = "genoa_1"

    # Upwash learning
    upwash_learning_rate: float = 0.1
    upwash_learning_enabled: bool = True

    # CAN writer
    can_writer_enabled: bool = False
    can_writer_dry_run: bool = True

    # Sampling rates
    sample_rate_hz: int = 10          # internal pipeline rate
    csv_rate_hz: int = 2              # CSV logging rate (Njord spec)
    websocket_rate_hz: int = 10       # WebSocket push rate

    # Damping windows (seconds)
    damping: Dict[str, float] = field(default_factory=lambda: {
        "tws_kt": 5.0,
        "twd_deg": 10.0,
        "bsp_kt": 2.0,
        "vmg_kt": 3.0,
    })

    # Display
    theme: str = "night"
    pages: list = field(default_factory=lambda: [
        "upwind", "wind_rose", "downwind", "nav",
        "performance", "race_timer", "trim", "system",
    ])

    # Data source
    source: str = "can0"         # "simulator", "interactive", or "can1"
    initial_twd: float = 180.0        # initial true wind direction (interactive mode)
    initial_tws: float = 10.0         # initial true wind speed (interactive mode)

    # Calibration timestamps (ISO format, per instrument)
    cal_timestamps: Dict[str, str] = field(default_factory=dict)

    def sail_config_key(self) -> str:
        """Derive the upwash table key from active sail selection."""
        headsails = self.sails.get("headsails", {})
        category = "genoa"  # default
        for cat, names in headsails.items():
            if self.active_headsail in names:
                category = cat
                break
        return f"{self.active_main}__{category}"

    @classmethod
    def load(cls, path: str = "data/aquarela-config.json") -> "AquarelaConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p) as f:
            raw = json.load(f)
        cal = raw.get("calibration", {})

        # Backward compat: if old sail_type present but no active_main, map to new fields
        _old_st = raw.get("sail_type")
        _default_main = "main_1"
        _default_head = "genoa_1"
        if _old_st and "active_main" not in raw:
            _mapping = {
                "training_white": ("main_1", "genoa_1"),
                "racing_white": ("main_1", "genoa_1"),
                "racing_gennaker": ("main_1", "gennaker_1"),
                "racing_gennaker_runner": ("main_1", "gennaker_1"),
            }
            _default_main, _default_head = _mapping.get(_old_st, ("main_1", "genoa_1"))

        return cls(
            compass_offset=cal.get("compass", {}).get("offset", 0.0),
            speed_factor=cal.get("speed", {}).get("factor", 1.0),
            awa_offset=cal.get("wind", {}).get("awa_offset", 0.0),
            tws_downwind_factor=cal.get("wind", {}).get("tws_downwind_factor", 1.0),
            depth_offset=cal.get("depth", {}).get("offset", -1.85),
            magnetic_variation=raw.get("magnetic_variation", 2.5),
            sample_rate_hz=raw.get("sample_rate_hz", 10),
            csv_rate_hz=raw.get("csv_rate_hz", 2),
            websocket_rate_hz=raw.get("websocket_rate_hz", 10),
            damping=raw.get("damping", {
                "tws_kt": 5.0, "twd_deg": 10.0, "bsp_kt": 2.0, "vmg_kt": 3.0,
            }),
            theme=raw.get("theme", "night"),
            pages=raw.get("pages", [
                "upwind", "wind_rose", "downwind", "nav",
                "performance", "race_timer", "trim", "system",
            ]),
            source=raw.get("source", "can0"),
            initial_twd=raw.get("initial_twd", 180.0),
            initial_tws=raw.get("initial_tws", 10.0),
            cal_timestamps=raw.get("cal_timestamps", {}),
            sails=raw.get("sails", {
                "mains": ["main_1", "main_2"],
                "headsails": {
                    "jib": ["jib_1"],
                    "genoa": ["genoa_1"],
                    "gennaker": ["gennaker_1", "gennaker_2"],
                },
            }),
            active_main=raw.get("active_main", _default_main),
            active_headsail=raw.get("active_headsail", _default_head),
            upwash_learning_rate=raw.get("upwash_learning_rate", 0.1),
            upwash_learning_enabled=raw.get("upwash_learning_enabled", True),
            can_writer_enabled=raw.get("can_writer_enabled", False),
            can_writer_dry_run=raw.get("can_writer_dry_run", True),
        )

    def save(self, path: str = "data/aquarela-config.json") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "calibration": {
                "compass": {"offset": self.compass_offset},
                "speed": {"factor": self.speed_factor},
                "wind": {
                    "awa_offset": self.awa_offset,
                    "tws_downwind_factor": self.tws_downwind_factor,
                },
                "depth": {"offset": self.depth_offset},
            },
            "magnetic_variation": self.magnetic_variation,
            "sample_rate_hz": self.sample_rate_hz,
            "csv_rate_hz": self.csv_rate_hz,
            "websocket_rate_hz": self.websocket_rate_hz,
            "damping": self.damping,
            "theme": self.theme,
            "pages": self.pages,
            "source": self.source,
            "initial_twd": self.initial_twd,
            "initial_tws": self.initial_tws,
            "cal_timestamps": self.cal_timestamps,
            "sails": self.sails,
            "active_main": self.active_main,
            "active_headsail": self.active_headsail,
            "upwash_learning_rate": self.upwash_learning_rate,
            "upwash_learning_enabled": self.upwash_learning_enabled,
            "can_writer_enabled": self.can_writer_enabled,
            "can_writer_dry_run": self.can_writer_dry_run,
        }
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
