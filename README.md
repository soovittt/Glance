<p align="center">
  <img src="assets/logo.png" alt="Glance" width="440">
</p>

<p align="center">
  <b>Make Claude <i>glance</i>, not stare.</b> — a token-efficient computer-use layer for Claude Code.
</p>

---

Glance lets Claude Code control your Mac using **far fewer tokens and model
round-trips**, on your **Pro/Max subscription (no API key)**. The default computer-use
loop sends a fresh ~1,500-token screenshot on *every* step; Glance cuts that on three
fronts — skip screenshots that didn't change, read the UI as cheap **text** instead of
pixels, and **batch** whole action sequences into one round-trip.

> Measured on a 30-task run: **~61% fewer tokens** and **~59% fewer model round-trips**
> than a naive one-screenshot-per-action loop.

## Quick start (macOS, ~5 min)

Requirements: macOS · Python 3.10+ · Claude Code on a **Pro/Max** plan.

```bash
git clone https://github.com/soovittt/Glance.git glance && cd glance
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[mcp]"

# register the efficient computer-use server with Claude Code:
claude mcp add glance-cua -- "$(pwd)/.venv/bin/python" -m glance.mcp_server
```

The first computer-use call prompts for macOS **Accessibility + Screen Recording** —
approve both (Screen Recording may need a Claude Code restart).

> It controls your **actual** desktop, so heavy native apps work — but the agent can
> click anything. Use a throwaway macOS user or VM if you don't want it touching real
> files.

## Using it

Open a **new Claude Code session** and give it desktop tasks in plain English — no tool
names, no step-by-step. Glance drives your Mac and applies its efficiency automatically.

```
You: open Calculator and work out 48 × 12
     draft a 3-line note titled "Groceries" with milk, eggs, bread
     find the current time in Tokyo and save it to a text file on the Desktop
```

To see how efficient a run was, ask it to **call `session_report`** (or run
`python hooks/session_report.py`):

```
=== glance-cua session telemetry (128 tool calls) ===
model round-trips        : 128   (naive 1:1 loop would be ~316)
  saved by batching      : 188 round-trips  (60 batches, 248 actions)
observations             : 62 screenshots (0 skipped), 6 ui_tree
tokens                   : 199,418  vs naive ~510,656  ->  60.9% fewer
```

## How it works — three levers

- **Frame-skip.** An unchanged screenshot becomes a ~15-token note instead of a
  ~1,500-token image. The decision engine (`glance/decide.py`) is tuned to **100%
  accuracy / 0 missed changes** on a labeled set, with caret-blink and cursor-motion
  suppression so it never blinds the agent.
- **Structured observation.** `ui_tree` reads the frontmost app's UI as text (10–50×
  cheaper than a screenshot); `click_element` / `type_into` act on elements **by name**
  via the macOS accessibility API — no pixel hunting.
- **Batching + procedure cache.** `computer_batch` runs a whole action sequence in one
  model round-trip (the biggest lever on real workloads); `task_begin` / `task_end`
  record a task once and replay it instantly, re-finding moved elements via
  accessibility anchoring.

Everything is measured: `session_report` and `~/.glance/session_telemetry.jsonl` show
exactly where tokens and round-trips go, so you tune from data.

## Tools the server exposes

| Tool | What it does |
|---|---|
| `computer_screenshot` | capture the active display (skipped → text note when unchanged) |
| `computer_click` / `computer_move` / `computer_drag` | mouse: click, move, drag |
| `computer_type` / `computer_key` | keyboard: type text, press a combo (e.g. `cmd+space`) |
| `computer_scroll` | scroll at a point |
| `computer_batch` | run a **sequence of actions in one call** — collapses the 1-screenshot-1-action loop |
| `ui_tree` | the frontmost app's UI as **structured text** (role/name/coords) — cheap and precise |
| `click_element` / `type_into` | act on an element **by name** via the accessibility tree |
| `open_app` / `focus_app` | launch (`open -a`) or raise an app to the front |
| `wait` / `frontmost_app` | settle the UI; confirm which app is focused |
| `task_begin` / `task_end` / `task_list` / `task_forget` | record a task once; replay it instantly |
| `session_report` | cross-tool efficiency: tokens by modality, round-trips saved, % vs naive |
| `glance_stats` / `glance_log` / `glance_reset` | savings, log tail, reset baseline |

Coordinates live in a 1366-px-wide space that preserves the aspect ratio of **the
display the active app is on** — glance-cua captures whichever monitor the front app is
on (multi-display safe), so an app on a second screen is never invisible.

## Observability & logs

Everything is logged (never to stdout — that's the MCP channel):

- `~/.glance/session_telemetry.jsonl` — one record per tool call → `session_report`.
- `~/.glance/glance.log` — human-readable trace (`tail -f`, the `glance_log` tool, or stderr).

## Augment Claude's *built-in* computer use (hook mode)

Prefer not to swap in glance-cua's tools? A `PostToolUse` hook lets Glance ride on
Claude Code's **own** computer use — it replaces an unchanged screenshot's image with a
text note via `updatedToolOutput`, so Anthropic's computer use is untouched and just
gets cheaper. See [`hooks/README.md`](hooks/README.md). *(Requires Claude Code ≥ 2.1.121.)*

## Architecture

```
glance/
  mcp_server.py   the MCP server: tool definitions + wiring (thin transport layer)
  decide.py       frame-skip decision engine (+ diff.py, observer.py, policy.py, metrics.py)
  display.py      multi-display geometry + per-display capture (Quartz)
  keys.py         macOS keyboard (System Events + pyautogui fallback)
  accessibility.py  read the UI as elements + anchor clicks by identity
  cache.py        task-keyed procedure cache (record once, verified replay + anchoring)
  telemetry.py    cross-tool session telemetry + report
hooks/            PostToolUse hook mode (augment built-in computer use) + analyzers
bench/            benchmarks — labeled-accuracy eval, token harness, video-to-frames
examples/         Anthropic-SDK loop + headless-browser agent (the API path)
tests/            91 tests (pure geometry/decision logic; display-free)
```

Design notes: native calls (Quartz capture, AppleScript) are isolated and degrade to
safe fallbacks; every control action goes through an error boundary so a bad action
returns a message instead of crashing a tool; coordinate math and the decision engine
are pure and unit-tested.

## Development

```bash
pip install -e ".[mcp,dev]"
pytest          # 91 tests
ruff check .    # lint (also runs in CI on 3.10–3.12)

make eval       # score the frame-skip policy on the labeled dataset
make tune       # grid-search a better policy
python bench/harness.py                      # token savings on a synthetic trace
python bench/video_to_frames.py session.mov  # measure on a real screen recording
```

## Roadmap

- [x] Frame-skip engine (100% accuracy / 0 missed changes) + accuracy eval & auto-tuner
- [x] Structured observation (`ui_tree`) and semantic actions (`click_element`/`type_into`)
- [x] Action batching + task-keyed procedure cache with accessibility re-grounding
- [x] Multi-display capture + cross-tool telemetry (`session_report`)
- [ ] Push the agent to prefer `ui_tree`/`click_element` (more savings on dynamic tasks)
- [ ] Auto-tune `skip_threshold` from real telemetry
- [ ] Windows / Linux support

## License

[MIT](LICENSE)
