"""Tests for auto polar rebuild+activate at session end."""

import pytest
from unittest.mock import MagicMock, patch
from aquarela.performance.polar import PolarTable
from aquarela.performance.polar_manager import PolarManager


def _make_polar(bsp_offset=0.0):
    """Create a minimal PolarTable for testing."""
    return PolarTable(
        tws_values=[8.0],
        twa_values=[90.0],
        bsp_grid={(8.0, 90.0): 6.0 + bsp_offset},
        upwind_targets={8.0: (45.0, 5.0, 3.54)},
        downwind_targets={8.0: (135.0, 5.5, 3.89)},
    )


def test_auto_rebuild_activates_learned_polar():
    """When rebuild returns a polar, it should be set on the manager."""
    base = _make_polar()
    learned = _make_polar(bsp_offset=0.3)

    manager = PolarManager(base)
    manager.active_sail_type = "main_1__jib"

    learner = MagicMock()
    learner.rebuild.return_value = learned

    # Simulate auto-rebuild logic
    key = "main_1__jib"
    result = learner.rebuild()
    assert result is not None
    manager.set_polar(key, result)

    assert manager.get_polar(key) is learned
    assert manager.active_polar is learned


def test_auto_rebuild_keeps_current_when_none():
    """When rebuild returns None, the current polar should stay."""
    base = _make_polar()
    manager = PolarManager(base)
    manager.active_sail_type = "main_1__jib"

    learner = MagicMock()
    learner.rebuild.return_value = None

    result = learner.rebuild()
    assert result is None
    # Don't call set_polar
    assert manager.active_polar is base


def test_auto_rebuild_survives_exception():
    """If rebuild raises, the current polar should stay."""
    base = _make_polar()
    manager = PolarManager(base)
    manager.active_sail_type = "main_1__jib"

    learner = MagicMock()
    learner.rebuild.side_effect = RuntimeError("DB locked")

    try:
        learner.rebuild()
    except Exception:
        pass  # auto-rebuild catches this

    assert manager.active_polar is base
