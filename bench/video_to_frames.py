"""Turn a screen recording into a frame trace, to measure Glance on REAL footage.

Record any computer-use session (QuickTime screen recording, a Cowork/agent demo,
etc.), then:

    python bench/video_to_frames.py session.mov
    python bench/harness.py --frames bench/traces/session

You get the real token-savings number on actual footage — no API key, no live agent.
By default it samples ~2 frames/sec (agents act at most a few times per second), so
the trace approximates the screenshots a loop would actually take.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def _sample_step(src_fps: float, fps_sample: float) -> int:
    """How many source frames to skip between saved frames. Always >= 1."""
    if fps_sample <= 0:
        return 1
    return max(1, round((src_fps or 30.0) / fps_sample))


def extract(video_path: Path, out_dir: Path, fps_sample: float = 2.0) -> int:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"could not open video: {video_path}")
    step = _sample_step(cap.get(cv2.CAP_PROP_FPS), fps_sample)
    out_dir.mkdir(parents=True, exist_ok=True)
    idx = saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            cv2.imwrite(str(out_dir / f"frame_{saved:05d}.png"), frame)
            saved += 1
        idx += 1
    cap.release()
    return saved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path, help="screen recording (.mov/.mp4/...)")
    ap.add_argument("--fps", type=float, default=2.0, help="frames/sec to sample")
    ap.add_argument("--out", type=Path, default=None, help="output frame dir")
    args = ap.parse_args()
    out = args.out or (Path(__file__).parent / "traces" / args.video.stem)
    n = extract(args.video, out, args.fps)
    print(f"wrote {n} frames to {out}\nnow run: python bench/harness.py --frames {out}")


if __name__ == "__main__":
    main()
