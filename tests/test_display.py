"""Tests for the pure Display geometry (multi-display coordinate math)."""

from __future__ import annotations

from glance.display import Display, containing, main_display


def test_target_size_preserves_aspect():
    d = Display(0, 0, 1512, 982)
    tw, th = d.target_size(1366)
    assert tw == 1366
    assert abs(th / tw - 982 / 1512) < 0.01


def test_to_global_maps_corners_to_display_bounds():
    d = Display(1512, 0, 1920, 1080)                 # a second display, to the right
    tw, th = d.target_size(1366)
    assert d.to_global(0, 0, 1366) == (1512, 0)      # top-left -> display origin
    assert d.to_global(tw, th, 1366) == (1512 + 1920, 1080)  # bottom-right -> far corner


def test_global_target_roundtrip():
    d = Display(1512, 0, 1920, 1080)
    gx, gy = d.to_global(400, 300, 1366)
    tx, ty = d.global_to_target(gx, gy, 1366)
    assert abs(tx - 400) <= 1 and abs(ty - 300) <= 1


def test_contains_and_containing():
    a = Display(0, 0, 1512, 982)
    b = Display(1512, 0, 1920, 1080)
    assert a.contains(100, 100) and not a.contains(2000, 100)
    assert containing([a, b], 2000, 100) is b        # point on the second display
    assert containing([a, b], -50, 50) is None       # off all displays


def test_main_display_prefers_origin():
    a = Display(1512, 0, 1920, 1080)
    b = Display(0, 0, 1512, 982)
    assert main_display([a, b]) is b                 # the one at origin (0,0)
    assert main_display([]) is None
