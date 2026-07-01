# Glance self-improvement loop

A verifiable task suite + a **measure → compare → prioritize** loop, so Glance improves
from real runs instead of guesses. The reward is **efficiency gated by correctness** —
a change is only kept if the success rate holds.

## Pieces
- **`tasks.py`** — **150 natural-language tasks** across real, complex apps (Pages,
  Numbers, Keynote, Chrome/Safari, Maps, Preview, Freeform, Music, Weather, Stocks,
  code editors, Notes/Reminders/Calendar, System Settings…), each with a programmatic
  `verify()` (a Desktop file containing X, a Note titled Y, a Reminders list with N
  items). No bare Calculator tasks. `SMOKE` is a 5-task subset for a quick check.
- **`verifiers.py`** — reusable end-state checks (file / Notes / Reminders) + `manual()`.
- **`runner.py`** — per task: clean slate → reset telemetry → run the agent headless via
  `claude -p` (your registered glance-cua MCP) → `verify()` → record correctness + the
  per-task efficiency the server logged.
- **`report.py`** — scorecard (success rate + tokens/round-trips vs a naive loop +
  **total/per-task time** with the 3 slowest tasks) and a regression diff vs the
  previous run. Time is a first-class metric — the loop optimizes for fast *and* cheap.
- **`loop.py`** — ties it together and prints prioritized next actions.

## Run
```bash
pip install -e ".[mcp]"                  # glance-cua registered with Claude Code
python -m bench.suite.loop               # run the suite, then report + findings
python -m bench.suite.loop --no-run      # report on the latest saved run only
python -m bench.suite.runner --ids calc_mul,note_groceries   # a subset
```
Results are saved to `results/run_<ts>.json`.

## The cycle
```
run loop  →  make ONE change (fix a task / tune a threshold / strengthen a tool desc)
          →  run loop again  →  keep it only if compare shows no regression + better efficiency
```
That's the optimizer. It never rewrites code on its own — it points you (or a coding
agent) at the single most valuable change.

## Notes
- macOS, against your real desktop. Tasks are benign (throwaway Desktop files / Notes /
  Reminders); use a throwaway user or VM if you prefer.
- Requires the `claude` CLI on your PATH and glance-cua registered as an MCP server.
