"""The single source of truth for 'did the screen meaningfully change?'

Both the live Observer and the offline evaluator call this, so the benchmark
measures exactly the code the agent runs — no drift between eval and production.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class Decision:
    """A skip/send decision plus *why* — the telemetry needed to tune accuracy."""

    changed: bool          # True => send the image; False => safe to skip
    reason: str            # below_threshold | big_change | caret | cursor_motion | changed
    diff: FrameDiff

    @property
    def changed_fraction(self) -> float:
        return self.diff.changed_fraction


def explain(prev_gray: np.ndarray, curr_gray: np.ndarray, policy: GlancePolicy) -> Decision:
    """Full decision with a reason label, so callers can log *why* and tune thresholds.

    Decision order:
      1. Below the skip threshold (essentially identical) -> skip (below_threshold).
      2. Above the 'clearly changed' fraction -> send (big_change), no blob analysis.
      3. Ambiguous small-change band: suppress a blinking caret or a moving mouse
         cursor -> skip (caret / cursor_motion). Otherwise -> send (changed).
    """
    d = diff_frames(prev_gray, curr_gray, policy.pixel_threshold)

    if d.changed_fraction < policy.skip_threshold:
        return Decision(False, "below_threshold", d)
    if d.changed_fraction >= policy.big_change_fraction:
        return Decision(True, "big_change", d)
    if policy.ignore_thin_carets and _is_caret(d.bbox, policy):
        return Decision(False, "caret", d)
    if policy.ignore_cursor_motion and _is_cursor_motion(prev_gray, curr_gray, policy):
        return Decision(False, "cursor_motion", d)
    return Decision(True, "changed", d)


def is_meaningful_change(
    prev_gray: np.ndarray,
    curr_gray: np.ndarray,
    policy: GlancePolicy,
) -> tuple[bool, FrameDiff]:
    """Return (changed, diff). `changed=False` means it's safe to skip the image."""
    dec = explain(prev_gray, curr_gray, policy)
    return dec.changed, dec.diff
