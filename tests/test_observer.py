"""Direct tests for the Observer integration surface (force, reset, block shapes)."""

from __future__ import annotations

import numpy as np

from glance import GlancePolicy, Observer


def _frame(color: int = 245) -> np.ndarray:
    return np.full((720, 1280, 3), color, dtype=np.uint8)


def test_force_bypasses_skip():
    obs = Observer(GlancePolicy())
    obs.observe(_frame())                       # first frame
    r = obs.observe(_frame(), force=True)        # identical, but forced
    assert r.kind == "full" and not r.skipped


def test_reset_makes_next_frame_full_again():
    obs = Observer(GlancePolicy())
    obs.observe(_frame())
    obs.reset()
    r = obs.observe(_frame())                    # treated as the first frame again
    assert r.kind == "full"


def test_skip_returns_text_block_send_returns_image_block():
    obs = Observer(GlancePolicy())
    sent = obs.observe(_frame())
    assert sent.blocks[0]["type"] == "image"
    skipped = obs.observe(_frame())              # identical -> skipped
    assert skipped.skipped
    assert skipped.blocks[0]["type"] == "text"


def test_observation_reports_tokens_and_fraction():
    obs = Observer(GlancePolicy())
    r = obs.observe(_frame())
    assert r.image_tokens > 0
    assert 0.0 <= r.changed_fraction <= 1.0
