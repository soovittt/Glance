"""The Glance self-improvement loop:  measure -> compare -> prioritize.

Runs the verifiable task suite, scores correctness + efficiency, diffs against the
previous run to catch regressions, and prints a prioritized list of what to change
next. The reward is efficiency **gated by correctness** — a change is only worth
keeping if the success rate holds.

It does NOT rewrite code on its own; it tells you (or a coding agent) exactly where the
wins and regressions are, so every change is deliberate and measured. The intended
cycle: run the loop -> make ONE change -> run the loop again -> keep it only if
`compare` shows no regression and efficiency improved.

Run:  python -m bench.suite.loop            # run the suite, then report + findings
      python -m bench.suite.loop --no-run   # report on the latest saved run only
"""

from __future__ import annotations

import argparse

from . import report
from .runner import run_suite

IMG_TOKENS = 1616


def findings(results) -> str:
    fails = [r for r in results if not r.ok and not r.manual]
    heavy = [r for r in results
             if r.tool_mix.get("ui_tree", 0) == 0 and r.tool_mix.get("computer_screenshot", 0) >= 3]

    lines = ["=== next actions (most valuable first) ===", "1. Correctness (fix before optimizing):"]
    lines += ([f"   - {r.id}: {r.detail}" for r in fails]
              or ["   - none — every auto-checked task passes"])
    lines.append("2. Adoption wins (screenshot-heavy, never used ui_tree):")
    lines += ([f"   - {r.id}: {r.tool_mix.get('computer_screenshot', 0)} screenshots, 0 ui_tree "
               f"(~{r.tool_mix.get('computer_screenshot', 0) * IMG_TOKENS} tok ui_tree could cut)"
               for r in heavy]
              or ["   - none — good structured-observation usage"])
    lines.append("3. Frame-skip thresholds: `python bench/eval.py --tune` (labeled-data auto-tune)")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-run", action="store_true",
                    help="report on the latest saved run without re-running the suite")
    ap.add_argument("--simulate", action="store_true",
                    help="dry-run the harness with synthetic results (no agent, no screen)")
    ap.add_argument("--catalog", action="store_true",
                    help="run the ~1000-task catalog (all apps) instead of the 150-task suite")
    args = ap.parse_args()

    if args.no_run:
        r = report.runs()
        if not r:
            raise SystemExit("no runs yet — drop --no-run to run the suite first")
        results = report.load_results(r[-1])
    elif args.catalog:
        from .catalog import build
        results = run_suite(tasks=build(), simulate=args.simulate)
    else:
        results = run_suite(simulate=args.simulate)

    print("\n" + report.score(results))
    r = report.runs()
    if len(r) >= 2:
        print("\n" + report.compare(report.load_results(r[-2]), results))
    print("\n" + findings(results))


if __name__ == "__main__":
    main()
