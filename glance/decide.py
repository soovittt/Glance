"""The single source of truth for 'did the screen meaningfully change?'

Both the live Observer and the offline evaluator call this, so the benchmark
measures exactly the code the agent runs — no drift between eval and production.
"""

from __future__ import annotations

import cv2
import numpy as np

from .diff import FrameDiff, diff_frames
from .policy import GlancePolicy


def _is_caret(bbox, policy: GlancePolicy) -> bool:
    """A thin, tall, tiny-area changed region == a blinking text caret."""
    if bbox is None:
        return False
    _, _, w, h = bbox
    return (
        w <= policy.caret_max_width
        and h >= policy.caret_min_height
        and (w * h) <= policy.caret_max_area
    )


def _is_cursor_motion(prev_gray: np.ndarray, curr_gray: np.ndarray, policy: GlancePolicy) -> bool:
    """True iff the only change is a mouse cursor moving from A to B.

    Signature of a cursor move: exactly two small, similarly-sized changed blobs,
    one that got *lighter* (cursor left) and one that got *darker* (cursor arrived).
    Typed text is all-darker with no matching lighter blob, so it never matches —
    that asymmetry is what preserves the 'never miss a real change' guarantee.
    """
    delta = curr_gray.astype(np.int16) - prev_gray.astype(np.int16)
    mask = (np.abs(delta) > policy.pixel_threshold).astype(np.uint8)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    blobs = []
    for i in range(1, n):  # label 0 is background
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < policy.min_blob_area:
            continue  # ignore sub-noise specks
        net = float(delta[labels == i].mean())  # >0 brighter, <0 darker
        blobs.append((area, net))

    if len(blobs) != 2:
        return False
    (a_area, a_net), (b_area, b_net) = blobs
    if a_area > policy.cursor_max_area or b_area > policy.cursor_max_area:
        return False
    if a_net * b_net >= 0:          # need opposite directions (one lighter, one darker)
        return False
    bigger = max(a_area, b_area)
    smaller = min(a_area, b_area)
    return smaller >= 0.4 * bigger  # similarly sized (same cursor shape)


def is_meaningful_change(
    prev_gray: np.ndarray,
    curr_gray: np.ndarray,
    policy: GlancePolicy,
) -> tuple[bool, FrameDiff]:
    """Return (changed, diff). `changed=False` means it's safe to skip the image.

    Decision order:
      1. Below the skip threshold (essentially identical) -> unchanged.
      2. Above the 'clearly changed' fraction -> changed (skip the expensive
         blob analysis for big, obvious updates).
      3. In the ambiguous small-change band, suppress known non-actionable motion:
         a blinking caret, or a mouse cursor moving. Otherwise -> changed.
    """
    d = diff_frames(prev_gray, curr_gray, policy.pixel_threshold)

    # (1) essentially identical
    if d.changed_fraction < policy.skip_threshold:
        return False, d

    # (2) clearly a real change -> don't bother analyzing
    if d.changed_fraction >= policy.big_change_fraction:
        return True, d

    # (3) ambiguous small change: is it just a caret or a cursor move?
    if policy.ignore_thin_carets and _is_caret(d.bbox, policy):
        return False, d
    if policy.ignore_cursor_motion and _is_cursor_motion(prev_gray, curr_gray, policy):
        return False, d

    return True, d
