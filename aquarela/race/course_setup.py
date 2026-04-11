"""Pre-race course setup — map buoys by GPS logging or triangulation.

Each mark gets its own SightTriangulator instance.  The user adds marks,
captures positions (GPS or sight), defines the course sequence, then
applies the setup to the MarkStore for navigation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .marks import Mark, MarkStore
from .sight_triangulator import SightTriangulator


@dataclass
class CourseMarkSetup:
    """State for a single mark being set up."""

    name: str
    mark_type: str = "generic"
    method: Optional[str] = None  # None | "gps" | "sight"
    lat: Optional[float] = None
    lon: Optional[float] = None
    triangulator: SightTriangulator = field(default_factory=SightTriangulator)

    @property
    def is_resolved(self) -> bool:
        return self.lat is not None and self.lon is not None

    def to_dict(self) -> dict:
        cm = self.triangulator.computed_mark()
        return {
            "name": self.name,
            "mark_type": self.mark_type,
            "method": self.method,
            "lat": self.lat,
            "lon": self.lon,
            "resolved": self.is_resolved,
            "sight_count": self.triangulator.count,
            "computed_mark": cm,
        }


class CourseSetupManager:
    """Manages pre-race buoy mapping with per-mark triangulators."""

    def __init__(self) -> None:
        self._marks: Dict[str, CourseMarkSetup] = {}
        self._sequence: List[str] = []

    # ── Mark CRUD ──────────────────────────────────────────────────

    def add_mark(self, name: str, mark_type: str = "generic") -> CourseMarkSetup:
        """Create a pending mark. Overwrites if name already exists."""
        m = CourseMarkSetup(name=name, mark_type=mark_type)
        self._marks[name] = m
        return m

    def remove_mark(self, name: str) -> bool:
        if name in self._marks:
            del self._marks[name]
            self._sequence = [n for n in self._sequence if n != name]
            return True
        return False

    def get_mark(self, name: str) -> Optional[CourseMarkSetup]:
        return self._marks.get(name)

    def set_mark_type(self, name: str, mark_type: str) -> bool:
        """Change the type of a mark (generic, start_rc, start_pin, windward, leeward, gate)."""
        m = self._marks.get(name)
        if m is None:
            return False
        m.mark_type = mark_type
        return True

    # ── Position capture ───────────────────────────────────────────

    def log_gps(self, name: str, lat: float, lon: float) -> dict:
        """Capture current GPS position for a mark."""
        m = self._marks.get(name)
        if m is None:
            return {"error": f"Mark '{name}' not found"}
        m.lat = lat
        m.lon = lon
        m.method = "gps"
        return {"name": name, "lat": lat, "lon": lon, "method": "gps"}

    def add_sight(
        self, name: str, lat: float, lon: float, bearing: float
    ) -> dict:
        """Add a bearing sighting for triangulation."""
        m = self._marks.get(name)
        if m is None:
            return {"error": f"Mark '{name}' not found"}
        count = m.triangulator.add_sighting(lat, lon, bearing)
        computed = m.triangulator.computed_mark()
        if computed is not None:
            m.lat = computed["lat"]
            m.lon = computed["lon"]
            m.method = "sight"
        return {
            "name": name,
            "sight_count": count,
            "computed_mark": computed,
        }

    def reset_mark(self, name: str) -> bool:
        """Clear position and sightings for a mark."""
        m = self._marks.get(name)
        if m is None:
            return False
        m.lat = None
        m.lon = None
        m.method = None
        m.triangulator.reset()
        return True

    # ── Course sequence ────────────────────────────────────────────

    def set_sequence(self, names: List[str]) -> List[str]:
        """Set the course leg order. Returns the validated sequence."""
        self._sequence = list(names)
        return self._sequence

    @property
    def sequence(self) -> List[str]:
        return list(self._sequence)

    # ── Status ─────────────────────────────────────────────────────

    def status(self) -> dict:
        """Full state for frontend display."""
        marks = [m.to_dict() for m in self._marks.values()]
        resolved = sum(1 for m in self._marks.values() if m.is_resolved)
        return {
            "marks": marks,
            "sequence": self._sequence,
            "total": len(self._marks),
            "resolved": resolved,
            "ready": resolved == len(self._marks) and len(self._marks) > 0,
        }

    # ── Apply to navigation ────────────────────────────────────────

    def apply(self, mark_store: MarkStore) -> dict:
        """Push resolved marks into MarkStore and set course sequence.

        Returns applied marks list plus rc/pin positions for start line setup.
        """
        mark_store.clear_course_marks()
        applied = []
        rc = None
        pin = None
        for m in self._marks.values():
            if m.is_resolved:
                mark_store.add_mark(
                    Mark(m.name, m.lat, m.lon, m.mark_type)
                )
                applied.append(m.name)
                if m.mark_type == "start_rc":
                    rc = {"lat": m.lat, "lon": m.lon}
                elif m.mark_type == "start_pin":
                    pin = {"lat": m.lat, "lon": m.lon}
        mark_store.set_course_sequence(self._sequence)
        return {
            "applied": applied,
            "sequence": self._sequence,
            "total": len(applied),
            "rc": rc,
            "pin": pin,
        }
