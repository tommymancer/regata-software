"""Mark waypoints — in-memory store with default Lake Lugano marks."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass
class Mark:
    """A racing mark / waypoint."""
    name: str
    lat: float
    lon: float
    mark_type: str = "generic"   # windward | leeward | gate | offset | start | reference

    def to_dict(self) -> dict:
        return asdict(self)


class MarkStore:
    """In-memory mark store, pre-loaded with Lake Lugano defaults."""

    def __init__(self) -> None:
        self._marks: Dict[str, Mark] = {}
        self._active_mark: Optional[str] = None
        self._course_sequence: List[str] = []   # ordered mark names for the race
        self._course_index: int = -1
        self._load_defaults()

    def _load_defaults(self) -> None:
        from .courses_lugano import LUGANO_MARKS
        for m in LUGANO_MARKS:
            self._marks[m.name] = m

    # ── Course sequence ───────────────────────────────────────────

    def set_course_sequence(self, mark_names: List[str]) -> None:
        """Define the ordered racing sequence (e.g. Windward → Leeward → Windward)."""
        self._course_sequence = [n for n in mark_names if n in self._marks]
        self._course_index = -1

    def next_mark(self) -> Optional[Mark]:
        """Advance to the next mark in the course sequence.

        Returns the new active mark, or None if no sequence or at end.
        """
        if not self._course_sequence:
            return None
        self._course_index = min(self._course_index + 1, len(self._course_sequence) - 1)
        name = self._course_sequence[self._course_index]
        self.set_active(name)
        return self.active_mark

    @property
    def course_leg(self) -> int:
        """Current leg number (1-based), or 0 if not started."""
        return self._course_index + 1

    @property
    def course_total_legs(self) -> int:
        return len(self._course_sequence)

    # ── Active mark ───────────────────────────────────────────────

    @property
    def active_mark(self) -> Optional[Mark]:
        if self._active_mark and self._active_mark in self._marks:
            return self._marks[self._active_mark]
        return None

    def set_active(self, name: str) -> bool:
        """Set the target mark for navigation.  Returns False if not found."""
        if name in self._marks:
            self._active_mark = name
            return True
        return False

    def clear_active(self) -> None:
        self._active_mark = None

    # ── CRUD ──────────────────────────────────────────────────────

    def list_marks(self) -> List[Mark]:
        return list(self._marks.values())

    def get(self, name: str) -> Optional[Mark]:
        return self._marks.get(name)

    def add_mark(self, mark: Mark) -> None:
        self._marks[mark.name] = mark

    def clear_course_marks(self) -> None:
        """Remove all non-reference marks (preparing for a fresh course setup)."""
        self._marks = {k: v for k, v in self._marks.items() if v.mark_type == "reference"}
        self._active_mark = None
        self._course_sequence = []
        self._course_index = -1

    def remove_mark(self, name: str) -> bool:
        if name in self._marks:
            del self._marks[name]
            if self._active_mark == name:
                self._active_mark = None
            return True
        return False
