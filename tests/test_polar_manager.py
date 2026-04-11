"""Tests for PolarManager with 6 sail config keys."""

import pytest

from aquarela.performance.polar_manager import SAIL_CONFIGS, PolarManager


class TestSailConfigs:
    def test_has_six_keys(self):
        assert len(SAIL_CONFIGS) == 6

    def test_keys_match_upwash(self):
        from aquarela.pipeline.upwash_table import SAIL_CONFIG_KEYS
        assert set(SAIL_CONFIGS.keys()) == set(SAIL_CONFIG_KEYS)

    def test_each_has_label_and_short(self):
        for key, info in SAIL_CONFIGS.items():
            assert "label" in info
            assert "short" in info


class TestPolarManagerConfigKeys:
    def test_init_creates_six_entries(self):
        pm = PolarManager()
        for key in SAIL_CONFIGS:
            assert key in pm._polars

    def test_set_active_valid(self):
        pm = PolarManager()
        pm.active_sail_type = "main_1__genoa"
        assert pm.active_sail_type == "main_1__genoa"

    def test_set_active_invalid_raises(self):
        pm = PolarManager()
        with pytest.raises(ValueError):
            pm.active_sail_type = "racing_white"  # old key should fail

    def test_default_active_sail_type(self):
        pm = PolarManager()
        assert pm.active_sail_type == "main_1__genoa"

    def test_active_polar_returns_none_without_base(self):
        pm = PolarManager()
        assert pm.active_polar is None

    def test_set_polar_valid(self):
        from unittest.mock import MagicMock
        from aquarela.performance.polar import PolarTable
        pm = PolarManager()
        mock_polar = MagicMock(spec=PolarTable)
        pm.set_polar("main_2__jib", mock_polar)
        assert pm.get_polar("main_2__jib") is mock_polar

    def test_set_polar_invalid_raises(self):
        from unittest.mock import MagicMock
        from aquarela.performance.polar import PolarTable
        pm = PolarManager()
        mock_polar = MagicMock(spec=PolarTable)
        with pytest.raises(ValueError):
            pm.set_polar("training_white", mock_polar)  # old key

    def test_reset_to_base(self):
        from unittest.mock import MagicMock
        from aquarela.performance.polar import PolarTable
        base = MagicMock(spec=PolarTable)
        override = MagicMock(spec=PolarTable)
        pm = PolarManager(base_polar=base)
        pm.set_polar("main_1__jib", override)
        assert pm.get_polar("main_1__jib") is override
        pm.reset_to_base("main_1__jib")
        assert pm.get_polar("main_1__jib") is base

    def test_all_six_config_keys_accessible(self):
        pm = PolarManager()
        expected_keys = {
            "main_1__jib", "main_1__genoa", "main_1__gennaker",
            "main_2__jib", "main_2__genoa", "main_2__gennaker",
        }
        assert set(pm._polars.keys()) == expected_keys
