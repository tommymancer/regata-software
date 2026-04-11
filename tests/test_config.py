"""Tests for configuration loading and saving."""

import json
import os
import tempfile

import pytest

from aquarela.config import AquarelaConfig


class TestConfigDefaults:
    def test_default_creation(self):
        cfg = AquarelaConfig()
        assert cfg.compass_offset == 0.0
        assert cfg.speed_factor == 1.0
        assert cfg.sample_rate_hz == 10
        assert cfg.magnetic_variation == 2.5

    def test_no_sail_type_field(self):
        cfg = AquarelaConfig()
        assert not hasattr(cfg, "sail_type")

    def test_sail_config_key_default(self):
        cfg = AquarelaConfig()
        assert cfg.sail_config_key() == "main_1__genoa"

    def test_default_damping(self):
        cfg = AquarelaConfig()
        assert cfg.damping["tws_kt"] == 5.0
        assert cfg.damping["twd_deg"] == 10.0
        assert cfg.damping["bsp_kt"] == 2.0

    def test_load_missing_file_returns_defaults(self):
        cfg = AquarelaConfig.load("/nonexistent/path/config.json")
        assert cfg.compass_offset == 0.0
        assert cfg.source == "can0"


class TestConfigLoadSave:
    def test_round_trip(self):
        """Save then load should preserve values."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test-config.json")
            original = AquarelaConfig(
                compass_offset=3.5,
                speed_factor=1.02,
                awa_offset=-1.0,
                magnetic_variation=3.0,
                sample_rate_hz=20,
                source="interactive",
                initial_twd=200.0,
                initial_tws=14.0,
            )
            original.save(path)
            loaded = AquarelaConfig.load(path)

            assert loaded.compass_offset == 3.5
            assert loaded.speed_factor == 1.02
            assert loaded.awa_offset == -1.0
            assert loaded.magnetic_variation == 3.0
            assert loaded.sample_rate_hz == 20
            assert loaded.source == "interactive"
            assert loaded.initial_twd == 200.0
            assert loaded.initial_tws == 14.0

    def test_save_creates_parent_dirs(self):
        """Save should create intermediate directories."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "dir", "config.json")
            AquarelaConfig().save(path)
            assert os.path.exists(path)

    def test_load_partial_json(self):
        """Config should handle JSON missing optional keys."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"source": "interactive", "magnetic_variation": 5.0}, f)
            f.flush()
            cfg = AquarelaConfig.load(f.name)

        os.unlink(f.name)
        assert cfg.source == "interactive"
        assert cfg.magnetic_variation == 5.0
        assert cfg.compass_offset == 0.0  # default
