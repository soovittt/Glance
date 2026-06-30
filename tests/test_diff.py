"""Unit tests for the diff engine and the Observer skip decision."""

from __future__ import annotations

import numpy as np

from glance import GlancePolicy, Observer, diff_frames, dhash, hamming


def _frame(color: int = 245) -> np.ndarray:
    return np.full((720, 1280, 3), color, dtype=np.uint8)


def _gray(color: int = 245) -> np.ndarray:
    return np.full((720, 1280), color, dtype=np.uint8)


def test_identical_frames_not_changed():
    d = diff_frames(_gray(), _gray())
    assert d.changed_fraction == 0.0
    assert d.bbox is None


def test_big_change_detected_with_bbox():
    a = _gray(245)
    b = _gray(245)
    b[100:200, 300:500] = 0          # paint a black rectangle
    d = diff_frames(a, b)
    assert d.changed_fraction > 0.01
    assert d.bbox is not None
    x, y, w, h = d.bbox
    assert (x, y, w, h) == (300, 100, 200, 100)


def test_dhash_identical_is_zero_distance():
    assert hamming(dhash(_frame()), dhash(_frame())) == 0


def test_observer_skips_unchanged_frame():
    obs = Observer(GlancePolicy())
    first = obs.observe(_frame())            # first frame is always sent
    assert first.kind == "full"
    second = obs.observe(_frame())           # identical -> skipped
    assert second.kind == "skip"
    assert obs.stats.frames_skipped == 1


def test_observer_sends_changed_frame():
    obs = Observer(GlancePolicy())
    obs.observe(_frame(245))
    changed = _frame(245)
    changed[:, :640] = 0                      # half the screen goes black
    result = obs.observe(changed)
    assert result.kind == "full"
    assert obs.stats.frames_skipped == 0


def test_disabled_policy_never_skips():
    obs = Observer(GlancePolicy(enabled=False))
    obs.observe(_frame())
    result = obs.observe(_frame())
    assert result.kind == "full"
