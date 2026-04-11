"""Tests for layline computation — bearings and cross-track distances."""

import math

import pytest

from aquarela.performance.laylines import compute_layline_distances, compute_laylines
from aquarela.performance.polar import PolarTable
from aquarela.pipeline.state import BoatState
from aquarela.race.navigation import haversine_distance


@pytest.fixture
def polar():
    return PolarTable.load("data/polars/2025_Polar.json")


def _make_state(**kwargs):
    s = BoatState.new()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


# ── compute_laylines ───────────────────────────────────────────────


class TestComputeLaylines:
    def test_upwind_returns_bearings(self, polar):
        s = _make_state(twd_deg=0.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5)
        port, stbd = compute_laylines(s, polar)
        assert port is not None
        assert stbd is not None

    def test_downwind_returns_bearings(self, polar):
        s = _make_state(twd_deg=180.0, tws_kt=10.0, twa_deg=150.0, bsp_kt=6.0)
        port, stbd = compute_laylines(s, polar)
        assert port is not None
        assert stbd is not None

    def test_missing_twd_returns_none(self, polar):
        s = _make_state(twd_deg=None, tws_kt=10.0, twa_deg=-42.0)
        port, stbd = compute_laylines(s, polar)
        assert port is None
        assert stbd is None

    def test_missing_tws_returns_none(self, polar):
        s = _make_state(twd_deg=0.0, tws_kt=None, twa_deg=-42.0)
        port, stbd = compute_laylines(s, polar)
        assert port is None
        assert stbd is None

    def test_bearings_bracket_twd_upwind(self, polar):
        """Upwind laylines should be on either side of TWD."""
        s = _make_state(twd_deg=0.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5)
        port, stbd = compute_laylines(s, polar)
        # Stbd layline: TWD + angle → clockwise from north
        assert stbd < 90
        # Port layline: TWD − angle → counterclockwise → near 360
        assert port > 270

    def test_leeway_widens_laylines(self, polar):
        """Non-zero leeway widens the effective layline angle."""
        s_no = _make_state(twd_deg=0.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5, leeway_deg=0.0)
        s_yes = _make_state(twd_deg=0.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5, leeway_deg=5.0)
        _, stbd_no = compute_laylines(s_no, polar)
        _, stbd_yes = compute_laylines(s_yes, polar)
        # Leeway widens the angle → stbd bearing further clockwise from 0
        assert stbd_yes > stbd_no

    def test_current_shifts_laylines(self, polar):
        """Current should shift laylines."""
        s_no = _make_state(twd_deg=0.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5)
        s_cur = _make_state(
            twd_deg=0.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5,
            current_set_deg=90.0, current_drift_kt=0.5,
        )
        p_no, _ = compute_laylines(s_no, polar)
        p_cur, _ = compute_laylines(s_cur, polar)
        assert p_no != pytest.approx(p_cur, abs=0.1)

    def test_bearings_in_range(self, polar):
        """Both bearings must be in [0, 360)."""
        for twd in [0.0, 90.0, 180.0, 270.0, 350.0, 5.0]:
            s = _make_state(twd_deg=twd, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5)
            port, stbd = compute_laylines(s, polar)
            assert 0 <= port < 360, f"port={port} for twd={twd}"
            assert 0 <= stbd < 360, f"stbd={stbd} for twd={twd}"

    def test_bearings_wrap_360(self, polar):
        """TWD near 360 should wrap correctly."""
        s = _make_state(twd_deg=355.0, tws_kt=10.0, twa_deg=-42.0, bsp_kt=5.5)
        port, stbd = compute_laylines(s, polar)
        assert 0 <= port < 360
        assert 0 <= stbd < 360


# ── compute_layline_distances ──────────────────────────────────────


# Lake Lugano mark (Campione area)
MARK_LAT = 46.0065
MARK_LON = 8.963


class TestComputeLaylineDistances:
    def test_no_gps_returns_none(self):
        s = _make_state(lat=None, lon=None)
        dp, ds = compute_layline_distances(s, MARK_LAT, MARK_LON, 315.0, 45.0)
        assert dp is None
        assert ds is None

    def test_boat_on_layline_zero_distance(self):
        """Boat on the port layline bearing from mark → cross-track ~0."""
        # Place boat 0.3 NM on bearing 315 from mark
        d_rad = 0.3 / 3440.065
        brg_rad = math.radians(315)
        boat_lat = MARK_LAT + math.degrees(d_rad * math.cos(brg_rad))
        boat_lon = MARK_LON + math.degrees(
            d_rad * math.sin(brg_rad) / math.cos(math.radians(MARK_LAT))
        )
        s = _make_state(lat=boat_lat, lon=boat_lon)
        dp, ds = compute_layline_distances(s, MARK_LAT, MARK_LON, 315.0, 45.0)
        assert dp == pytest.approx(0.0, abs=0.01)

    def test_distances_always_positive(self):
        """Cross-track distances are always >= 0."""
        s = _make_state(lat=46.001, lon=8.960)
        dp, ds = compute_layline_distances(s, MARK_LAT, MARK_LON, 315.0, 45.0)
        assert dp >= 0
        assert ds >= 0

    def test_perpendicular_equals_full_distance(self):
        """Boat perpendicular to layline → cross-track = full distance."""
        # Boat due east of mark. Layline due north (0°).
        # Bearing mark→boat = 90°. Angle = 0−90 = −90°. sin(90)=1.
        s = _make_state(lat=MARK_LAT, lon=MARK_LON + 0.005)
        dp, _ = compute_layline_distances(s, MARK_LAT, MARK_LON, 0.0, 180.0)
        full_dist = haversine_distance(MARK_LAT, MARK_LON, MARK_LAT, MARK_LON + 0.005)
        assert dp == pytest.approx(full_dist, abs=0.005)

    def test_symmetry_on_bearing_swap(self):
        """Swapping port/stbd bearings swaps the distances."""
        s = _make_state(lat=46.003, lon=8.960)
        dp1, ds1 = compute_layline_distances(s, MARK_LAT, MARK_LON, 315.0, 45.0)
        dp2, ds2 = compute_layline_distances(s, MARK_LAT, MARK_LON, 45.0, 315.0)
        assert dp1 == pytest.approx(ds2, abs=0.001)
        assert ds1 == pytest.approx(dp2, abs=0.001)

    def test_boat_on_stbd_layline(self):
        """Boat on stbd layline bearing → stbd distance ~0."""
        d_rad = 0.2 / 3440.065
        brg_rad = math.radians(45)
        boat_lat = MARK_LAT + math.degrees(d_rad * math.cos(brg_rad))
        boat_lon = MARK_LON + math.degrees(
            d_rad * math.sin(brg_rad) / math.cos(math.radians(MARK_LAT))
        )
        s = _make_state(lat=boat_lat, lon=boat_lon)
        _, ds = compute_layline_distances(s, MARK_LAT, MARK_LON, 315.0, 45.0)
        assert ds == pytest.approx(0.0, abs=0.01)
