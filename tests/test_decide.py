"""Unit tests for the hard discriminations the loop added."""

from __future__ import annotations

import cv2
import numpy as np

from glance import GlancePolicy
from glance.decide import is_meaningful_change


def _page() -> np.ndarray:
    img = np.full((720, 1280), 245, dtype=np.uint8)
    cv2.putText(img, "hello world", (24, 120), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (20,), 1, cv2.LINE_AA)
    return img


POLICY = GlancePolicy()


def test_caret_blink_is_skipped():
    base = _page()
    caret = base.copy()
    cv2.rectangle(caret, (300, 106), (302, 124), (0,), -1)  # thin tall sliver
    changed, _ = is_meaningful_change(base, caret, POLICY)
    assert changed is False


def test_single_char_is_sent():
    base = _page()
    typed = base.copy()
    cv2.putText(typed, "X", (250, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20,), 1, cv2.LINE_AA)
    changed, _ = is_meaningful_change(base, typed, POLICY)
    assert changed is True, "a typed character must never be skipped"


def test_cursor_move_is_skipped():
    base = _page()
    a, b = base.copy(), base.copy()
    cv2.rectangle(a, (200, 200), (211, 218), (0,), -1)   # cursor at A
    cv2.rectangle(b, (800, 300), (811, 318), (0,), -1)   # cursor at B
    changed, _ = is_meaningful_change(a, b, POLICY)
    assert changed is False


def test_two_chars_not_mistaken_for_cursor_move():
    base = _page()
    typed = base.copy()
    cv2.putText(typed, "XY", (250, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20,), 1, cv2.LINE_AA)
    changed, _ = is_meaningful_change(base, typed, POLICY)
    assert changed is True, "two dark blobs are text, not a cursor move"
