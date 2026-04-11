"""Shared fixtures for Aquarela test suite."""

import pytest

from aquarela.config import AquarelaConfig
from aquarela.performance.polar import PolarTable
from aquarela.pipeline.state import BoatState


@pytest.fixture
def default_config():
    """Default config with no file on disk."""
    return AquarelaConfig()


@pytest.fixture
def polar():
    """Loaded polar table from the standard data file."""
    return PolarTable.load("data/polars/2025_Polar.json")


@pytest.fixture
def base_state():
    """Fresh BoatState with typical upwind values pre-filled."""
    s = BoatState.new()
    s.heading_mag = 40.0
    s.awa_deg = -35.0
    s.aws_kt = 12.0
    s.bsp_kt = 5.5
    s.lat = 46.0
    s.lon = 8.963
    s.sog_kt = 5.3
    s.cog_deg = 42.0
    s.depth_m = 50.0
    s.magnetic_variation = 2.5
    return s
