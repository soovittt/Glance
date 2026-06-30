"""Tests for the video-to-frames sampling math (codec-free, CI-safe)."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))

from video_to_frames import _sample_step  # noqa: E402


@pytest.mark.parametrize("src_fps,fps_sample,expected", [
    (30, 2, 15),     # 30fps source, want 2/s -> every 15th frame
    (60, 2, 30),
    (24, 12, 2),
    (30, 30, 1),     # sample as fast as source -> every frame
    (30, 100, 1),    # can't sample faster than source -> clamp to 1
    (30, 0, 1),      # guard against divide-by-zero
    (0, 2, 15),      # unknown source fps -> assume 30
])
def test_sample_step(src_fps, fps_sample, expected):
    assert _sample_step(src_fps, fps_sample) == expected
