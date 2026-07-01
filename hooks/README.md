# Glance hook — augment Claude Code's built-in computer use

This makes Claude Code's **own** computer use token-efficient without replacing it.
A `PostToolUse` hook runs after each MCP tool call; for a screenshot whose screen
didn't change, it returns `hookSpecificOutput.updatedToolOutput` — a short text note
that the model receives **instead of** the ~1,000-token image.

> Requires **Claude Code ≥ 2.1.121** (when `updatedToolOutput` became available for
> all tools). Check with `claude --version`.

## Install (pluggable — 3 steps)

1. Make sure the package is installed in the repo venv:
   ```bash
   cd /path/to/Glance && python3 -m venv .venv && source .venv/bin/activate
   pip install -e ".[mcp]"
   ```
2. Merge [`settings.snippet.json`](settings.snippet.json) into your
   `.claude/settings.json` (project) or `~/.claude/settings.json` (global), replacing
   the two absolute paths with your checkout.
3. **Start a NEW Claude Code session.** Hooks load at **startup** — you cannot add a
   hook to a running session (`/hooks` does not reload in non-interactive sessions).

That's it. Now every computer-use screenshot flows through Glance automatically. The
matcher `mcp__.*` covers the built-in `mcp__computer-use__*` tools; non-screenshot
calls pass straight through.

> Want it scoped to only the screenshot tool? Once you know your build's exact tool
> name (from the telemetry `tool` field), narrow the matcher, e.g.
> `"mcp__computer-use__.*"`.

## Telemetry — full visibility (this is the point)

Everything is recorded under `~/.glance/`:

| File | What |
|---|---|
| `telemetry.jsonl` | one JSON record per screenshot: `event` (send/skip), `reason`, `changed_fraction`, tokens, cumulative savings |
| `hook_debug.log` | human-readable trace |
| `hook_state.json` | persistent cumulative counters |

Analyze it any time:

```bash
python hooks/analyze.py
```

```
=== Glance telemetry ===
screenshots     : 42
  sent          : 27 (64%)
  skipped       : 15 (36%)
tokens saved    : 15330 of ~44100 baseline (35%)

reasons:
  changed            18
  first_frame         1
  below_threshold    12
  cursor_motion       3
  ...

changed_fraction distribution (the signal to tune skip_threshold):
  SKIP frames : min=0.00000 p50=0.00001 p90=0.00004 max=0.00009
  SEND frames : min=0.00012 p50=0.03100 p90=0.42000 max=1.00000

accuracy watch:
  borderline skips (fraction >=0.001)   : 0   <- review if any real change was hidden
  near-zero 'changed' sends (<0.0002)   : 2   <- candidates to also skip (more savings)
```

**How to use it to increase accuracy:** the `changed_fraction` distributions for
SKIP vs SEND should have a clean gap around `skip_threshold` (default `5e-5`). If SKIP
frequently reaches into the SEND band, tighten the threshold; if many SENDs sit at
near-zero fractions, you're leaving savings on the table. The `reason` breakdown shows
which rule (`below_threshold` / `caret` / `cursor_motion`) is doing the work.

## Reset counters
```bash
rm ~/.glance/telemetry.jsonl ~/.glance/hook_state.json ~/.glance/hook_prev_frame.png
```
