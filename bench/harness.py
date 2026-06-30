"""Deterministic benchmark: run a screenshot trace through Glance, report savings.

This needs NO API key and NO desktop VM — it replays a folder of PNG frames and
counts the tokens a real loop WOULD send, with Glance on vs off. That makes the
headline number ("X% fewer image tokens at equal frames") reproducible by anyone
who clones the repo.

Run:
    python bench/make_synthetic_trace.py        # once, to create frames
    python bench/harness.py                       # benchmark on the synthetic trace
    python bench/harness.py --frames path/to/dir  # benchmark on your own frames
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from glance import GlancePolicy, Observer


def load_frames(folder: Path) -> list[bytes]:
    paths = sorted(folder.glob("*.png")) + sorted(folder.glob("*.jpg"))
    if not paths:
        raise SystemExit(
            f"No frames in {folder}. Run: python bench/make_synthetic_trace.py"
        )
    return [p.read_bytes() for p in paths]


def run(frames: list[bytes], enabled: bool) -> tuple[Observer, float]:
    observer = Observer(GlancePolicy(enabled=enabled))
    t0 = time.perf_counter()
    for frame in frames:
        observer.observe(frame)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return observer, elapsed_ms


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--frames",
        type=Path,
        default=Path(__file__).parent / "traces" / "synthetic",
        help="folder of *.png frames in capture order",
    )
    args = ap.parse_args()

    frames = load_frames(args.frames)

    baseline, base_ms = run(frames, enabled=False)   # full image every frame
    glance, glance_ms = run(frames, enabled=True)    # skip unchanged frames

    print(f"\nTrace: {args.frames}  ({len(frames)} frames)\n")
    print(f"  {'':14} {'tokens':>10} {'images sent':>13} {'diff time':>11}")
    print(f"  {'baseline':14} {baseline.stats.tokens_baseline:>10} "
          f"{baseline.stats.frames_total:>13} {base_ms:>9.1f}ms")
    print(f"  {'glance':14} {glance.stats.tokens_sent:>10} "
          f"{glance.stats.frames_total - glance.stats.frames_skipped:>13} "
          f"{glance_ms:>9.1f}ms")
    print()
    print(f"  frames skipped : {glance.stats.frames_skipped}/{glance.stats.frames_total} "
          f"({glance.stats.skip_rate:.0f}%)")
    print(f"  image tokens   : {glance.stats.tokens_sent} vs {glance.stats.tokens_baseline} "
          f"baseline")
    print(f"  >>> SAVED      : {glance.stats.tokens_saved} tokens "
          f"({glance.stats.pct_saved:.0f}% fewer image tokens)")
    avg_diff = glance_ms / max(len(frames), 1)
    print(f"\n  (diff cost {avg_diff:.2f} ms/frame — vs a ~1000 ms Claude call: "
          f"~{avg_diff / 1000 * 100:.2f}% of step time)\n")


if __name__ == "__main__":
    main()
