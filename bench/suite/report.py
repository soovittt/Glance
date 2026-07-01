"""Score a suite run (correctness + efficiency) and compare it to the previous run."""

from __future__ import annotations

import json
from pathlib import Path

from .model import TaskResult

RESULTS_DIR = Path(__file__).parent / "results"
IMG_TOKENS = 1616   # ~one screenshot; the naive loop would spend this per round-trip


def load_results(path: str | Path) -> list[TaskResult]:
    return [TaskResult.from_dict(d) for d in json.loads(Path(path).read_text())]


def runs() -> list[Path]:
    return sorted(RESULTS_DIR.glob("run_*.json"))


def _pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def score(results: list[TaskResult]) -> str:
    auto = [r for r in results if not r.manual]
    passed = [r for r in auto if r.ok]
    manual = [r for r in results if r.manual]
    tokens = sum(r.tokens for r in results)
    naive_tokens = sum(r.naive_round_trips for r in results) * IMG_TOKENS
    rt = sum(r.round_trips for r in results)
    naive_rt = sum(r.naive_round_trips for r in results)

    lines = [
        "=== suite scorecard ===",
        f"tasks         : {len(results)}  ({len(manual)} manual — excluded from success rate)",
        f"success rate  : {len(passed)}/{len(auto)} ({_pct(len(passed), len(auto))}%)",
    ]
    for diff in ("easy", "medium", "hard"):
        d = [r for r in auto if r.difficulty == diff]
        if d:
            lines.append(f"  {diff:8}    : {sum(r.ok for r in d)}/{len(d)} ({_pct(sum(r.ok for r in d), len(d))}%)")
    total_time = sum(r.duration_s for r in results)
    slowest = sorted(results, key=lambda r: -r.duration_s)[:3]
    lines += [
        f"round-trips   : {rt} vs naive ~{naive_rt}  ({_pct(naive_rt - rt, naive_rt)}% fewer)",
        f"tokens        : {tokens} vs naive ~{naive_tokens}  ({_pct(naive_tokens - tokens, naive_tokens)}% fewer)",
        f"time          : {total_time / 60:.1f} min total, {total_time / max(len(results), 1):.1f}s/task avg",
        "  slowest     : " + ", ".join(f"{r.id} {r.duration_s:.0f}s" for r in slowest),
    ]
    fails = [r for r in auto if not r.ok]
    if fails:
        lines.append("\nfailures:")
        lines += [f"  {r.id}: {r.detail}" for r in fails]
    if manual:
        lines.append("\nmanual (check by hand):")
        lines += [f"  {r.id}: {r.detail}" for r in manual]
    return "\n".join(lines)


def compare(prev: list[TaskResult], curr: list[TaskResult]) -> str:
    prev_ok = {r.id for r in prev if r.ok}
    curr_ok = {r.id for r in curr if r.ok}
    regressed = sorted(prev_ok - curr_ok)
    fixed = sorted(curr_ok - prev_ok)
    dt = sum(r.tokens for r in curr) - sum(r.tokens for r in prev)
    lines = ["=== vs previous run ==="]
    lines.append(f"regressed (passed before, fail now): {', '.join(regressed) or 'none'}")
    lines.append(f"newly passing                      : {', '.join(fixed) or 'none'}")
    lines.append(f"token delta                        : {dt:+d}")
    if regressed:
        lines.append("!! REGRESSION — a change broke correctness; revert or fix before keeping it.")
    return "\n".join(lines)


def main() -> None:
    r = runs()
    if not r:
        raise SystemExit("no runs yet — python -m bench.suite.runner")
    curr = load_results(r[-1])
    print(score(curr))
    if len(r) >= 2:
        print("\n" + compare(load_results(r[-2]), curr))


if __name__ == "__main__":
    main()
