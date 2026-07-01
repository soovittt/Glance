"""Deep-dive a run's trajectories.

For each task (failures by default, `--all` for every task) show what the agent actually
did — its glance-cua tool sequence, any agent-level error, and the transcript tail — so
an overnight failure can be diagnosed without re-running anything. This is the raw
material for the RLVR loop: it turns "task X failed" into "here's exactly why".

Run:  python -m bench.suite.analyze            # latest run, failures only
      python -m bench.suite.analyze --all      # every task
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

TRAJ_DIR = Path(__file__).parent / "results" / "trajectories"


def latest_run() -> Path | None:
    runs = sorted(d for d in TRAJ_DIR.glob("*") if d.is_dir())
    return runs[-1] if runs else None


def analyze(run_dir: Path, failures_only: bool = True) -> str:
    meta_path = run_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    lines = [f"=== trajectories: {run_dir.name} ===",
             f"meta: {json.dumps(meta)}" if meta else "meta: (none)", ""]
    files = sorted(f for f in run_dir.glob("*.json") if f.name != "_meta.json")
    shown = 0
    for f in files:
        t = json.loads(f.read_text())
        r = t["result"]
        if failures_only and r["ok"]:
            continue
        shown += 1
        seq = [rec.get("tool") for rec in t.get("telemetry", [])]
        flag = "OK" if r["ok"] else "FAIL"
        err = f" ({r['error']})" if r.get("error") else ""
        lines += [
            f"### {t['id']} [{flag}{err}]  {r['duration_s']}s  {r['round_trips']}rt  {r['tokens']}tok",
            f"  verify : {r['detail']}",
            f"  tools  : {dict(Counter(seq))}  (total {len(seq)})",
            f"  agent  : {(t.get('stdout_tail') or '').strip()[-280:] or '(no output)'}",
            "",
        ]
    if not shown:
        lines.append("no matching tasks (all passed?) — try --all")
    return "\n".join(lines)


def main() -> None:
    run_dir = latest_run()
    if run_dir is None:
        raise SystemExit("no trajectories yet — run the suite first (not --simulate)")
    print(analyze(run_dir, failures_only="--all" not in sys.argv))


if __name__ == "__main__":
    main()
