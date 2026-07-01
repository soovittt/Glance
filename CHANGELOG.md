# Changelog

All notable changes to Glance are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0.

## [Unreleased]

### Efficiency levers
- **Frame-skip** — an unchanged screenshot becomes a ~15-token note instead of a
  ~1,500-token image. Decision engine tuned to 100% accuracy / 0 missed changes on a
  labeled dataset, with caret-blink and cursor-motion suppression.
- **Structured observation** — `ui_tree` reads the frontmost app's UI as text via the
  macOS accessibility API; `click_element` / `type_into` act on elements by name.
- **Action batching** — `computer_batch` runs a whole action sequence in one model
  round-trip, with a per-step change log and safe fallback.
- **Procedure cache** — `task_begin` / `task_end` record a task once and replay it
  instantly, verified per step and re-grounded by accessibility anchoring.

### Platform
- MCP server for Claude Code — runs on a Pro/Max subscription, no API key.
- **Multi-display** capture (`glance/display.py`): captures the display the front app
  is on and maps clicks to global coordinates; `focus_app` raises an app to the front.
- Reliable primitives: `open_app` (via `open -a`), `wait`, `frontmost_app`,
  `computer_drag`, aspect-preserving coordinates.

### Observability
- Cross-tool session telemetry (`glance/telemetry.py`) + `session_report` tool and
  `hooks/session_report.py` — tokens by modality, round-trips saved by batching, and
  % vs a naive screenshot-per-action loop.
- File + stderr + `glance_log` logging of every screenshot decision and action.

### Hook mode
- `hooks/glance_hook.py`: a `PostToolUse` hook that makes Claude Code's **built-in**
  computer use token-efficient via `updatedToolOutput` (requires Claude Code ≥ 2.1.121),
  with its own telemetry and `hooks/analyze.py` report.

### Robustness
- `_safe_act` error boundary; screenshot / replay / recording failure guards;
  `TaskCache` survives a corrupt cache file; native calls degrade to safe fallbacks.

### Tooling
- GitHub Actions CI (pytest on 3.10–3.12 + ruff lint), ruff config, 91 tests.
- Benchmarks with no API key: labeled-accuracy `eval`, token `harness`, `video_to_frames`.
