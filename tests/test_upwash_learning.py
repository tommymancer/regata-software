"""Tests for upwash auto-learning (UpwashLearner)."""

import random

import pytest

from aquarela.pipeline.upwash_learning import UpwashLearner, _angle_diff, _angle_mean


# ── helpers ─────────────────────────────────────────────────────────────

def feed_n(learner, n, twd=180.0, awa=30.0, heel=10.0, bsp=5.0, sail="main_1__jib"):
    """Feed n identical samples at hz=1 (one update = one second)."""
    result = None
    for _ in range(n):
        r = learner.update(twd, awa, heel, bsp, sail)
        if r is not None:
            result = r
    return result


# ── test 1: tack detection ─────────────────────────────────────────────

def test_tack_detection_triggers_post_tack():
    """AWA sign change must move state to post_tack."""
    learner = UpwashLearner(hz=1, buffer_seconds=180, pre_window=120, post_window=120)

    # Feed positive AWA for a while
    feed_n(learner, 5, awa=30.0)
    assert learner.state == "waiting"

    # Sign change → post_tack
    learner.update(180.0, -30.0, 10.0, 5.0, "main_1__jib")
    assert learner.state == "post_tack"


def test_no_sign_change_stays_waiting():
    """Without AWA sign change, state stays waiting."""
    learner = UpwashLearner(hz=1, buffer_seconds=180, pre_window=120, post_window=120)

    feed_n(learner, 50, awa=30.0)
    assert learner.state == "waiting"


# ── test 2: rejects unstable wind ──────────────────────────────────────

def test_rejects_unstable_post_tack_wind():
    """Noisy post-tack TWD (std >> 5 deg) must be rejected."""
    learner = UpwashLearner(hz=1, buffer_seconds=300, pre_window=120, post_window=120)

    # Stable pre-tack: 120 samples with TWD=180, AWA=+30
    feed_n(learner, 120, twd=180.0, awa=30.0, heel=10.0, bsp=5.0)

    # Tack (AWA sign change)
    learner.update(180.0, -30.0, 10.0, 5.0, "main_1__jib")
    assert learner.state == "post_tack"

    # Noisy post-tack: TWD jumping ±20 degrees
    random.seed(42)
    for i in range(120):
        noisy_twd = 180.0 + random.uniform(-20, 20)
        learner.update(noisy_twd, -30.0, 10.0, 5.0, "main_1__jib")

    # Should have been evaluated (AWA is stable at -30) and rejected
    assert learner.state == "waiting"
    assert learner.last_result == "rejected_twd_unstable_post"


# ── test 3: rejects low BSP ────────────────────────────────────────────

def test_rejects_low_bsp():
    """BSP < 3 kt in pre-window must be rejected."""
    learner = UpwashLearner(hz=1, buffer_seconds=300, pre_window=120, post_window=120)

    # Pre-tack with low BSP
    feed_n(learner, 120, twd=180.0, awa=30.0, heel=10.0, bsp=2.0)

    # Tack
    learner.update(180.0, -30.0, 10.0, 2.0, "main_1__jib")
    assert learner.state == "post_tack"

    # Stable post-tack
    feed_n(learner, 120, twd=180.0, awa=-30.0, heel=10.0, bsp=2.0)

    assert learner.state == "waiting"
    assert learner.last_result == "rejected_low_bsp"


# ── test 4: clean tack produces update ─────────────────────────────────

def test_clean_tack_produces_residual():
    """Stable TWD=180 pre, TWD=184 post → residual ~ 2.0 degrees."""
    learner = UpwashLearner(hz=1, buffer_seconds=300, pre_window=120, post_window=120)

    # Pre-tack: TWD=180, AWA=+30
    feed_n(learner, 120, twd=180.0, awa=30.0, heel=10.0, bsp=5.0)

    # Tack (AWA sign flip)
    learner.update(184.0, -30.0, 10.0, 5.0, "main_1__jib")
    assert learner.state == "post_tack"

    # Post-tack: TWD=184, AWA=-30 (stable), 120 samples
    result = feed_n(learner, 120, twd=184.0, awa=-30.0, heel=10.0, bsp=5.0)

    # The settle check triggers at 30 samples but we need 120 for post_window
    # After 120 samples the maneuver should be evaluated
    assert learner.state == "waiting"
    assert learner.last_result == "updated"
    assert result is not None

    residual, mean_awa, mean_heel, sail = result
    assert abs(residual - 2.0) < 0.5
    assert sail == "main_1__jib"


# ── helper function unit tests ──────────────────────────────────────────

def test_angle_diff_wrap():
    assert abs(_angle_diff(10, 350) - 20.0) < 1e-9
    assert abs(_angle_diff(350, 10) - (-20.0)) < 1e-9
    assert abs(_angle_diff(180, 180)) < 1e-9


def test_angle_mean_wrap():
    """Circular mean of 350 and 10 should be ~0 (north)."""
    m = _angle_mean([350, 10])
    assert m < 5 or m > 355
