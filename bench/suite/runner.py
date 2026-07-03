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
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from glance import telemetry

from .model import Task, TaskResult
from .tasks import TASKS

RESULTS_DIR = Path(__file__).parent / "results"


def _mcp_config_path() -> str:
    """Write an MCP config that loads glance-cua from THIS venv, so a headless agent has
    the tools regardless of which project scope glance-cua happens to be registered in."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    p = RESULTS_DIR / "_mcp.json"
    p.write_text(json.dumps({"mcpServers": {"glance-cua":
        {"command": sys.executable, "args": ["-m", "glance.mcp_server"]}}}))
    return str(p)


# Steers the headless agent to actually DRIVE THE GUI with glance-cua instead of
# floundering (trying the sandboxed shell, then stalling until timeout — the exact
# failure the 1-task validation caught).
SYSTEM_PROMPT = (
    "You are an automated macOS computer-use agent. Complete the task by driving the "
    "GUI with the glance-cua tools ONLY: open_app, focus_app, ui_tree, click_element, "
    "type_into, computer_batch, computer_click, computer_type, computer_key, "
    "computer_screenshot, computer_scroll, wait. Do NOT use the shell or write files "
    "directly to shortcut a GUI task — the point is to use the desktop. Be "
    "token-efficient: prefer ui_tree and computer_batch over one-screenshot-per-action. "
    "Do the task, confirm the result on screen, then stop — do not ask questions."
)


def default_agent() -> list[str]:
    """Headless agent command: load glance-cua, pre-approve ONLY its tools (an allowlist,
    not a blanket gate-disable), and steer it to drive the GUI. The task prompt is fed on
    stdin (that's how `claude -p` wants it alongside flags)."""
    return ["claude", "-p", "--mcp-config", _mcp_config_path(),
            "--allowedTools", "mcp__glance-cua", "--append-system-prompt", SYSTEM_PROMPT]


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


def _metrics(recs: list[dict]) -> dict:
    """Aggregate the raw telemetry records the server wrote for one task."""
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


def _save_trajectory(trace_dir: Path, task: Task, result: TaskResult,
                     recs: list[dict], stdout: str, stderr: str) -> None:
    """Persist the full per-task trajectory — the agent's tool sequence, transcript, and
    verdict — so an overnight failure can be diagnosed after the fact."""
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / f"{task.id}.json").write_text(json.dumps({
        "id": task.id, "difficulty": task.difficulty, "prompt": task.prompt,
        "result": result.to_dict(), "telemetry": recs,
        "stdout_tail": (stdout or "")[-4000:], "stderr_tail": (stderr or "")[-1000:],
    }, indent=2))


def run_task(task: Task, agent_cmd: list[str] | None = None, timeout: int = 300,
             trace_dir: Path | None = None) -> TaskResult:
    agent_cmd = agent_cmd or default_agent()
    if task.setup:
        try:
            task.setup()
        except Exception:  # noqa: BLE001 - setup is best-effort clean-up
            pass
    telemetry.reset()
    error, stdout, stderr = "", "", ""
    t0 = time.perf_counter()
    try:
        p = subprocess.run(agent_cmd, input=task.prompt, timeout=timeout,
                           capture_output=True, text=True)
        stdout, stderr = p.stdout, p.stderr
        if p.returncode != 0:
            error = f"exit {p.returncode}"
    except subprocess.TimeoutExpired as e:
        error, stdout = "timeout", (e.stdout if isinstance(e.stdout, str) else "") or ""
    except OSError as e:
        error = f"launch: {e}"
    dt = round(time.perf_counter() - t0, 1)
    recs = telemetry.load()                      # raw trajectory for THIS task
    res = task.verify()
    result = TaskResult(id=task.id, difficulty=task.difficulty, ok=res.ok, manual=res.manual,
                        detail=res.detail, duration_s=dt, error=error, **_metrics(recs))
    if trace_dir is not None:
        _save_trajectory(trace_dir, task, result, recs, stdout, stderr)
    return result


def run_suite(tasks: list[Task] = TASKS, agent_cmd: list[str] | None = None,
              timeout: int = 300, simulate: bool = False) -> list[TaskResult]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_dir = None if simulate else RESULTS_DIR / "trajectories" / stamp
    if not simulate:
        agent_cmd = agent_cmd or default_agent()
    results: list[TaskResult] = []
    t0 = time.perf_counter()
    for i, t in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {t.id} ...", flush=True)
        r = simulate_result(t, i) if simulate else run_task(t, agent_cmd, timeout, trace_dir)
        status = "PASS" if r.ok else ("MANUAL" if r.manual else "FAIL")
        tag = f" [{r.error}]" if r.error else ""
        print(f"    {status}{tag}  {r.detail}  ({r.round_trips} rt, {r.tokens} tok, {r.duration_s}s)",
              flush=True)
        results.append(r)
    elapsed = time.perf_counter() - t0
    passed = sum(r.ok for r in results if not r.manual)
    auto = sum(1 for r in results if not r.manual)
    print(f"\n=== {len(results)} tasks in {elapsed / 60:.1f} min "
          f"({elapsed / max(len(results), 1):.1f}s/task) | passed {passed}/{auto} ===")
    _save(results, stamp)
    if trace_dir is not None:
        _save_meta(trace_dir, results, elapsed)
    return results


def _save(results: list[TaskResult], stamp: str | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"run_{stamp}.json"
    path.write_text(json.dumps([r.to_dict() for r in results], indent=2))
    print(f"\nsaved {len(results)} results -> {path}")
    return path


def _save_meta(trace_dir: Path, results: list[TaskResult], elapsed: float) -> None:
    """Run-level metadata for reproducibility (commit, host, timing, error breakdown)."""
    import platform
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = "?"
    errs = {e: sum(1 for r in results if r.error == e) for e in {r.error for r in results if r.error}}
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "_meta.json").write_text(json.dumps({
        "tasks": len(results),
        "passed": sum(r.ok for r in results if not r.manual),
        "errors": errs,
        "elapsed_min": round(elapsed / 60, 1),
        "commit": commit, "host": platform.node(),
    }, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated task ids to run (default: all)")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--simulate", action="store_true",
                    help="dry-run the harness with synthetic results (no agent, no screen)")
    ap.add_argument("--catalog", action="store_true",
                    help="run the ~1000-task catalog (all apps) instead of the 150-task suite")
    args = ap.parse_args()
    if args.catalog:
        from .catalog import build
        tasks = build()
    else:
        tasks = TASKS
    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",")}
        tasks = [t for t in TASKS if t.id in wanted]
    run_suite(tasks, timeout=args.timeout, simulate=args.simulate)


if __name__ == "__main__":
    main()
