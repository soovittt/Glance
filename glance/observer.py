"""The integration surface: drop `Observer` into your computer-use loop.

Typical use:

    from glance import Observer

    observer = Observer()
    ...
    # in your agent loop, after every action:
    screenshot_png = take_screenshot()             # your code
    obs = observer.observe(screenshot_png)         # Glance decides
    tool_result_content = obs.blocks               # full image OR a tiny text note
    messages.append({"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tid, "content": tool_result_content}
    ]})

When the screen didn't change, `obs.blocks` is a ~15-token text note instead of a
~1,100-token image. Claude still has the previous real screenshot in its history,
so "nothing changed" is enough for it to keep going.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import numpy as np

from .decide import is_meaningful_change
from .diff import to_array, to_gray
from .metrics import GlanceStats, estimate_image_tokens
from .policy import GlancePolicy

SKIP_TEXT = (
    "[glance] No visual change since your previous screenshot. "
    "The screen is identical to your last view; continue from that state."
)


@dataclass
class Observation:
    """What observe() returns for a single frame."""

    kind: str                       # "full" | "skip"
    blocks: list[dict[str, Any]]    # content blocks ready to drop into a tool_result
    changed_fraction: float
    bbox: tuple[int, int, int, int] | None
    image_tokens: int               # tokens this frame WOULD cost as a full image

    @property
    def skipped(self) -> bool:
        return self.kind == "skip"


def _image_block(png_bytes: bytes) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.b64encode(png_bytes).decode("ascii"),
        },
    }


def _encode_png(arr: np.ndarray) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".png", arr)
    if not ok:
        raise ValueError("Failed to PNG-encode frame")
    return buf.tobytes()


class Observer:
    """Stateful frame gate. Holds the previous frame and decides skip vs send."""

    def __init__(self, policy: GlancePolicy | None = None):
        self.policy = policy or GlancePolicy()
        self.stats = GlanceStats()
        self._prev_gray: np.ndarray | None = None

    def observe(self, image, force: bool = False) -> Observation:
        """Compare `image` to the previous frame; return blocks to send to Claude.

        `image` may be PNG/JPEG bytes, a NumPy array, or a PIL image.
        `force=True` always returns the full image (bypasses skipping) while still
        updating the baseline and stats — an escape hatch when the caller wants to
        look no matter what.
        """
        arr = to_array(image)
        gray = to_gray(arr)
        height, width = gray.shape[:2]
        image_tokens = estimate_image_tokens(width, height)

        # First frame, or feature disabled => always send the full image.
        is_first = self._prev_gray is None
        changed_fraction = 1.0
        bbox: tuple[int, int, int, int] | None = None

        if is_first or not self.policy.enabled or force:
            skip = False
        else:
            changed, d = is_meaningful_change(self._prev_gray, gray, self.policy)
            changed_fraction = d.changed_fraction
            bbox = d.bbox
            skip = not changed

        if skip:
            blocks = [{"type": "text", "text": SKIP_TEXT}]
            kind = "skip"
        else:
            png = image if isinstance(image, (bytes, bytearray)) else _encode_png(arr)
            blocks = [_image_block(bytes(png))]
            kind = "full"
            self._prev_gray = gray  # only update the reference when we actually "looked"

        # On a skip we keep the OLD reference frame on purpose: we want to detect
        # drift against the last frame Claude actually saw, not the last raw frame.

        self.stats.record(skipped=skip, image_tokens=image_tokens)
        return Observation(
            kind=kind,
            blocks=blocks,
            changed_fraction=changed_fraction,
            bbox=bbox,
            image_tokens=image_tokens,
        )

    def reset(self) -> None:
        """Forget the previous frame (e.g. when starting a new task)."""
        self._prev_gray = None
