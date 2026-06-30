"""Direct tests for the token-accounting module."""

from __future__ import annotations

from glance import GlanceStats, estimate_image_tokens
from glance.metrics import SKIP_NOTE_TOKENS


def test_estimate_image_tokens_matches_formula():
    assert estimate_image_tokens(1024, 768) == round(1024 * 768 / 750)
    assert estimate_image_tokens(0, 0) == 0


def test_stats_accumulate_sent_vs_baseline():
    s = GlanceStats()
    s.record(skipped=False, image_tokens=1000)   # sent in full
    s.record(skipped=True, image_tokens=1000)    # skipped -> only the note
    assert s.frames_total == 2
    assert s.frames_skipped == 1
    assert s.tokens_baseline == 2000
    assert s.tokens_sent == 1000 + SKIP_NOTE_TOKENS
    assert s.tokens_saved == 1000 - SKIP_NOTE_TOKENS
    assert s.skip_rate == 50.0
    assert 0 < s.pct_saved < 100


def test_empty_stats_are_zero_not_div_by_zero():
    s = GlanceStats()
    assert s.pct_saved == 0.0
    assert s.skip_rate == 0.0
    assert "frames=0" in s.summary()
