"""Labeled accuracy benchmark + auto-tuner for Glance's skip decision.

Builds frame PAIRS with known ground truth across realistic agent scenarios, then
measures how well `is_meaningful_change` classifies them. The metric that matters:

  - missed_changes : real changes wrongly skipped (blinds the agent) -> MUST be 0
  - accuracy       : overall correct classification
  - skip_rate      : true skips on unchanged frames -> token savings

`--tune` grid-searches the policy and prints the best configs (zero missed changes
first, then highest accuracy, then most savings).

Run:
    python bench/eval.py            # score the current default policy
    python bench/eval.py --tune     # search for a better policy
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass

import cv2
import numpy as np

from glance import GlancePolicy
from glance.decide import is_meaningful_change

W, H = 1280, 720
RNG = random.Random(7)


# ----- frame synthesis ------------------------------------------------------

def _page(lines: list[str]) -> np.ndarray:
    img = np.full((H, W, 3), 245, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (W, 48), (60, 60, 60), -1)
    for i, line in enumerate(lines):
        cv2.putText(img, line, (24, 90 + i * 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (20, 20, 20), 1, cv2.LINE_AA)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _base_lines(n: int) -> list[str]:
    return [f"line {i+1}: the quick brown fox jumps over the lazy dog" for i in range(n)]


@dataclass
class Pair:
    prev: np.ndarray
    curr: np.ndarray
    changed: bool      # ground truth
    kind: str


def make_dataset(per_kind: int = 10) -> list[Pair]:
    pairs: list[Pair] = []
    for _ in range(per_kind):
        nlines = RNG.randint(3, 8)
        base = _page(_base_lines(nlines))

        # --- UNCHANGED (skipping these is the win) ---
        # exact duplicate (no-op action / redundant screenshot)
        pairs.append(Pair(base, base.copy(), False, "duplicate"))

        # compression / capture noise (+/-3 gray)
        noise = np.clip(base.astype(int) + RNG.randint(-3, 3), 0, 255).astype(np.uint8)
        pairs.append(Pair(base, noise, False, "noise"))

        # blinking text caret: thin tall sliver toggles on
        caret = base.copy()
        cx = 24 + RNG.randint(300, 500)
        cy = 90 + (nlines - 1) * 28
        cv2.rectangle(caret, (cx, cy - 14), (cx + 2, cy + 2), (0, 0, 0), -1)
        pairs.append(Pair(base, caret, False, "caret_blink"))

        # mouse cursor moved (agent moved its own mouse; no state change)
        ax, ay = RNG.randint(200, 600), RNG.randint(200, 600)
        bx, by = RNG.randint(700, 1100), RNG.randint(200, 600)
        cur_a, cur_b = base.copy(), base.copy()
        cv2.rectangle(cur_a, (ax, ay), (ax + 11, ay + 18), (0, 0, 0), -1)
        cv2.rectangle(cur_b, (bx, by), (bx + 11, by + 18), (0, 0, 0), -1)
        pairs.append(Pair(cur_a, cur_b, False, "cursor_move"))

        # --- CHANGED (missing these blinds the agent) ---
        # a single typed character appended to the last line
        char = _page(_base_lines(nlines)[:-1] + [_base_lines(nlines)[-1] + "X"])
        pairs.append(Pair(base, char, True, "single_char"))

        # adversarial: two characters typed at once -> TWO dark blobs. Must NOT be
        # mistaken for cursor motion (which is one-lighter + one-darker blob).
        two = _page(_base_lines(nlines)[:-1] + [_base_lines(nlines)[-1] + "XY"])
        pairs.append(Pair(base, two, True, "two_char"))

        # a whole new line appears
        pairs.append(Pair(base, _page(_base_lines(nlines + 1)), True, "new_line"))

        # button hover highlight (a recolored region)
        hover = base.copy()
        hx, hy = RNG.randint(800, 1000), RNG.randint(500, 600)
        cv2.rectangle(hover, (hx, hy), (hx + 90, hy + 30), (120, 120, 120), -1)
        pairs.append(Pair(base, hover, True, "hover"))

        # scroll: content shifts up
        scroll = np.roll(base, -28, axis=0)
        pairs.append(Pair(base, scroll, True, "scroll"))

        # page navigation: a totally different screen
        nav = np.full((H, W), 30, dtype=np.uint8)
        cv2.putText(nav, "different page", (40, 360), cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, (230, 230, 230), 2, cv2.LINE_AA)
        pairs.append(Pair(base, nav, True, "page_nav"))

    return pairs


# ----- scoring --------------------------------------------------------------

@dataclass
class Score:
    total: int
    correct: int
    missed_changes: int      # changed labeled True, predicted skip  (DANGER)
    false_sends: int         # unchanged labeled False, predicted send (waste)
    n_changed: int
    n_unchanged: int
    skipped_unchanged: int
    by_kind: dict

    @property
    def accuracy(self) -> float:
        return 100.0 * self.correct / self.total

    @property
    def skip_rate(self) -> float:
        return 100.0 * self.skipped_unchanged / max(self.n_unchanged, 1)


def score(policy: GlancePolicy, data: list[Pair]) -> Score:
    correct = missed = false_sends = skipped_unchanged = 0
    by_kind: dict[str, list[int]] = {}
    for p in data:
        changed, _ = is_meaningful_change(p.prev, p.curr, policy)
        ok = changed == p.changed
        correct += ok
        if p.changed and not changed:
            missed += 1
        if (not p.changed) and changed:
            false_sends += 1
        if (not p.changed) and (not changed):
            skipped_unchanged += 1
        agg = by_kind.setdefault(p.kind, [0, 0])
        agg[0] += ok
        agg[1] += 1
    return Score(
        total=len(data), correct=correct, missed_changes=missed,
        false_sends=false_sends,
        n_changed=sum(p.changed for p in data),
        n_unchanged=sum(not p.changed for p in data),
        skipped_unchanged=skipped_unchanged, by_kind=by_kind,
    )


def report(tag: str, s: Score) -> None:
    print(f"\n[{tag}]  accuracy={s.accuracy:.1f}%  "
          f"missed_changes={s.missed_changes}  false_sends={s.false_sends}  "
          f"skip_rate={s.skip_rate:.0f}%")
    for kind, (ok, n) in sorted(s.by_kind.items()):
        flag = "" if ok == n else "  <-- errors"
        print(f"    {kind:14} {ok}/{n}{flag}")


# ----- tuner ----------------------------------------------------------------

def tune(data: list[Pair]) -> None:
    grid = []
    for pixel in (4, 8, 12, 16, 20):
        for skip in (0.00005, 0.0001, 0.0003, 0.001, 0.002, 0.005):
            for caret in (False, True):
                pol = GlancePolicy(pixel_threshold=pixel, skip_threshold=skip,
                                   ignore_thin_carets=caret)
                s = score(pol, data)
                grid.append((pol, s))
    # rank: zero missed changes first, then accuracy, then savings
    grid.sort(key=lambda g: (g[1].missed_changes, -g[1].accuracy, -g[1].skip_rate))
    print("\n=== TOP CONFIGS (safe first: 0 missed changes, then accuracy, then savings) ===")
    print(f"  {'pixel':>5} {'skip_thr':>9} {'caret':>6} | {'acc':>6} {'missed':>6} {'skip%':>6}")
    for pol, s in grid[:8]:
        print(f"  {pol.pixel_threshold:>5} {pol.skip_threshold:>9} "
              f"{str(pol.ignore_thin_carets):>6} | {s.accuracy:>5.1f}% "
              f"{s.missed_changes:>6} {s.skip_rate:>5.0f}%")
    best = grid[0][0]
    print(f"\n  BEST: pixel_threshold={best.pixel_threshold} "
          f"skip_threshold={best.skip_threshold} "
          f"ignore_thin_carets={best.ignore_thin_carets}")
    report("BEST", grid[0][1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--per-kind", type=int, default=12)
    args = ap.parse_args()

    data = make_dataset(args.per_kind)
    print(f"dataset: {len(data)} labeled frame pairs "
          f"({sum(p.changed for p in data)} changed / "
          f"{sum(not p.changed for p in data)} unchanged)")

    report("current default policy", score(GlancePolicy(), data))
    if args.tune:
        tune(data)


if __name__ == "__main__":
    main()
