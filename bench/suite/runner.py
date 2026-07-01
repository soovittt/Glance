"""Run the task suite and record correctness + efficiency for each task.

For every task: clean the slate, reset telemetry, run the agent **headless** via
`claude -p` (which uses your registered glance-cua MCP on your subscription), verify
the end state, then read the per-task telemetry the server wrote. Results are saved to
`bench/suite/results/run_<ts>.json`.

Run:  python -m bench.suite.runner            # whole suite
      python -m bench.suite.runner --ids calc_mul,note_groceries
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from glance import telemetry

from .model import Task, TaskResult
from .tasks import TASKS

RESULTS_DIR = Path(__file__).parent / "results"
# Headless automation needs approval gates off so the agent can drive the screen; the
# glance-cua tools come from your registered MCP config. This MUST be launched by you
# in your own terminal — a nested agent can't disable its own permission gates.
DEFAULT_AGENT = ["claude", "-p", "--permission-mode", "bypassPermissions"]


def simulate_result(task: Task, idx: int) -> TaskResult:
    """A deterministic synthetic result — no agent, no screen. Lets you dry-run the whole
    harness (scoring, time, regression diff, findings) without burning tokens."""
    h = int(hashlib.md5(task.id.encode()).hexdigest(), 16)
    ok = (h % 100) < 80                                    # ~80% "pass" for a realistic mix
    base = {"easy": 6, "medium": 12, "hard": 20}[task.difficulty]
    rt = base + (h % 7)
    saved = (h // 7) % 10
    heavy = (h % 5 == 0)                                   # some screenshot-heavy tasks
    mix = {"computer_batch": max(1, rt // 3),
           "computer_screenshot": 5 if heavy else 1}
    if not heavy and h % 2:
        mix["ui_tree"] = 2
    return TaskResult(id=task.id, difficulty=task.difficulty, ok=ok, manual=False,
                      detail="verified (sim)" if ok else "artifact missing (sim)",
                      tokens=rt * 1200 + (h % 500), round_trips=rt, naive_round_trips=rt + saved,
                      tool_mix=mix, duration_s=round(base * 2.5 + (h % 30), 1))


def _telemetry_metrics() -> dict:
    """Aggregate the telemetry the server wrote for the task just run."""
    recs = telemetry.load()
    saved = sum(int(r.get("round_trips_saved", 0) or 0) for r in recs)
    tokens = 0
    for r in recs:
        est = int(r.get("est_tokens", 0) or 0)
        skip = r.get("modality") == "image" and r.get("event") == "skip"
        tokens += 15 if skip else est
    return {
        "round_trips": len(recs),
        "naive_round_trips": len(recs) + saved,
        "tokens": tokens,
        "tool_mix": dict(Counter(r.get("tool", "?") for r in recs)),
    }


def run_task(task: Task, agent_cmd: list[str] = DEFAULT_AGENT, timeout: int = 300) -> TaskResult:
    if task.setup:
        try:
            task.setup()
        except Exception:  # noqa: BLE001 - setup is best-effort clean-up
            pass
    telemetry.reset()
    t0 = time.perf_counter()
    try:
        subprocess.run([*agent_cmd, task.prompt], timeout=timeout, capture_output=True, text=True)
    except (subprocess.TimeoutExpired, OSError):
        pass
    dt = round(time.perf_counter() - t0, 1)
    res = task.verify()
    return TaskResult(id=task.id, difficulty=task.difficulty, ok=res.ok, manual=res.manual,
                      detail=res.detail, duration_s=dt, **_telemetry_metrics())


def run_suite(tasks: list[Task] = TASKS, agent_cmd: list[str] = DEFAULT_AGENT,
              timeout: int = 300, simulate: bool = False) -> list[TaskResult]:
    results: list[TaskResult] = []
    t0 = time.perf_counter()
    for i, t in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {t.id} ...", flush=True)
        r = simulate_result(t, i) if simulate else run_task(t, agent_cmd, timeout)
        status = "PASS" if r.ok else ("MANUAL" if r.manual else "FAIL")
        print(f"    {status}  {r.detail}  ({r.round_trips} rt, {r.tokens} tok, {r.duration_s}s)",
              flush=True)
        results.append(r)
    elapsed = time.perf_counter() - t0
    passed = sum(r.ok for r in results if not r.manual)
    auto = sum(1 for r in results if not r.manual)
    print(f"\n=== {len(results)} tasks in {elapsed / 60:.1f} min "
          f"({elapsed / max(len(results), 1):.1f}s/task) | passed {passed}/{auto} ===")
    _save(results)
    return results


def _save(results: list[TaskResult]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps([r.to_dict() for r in results], indent=2))
    print(f"\nsaved {len(results)} results -> {path}")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated task ids to run (default: all)")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--simulate", action="store_true",
                    help="dry-run the harness with synthetic results (no agent, no screen)")
    args = ap.parse_args()
    tasks = TASKS
    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",")}
        tasks = [t for t in TASKS if t.id in wanted]
    run_suite(tasks, timeout=args.timeout, simulate=args.simulate)


if __name__ == "__main__":
    main()
