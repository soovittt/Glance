# Changelog

All notable changes to Glance are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0.

## [Unreleased]

### Added
- **Glance (Layer 1)** — skip sending screenshots that didn't change; decision
  engine tuned via a self-improving eval loop to 100% accuracy / 0 missed changes
  on a labeled dataset, with caret-blink and cursor-motion suppression.
- **Procedure cache (Layer 2)** — `task_begin` / `task_end` record a task once and
  replay it on exact repeat with zero per-action model round-trips, verified
  per-step by a 128-bit perceptual fingerprint.
- **MCP server for Claude Code** — runs on a Pro/Max subscription (no API key).
- **Reliable primitives** — `open_app` (launch via `open -a`), `wait`,
  `frontmost_app`, `computer_drag`, plus click/move/type/key/scroll.
- **Logging** — file (`<repo>/glance.log`) + stderr + `glance_log` tool, with
  per-screenshot SEND/SKIP decisions and a running token-savings total.
- **Benchmarks** — reproducible token-savings and labeled-accuracy harnesses that
  need no API key; an Anthropic SDK example and a browser-agent example.
- **GitHub Actions CI** — pytest on Python 3.10–3.12.

### Robustness
- Aspect-ratio-preserving screenshot coordinates (fixes distorted click mapping).
- `_safe_act` error boundary: a failed control action returns a message instead of
  crashing the tool.
- `TaskCache` survives a corrupt/unreadable cache file (starts empty; skips
  malformed entries).
- `computer_screenshot` returns an actionable message if a capture fails.

### Notes
- Found and documented why fully-automatic *pixel-state* action caching can't work
  as a bolt-on (whole-screen fingerprints collide on fine UI states); the reliable
  approach is task-keyed procedure replay.
