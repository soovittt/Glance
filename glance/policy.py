"""Configuration knobs for Glance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GlancePolicy:
    """Tunables that control when Glance skips a frame.

    skip_threshold: if the fraction of changed pixels is BELOW this, the frame is
        treated as "unchanged" and the image is dropped in favor of a text note.
        0.002 == "skip if less than 0.2% of pixels changed". Raise it to skip more
        aggressively (cheaper, riskier); lower it to be more conservative.
    pixel_threshold: per-pixel intensity delta (0-255) required to count a pixel as
        changed. Filters compression noise and cursor shimmer.
    enabled: master switch. When False, observe() always sends the full image —
        used as the A/B baseline in the benchmark.
    """

    # Tuned by bench/eval.py against a labeled dataset: this is the LOWEST safe
    # noise floor — high enough to skip identical/noisy frames, low enough that a
    # single typed character (~1e-4 of the screen) is never wrongly skipped. The
    # caret rule below handles the structured-but-ignorable case (cursor blink).
    skip_threshold: float = 0.00005
    pixel_threshold: int = 12
    enabled: bool = True

    # Caret/cursor-blink suppression: a thin, tall, tiny-area changed region is a
    # blinking text cursor, not actionable state. Lets us keep skip_threshold low
    # (never miss a typed character) without sending a frame on every blink.
    ignore_thin_carets: bool = True
    caret_max_width: int = 3
    caret_min_height: int = 8
    caret_max_area: int = 120

    # Cursor-motion suppression: the agent moving its own mouse changes only the
    # cursor's pixels (one region gets lighter where it left, one gets darker where
    # it arrived). That's not actionable state. Detected via connected components +
    # opposite-luminance-direction, which is what keeps typed text (all-darker) safe.
    ignore_cursor_motion: bool = True
    cursor_max_area: int = 400        # a mouse cursor is small; text edits aren't
    min_blob_area: int = 8            # ignore sub-noise specks when counting blobs
    big_change_fraction: float = 0.005  # above this, it's clearly a real change -> send
