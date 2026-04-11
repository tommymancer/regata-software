"""Tests for mark store and Lake Lugano pre-stored marks."""

import pytest
from aquarela.race.marks import Mark, MarkStore


class TestMark:
    def test_to_dict(self):
        m = Mark("Test", 46.0, 8.96, "windward")
        d = m.to_dict()
        assert d["name"] == "Test"
        assert d["lat"] == 46.0
        assert d["lon"] == 8.96
        assert d["mark_type"] == "windward"


class TestMarkStore:
    def test_loads_defaults(self):
        """Store loads Lake Lugano marks on init."""
        store = MarkStore()
        marks = store.list_marks()
        assert len(marks) >= 10  # at least 10 pre-stored marks

    def test_set_active(self):
        """Setting active mark by name works."""
        store = MarkStore()
        assert store.set_active("Windward")
        assert store.active_mark is not None
        assert store.active_mark.name == "Windward"

    def test_set_active_unknown(self):
        """Setting unknown mark returns False."""
        store = MarkStore()
        assert not store.set_active("Nonexistent")
        assert store.active_mark is None

    def test_clear_active(self):
        store = MarkStore()
        store.set_active("Windward")
        store.clear_active()
        assert store.active_mark is None

    def test_add_remove_mark(self):
        store = MarkStore()
        m = Mark("Custom", 46.01, 8.97)
        store.add_mark(m)
        assert store.get("Custom") is not None
        assert store.remove_mark("Custom")
        assert store.get("Custom") is None

    def test_remove_active_clears(self):
        """Removing the active mark clears the active selection."""
        store = MarkStore()
        store.set_active("Windward")
        store.remove_mark("Windward")
        assert store.active_mark is None

    def test_lugano_marks_have_coordinates(self):
        """All Lake Lugano marks have valid lat/lon."""
        store = MarkStore()
        for m in store.list_marks():
            assert 45.9 < m.lat < 46.1
            assert 8.9 < m.lon < 9.0

    def test_windward_mark_exists(self):
        store = MarkStore()
        m = store.get("Windward")
        assert m is not None
        assert m.mark_type == "windward"
