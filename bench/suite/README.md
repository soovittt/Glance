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
  **total/per-task time** with the 3 slowest tasks + agent-error/timeout counts) and a
  regression diff vs the previous run. Time is a first-class metric.
- **`catalog.py`** — a **~1000-task corpus across 60 apps** (After Effects, Premiere,
  Media Encoder, CapCut, Screen Studio, iMovie, GarageBand, Photos, browsers, iWork,
  code editors, TablePlus/Postman/Docker/Xcode, and every native app), generated from
  compact per-app banks + parametric families. `python -m bench.suite.catalog --dump`
  writes `results/catalog.md` + `.json`. Run it with `--catalog`:
  `python -m bench.suite.loop --catalog`. Creative/app-internal results verify `manual`.
- **`analyze.py`** — deep-dive a run's **per-task trajectories**: for each failure, the
  glance-cua tool sequence, the agent-level error, and the agent's own transcript tail
  ("got stuck on the template chooser") — so you can see *why* it failed, not just that
  it did. `python -m bench.suite.analyze [--all]`.

## Observability captured per run
- `results/run_<ts>.json` — one `TaskResult` per task (correctness, tokens, round-trips,
  time, `error`).
- `results/trajectories/<ts>/<task>.json` — the **full trajectory**: prompt, verdict,
  every glance-cua telemetry record (all tool calls now emit — clicks/types included, so
  round-trips are exact), and the agent's stdout/stderr tail.
- `results/trajectories/<ts>/_meta.json` — run metadata (commit, host, timing, error mix).

The agent runs headless with a **system prompt** that steers it to drive the GUI via
glance-cua only (no shell/file shortcuts) — without it, a restricted headless agent
flounders and times out.
- **`loop.py`** — ties it together and prints prioritized next actions.

## Run
```bash
pip install -e ".[mcp]"                  # glance-cua registered with Claude Code
python -m bench.suite.loop --simulate    # dry-run the harness (no agent, no screen)
python -m bench.suite.loop               # LIVE run, then report + findings
python -m bench.suite.loop --no-run      # report on the latest saved run only
python -m bench.suite.runner --ids text_01,notes_01   # a subset
```
Results are saved to `results/run_<ts>.json`.

**Validate first, then go live.** `--simulate` exercises the whole pipeline (scoring,
time, regression diff, findings) with synthetic results so you can confirm it works
before committing your machine. A live run drives your real desktop via headless
`claude -p --permission-mode bypassPermissions` — approval gates are off so the agent
can act unattended, so **you must launch it yourself** in your own terminal (a nested
agent cannot disable its own permission gates). Budget ~2 hours for the full 150.

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
