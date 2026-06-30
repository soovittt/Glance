"""Generate a synthetic screenshot trace so the benchmark runs with zero setup.

It mimics a real agent session: a "document editor" where most steps make a tiny
change (one line of text appears) and a meaningful fraction of steps make NO
visible change at all — e.g. a no-op action, a redundant screenshot, or waiting
on something. Those no-change frames are exactly what Glance skips.

Run:  python bench/make_synthetic_trace.py
Writes PNG frames to bench/traces/synthetic/frame_0000.png ...
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).parent / "traces" / "synthetic"
W, H = 1280, 720
N_FRAMES = 30


def render(lines: list[str]) -> np.ndarray:
    img = np.full((H, W, 3), 245, dtype=np.uint8)          # near-white "page"
    cv2.rectangle(img, (0, 0), (W, 48), (60, 60, 60), -1)  # static title bar
    cv2.putText(img, "untitled.txt - editor", (16, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 1, cv2.LINE_AA)
    for i, line in enumerate(lines):
        y = 90 + i * 28
        cv2.putText(img, line, (24, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (20, 20, 20), 1, cv2.LINE_AA)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for f in range(N_FRAMES):
        # Every 3rd frame is a no-op (identical to the previous one) — a redundant
        # observation. ~33% of frames, which Glance should skip.
        if f % 3 != 0 or f == 0:
            lines = lines + [f"line {len(lines) + 1}: the quick brown fox jumps over the lazy dog"]
        img = render(lines)
        path = OUT / f"frame_{f:04d}.png"
        cv2.imwrite(str(path), img)
    print(f"Wrote {N_FRAMES} frames to {OUT}")


if __name__ == "__main__":
    main()
