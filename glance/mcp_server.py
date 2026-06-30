"""Glance-CUA: a token-efficient, procedure-caching computer-use MCP server for Claude Code.

Runs on your Pro/Max subscription (no API key). Two levers:

  Layer 1 — Glance (cheaper): when the screen didn't change since Claude last looked,
    `computer_screenshot` returns a ~15-token note instead of a ~1,500-token image.

  Layer 2 — Procedure cache (faster): call `task_begin(label)` at the start of a task.
    The first time, the server records every action under that label; you call
    `task_end` when done. Every later time, `task_begin(label)` REPLAYS the whole
    recorded sequence locally with ZERO model round-trips — a 30s, 8-call task becomes
    ~2s — verifying each step against the recorded screen and aborting to the model if
    reality drifts. Keyed on the task label (no pixel-state collisions); persists
    across sessions.

Register with Claude Code:
    claude mcp add glance-cua -- /path/to/Glance/.venv/bin/python -m glance.mcp_server

Requires:  pip install -e ".[mcp]"   and macOS Accessibility + Screen Recording.
"""

from __future__ import annotations

import io
import logging
import os
import subprocess
import sys
import time

from mcp.server.fastmcp import FastMCP, Image

from .cache import Step, TaskCache
from .diff import fingerprint, hamming
from .observer import Observer
from .policy import GlancePolicy

_ENABLED = os.environ.get("GLANCE_DISABLED", "0") != "1"
TARGET_W, TARGET_H = 1366, 768

# Replay guards (out of 128 fingerprint bits). Lenient: catch GROSS drift (app didn't
# open, wrong window), tolerate clocks/cursor/anti-aliasing.
START_DIVERGE_BITS = 22   # current screen vs where the procedure was recorded
STEP_DIVERGE_BITS = 26    # each replayed step's result vs the recorded result
REPLAY_SETTLE = 0.35

mcp = FastMCP("glance-cua")
_observer = Observer(GlancePolicy(enabled=_ENABLED))
_cache = TaskCache(os.environ.get("GLANCE_TASK_FILE", ".glance_tasks.json"))


def _setup_logging() -> tuple[logging.Logger, str]:
    """Log to a file (tailable) + stderr. NEVER stdout — that's the MCP channel."""
    lg = logging.getLogger("glance-cua")
    lg.setLevel(logging.INFO)
    lg.propagate = False
    path = os.environ.get("GLANCE_LOG", os.path.expanduser("~/.glance/glance.log"))
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        fh = logging.FileHandler(path)
        fh.setFormatter(fmt)
        lg.addHandler(fh)
    except OSError:
        path = "(file logging unavailable)"
    sh = logging.StreamHandler(sys.stderr)   # stderr is safe for stdio MCP
    sh.setFormatter(logging.Formatter("[glance] %(message)s"))
    lg.addHandler(sh)
    return lg, path


log, LOG_PATH = _setup_logging()
log.info("=== glance-cua start | glance=%s target=%dx%d | %d cached task(s) | log=%s",
         "on" if _ENABLED else "OFF", TARGET_W, TARGET_H, len(_cache), LOG_PATH)

# Recording state (set between task_begin on a new task and task_end).
_recording_label: str | None = None
_recorded: list[Step] = []
_start_fp: int | None = None

# pyautogui is imported lazily — it touches the display on import, which at
# module-load time would crash the server before it can register its tools.
_pg = None
_screen: tuple[int, int] | None = None


def _pyautogui():
    global _pg, _screen
    if _pg is None:
        import pyautogui as pg

        pg.FAILSAFE = False
        _pg = pg
        _screen = pg.size()
    return _pg


def _to_screen(x: int, y: int) -> tuple[int, int]:
    _pyautogui()
    sw, sh = _screen  # type: ignore[misc]
    return round(x * sw / TARGET_W), round(y * sh / TARGET_H)


def _grab_png() -> bytes:
    shot = _pyautogui().screenshot().resize((TARGET_W, TARGET_H))
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    return buf.getvalue()


# --- keyboard ---------------------------------------------------------------

_KEYS = {  # pyautogui names (non-macOS fallback)
    "return": "enter", "escape": "esc", "backspace": "backspace", "delete": "delete",
    "cmd": "command", "super": "command", "ctrl": "ctrl", "control": "ctrl",
    "page_down": "pagedown", "page_up": "pageup", "space": "space",
}
_MAC_KEYCODES = {
    "space": 49, "enter": 36, "return": 36, "tab": 48, "escape": 53, "esc": 53,
    "delete": 51, "backspace": 51, "left": 123, "right": 124, "down": 125, "up": 126,
    "pagedown": 121, "page_down": 121, "pageup": 116, "page_up": 116,
    "home": 115, "end": 119,
}
_MAC_MODS = {
    "command": "command", "cmd": "command", "super": "command",
    "ctrl": "control", "control": "control", "shift": "shift",
    "option": "option", "alt": "option",
}


def _mac_key(keys: str) -> bool:
    """Send a key/combo via AppleScript System Events. Never blocks (short timeout +
    captured output); returns False on timeout/error so the caller can fall back."""
    *mods, key = [p.strip() for p in keys.split("+")]
    using = ""
    if mods:
        names = [_MAC_MODS.get(m.lower(), m.lower()) for m in mods]
        using = " using {" + ", ".join(f"{n} down" for n in names) + "}"
    kl = key.lower()
    if kl in _MAC_KEYCODES:
        action = f"key code {_MAC_KEYCODES[kl]}"
    else:
        safe = key.replace("\\", "\\\\").replace('"', '\\"')
        action = f'keystroke "{safe}"'
    script = f'tell application "System Events" to {action}{using}'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=4)
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False


def _press_key(keys: str) -> None:
    if sys.platform == "darwin" and _mac_key(keys):
        return
    pg = _pyautogui()
    parts = [_KEYS.get(p.lower(), p.lower()) for p in keys.split("+")]
    pg.hotkey(*parts) if len(parts) > 1 else pg.press(parts[0])


# --- one dispatcher used by both the live tools and replay ------------------

def _do(action: dict) -> None:
    """Execute a single normalized action dict on the machine."""
    a = action["action"]
    if a == "click":
        sx, sy = _to_screen(action["x"], action["y"])
        _pyautogui().click(sx, sy, button=action.get("button", "left"),
                           clicks=2 if action.get("double") else 1)
    elif a == "move":
        _pyautogui().moveTo(*_to_screen(action["x"], action["y"]))
    elif a == "type":
        _pyautogui().write(action["text"], interval=0.01)
    elif a == "key":
        _press_key(action["keys"])
    elif a == "scroll":
        pg = _pyautogui()
        pg.moveTo(*_to_screen(action["x"], action["y"]))
        amt = int(action.get("amount", 3))
        pg.scroll(-amt * 100 if action.get("direction", "down") == "down" else amt * 100)


def _act(action: dict) -> None:
    """Run a model-issued action; if a task is recording, append it to the procedure."""
    _do(action)
    rec = _recording_label is not None
    if rec:
        _recorded.append(Step(action=action, fingerprint=fingerprint(_grab_png())))
    log.info("action %s%s", action, f"  [recording '{_recording_label}' step {len(_recorded)}]" if rec else "")


# --- live computer-use tools ------------------------------------------------

@mcp.tool()
def computer_screenshot(force: bool = False):
    """Capture the screen. Returns the image, OR a short 'no change' note if it's
    identical to what you last saw (saves tokens; also reliable signal that your last
    action had no visible effect). Pass force=True to always get the pixels."""
    png = _grab_png()
    obs = _observer.observe(png, force=force)
    s = _observer.stats
    log.info("screenshot %-4s changed=%5.2f%% img=%4dtok | session: %d/%d skipped, "
             "saved %d tok (%.0f%%)",
             "SKIP" if obs.skipped else "SEND", obs.changed_fraction * 100, obs.image_tokens,
             s.frames_skipped, s.frames_total, s.tokens_saved, s.pct_saved)
    if obs.skipped:
        return ("[glance] No visual change since the last screenshot you saw. The "
                "screen is identical — if your last action was meant to change "
                "something, it had no visible effect; try a different approach.")
    return Image(data=png, format="png")


@mcp.tool()
def computer_click(x: int, y: int, button: str = "left", double: bool = False) -> str:
    """Click at (x, y) in the 1366x768 screenshot coordinate space."""
    _act({"action": "click", "x": x, "y": y, "button": button, "double": double})
    return f"clicked {button} at ({x},{y})"


@mcp.tool()
def computer_move(x: int, y: int) -> str:
    """Move the mouse to (x, y) in the screenshot coordinate space."""
    _act({"action": "move", "x": x, "y": y})
    return f"moved to ({x},{y})"


@mcp.tool()
def computer_type(text: str) -> str:
    """Type text at the current focus."""
    _act({"action": "type", "text": text})
    return f"typed {len(text)} chars"


@mcp.tool()
def computer_key(keys: str) -> str:
    """Press a key or combo, e.g. 'enter', 'cmd+space', 'cmd+c', 'ctrl+shift+t'."""
    _act({"action": "key", "keys": keys})
    return f"pressed {keys}"


@mcp.tool()
def computer_scroll(x: int, y: int, direction: str = "down", amount: int = 3) -> str:
    """Scroll at (x, y). direction is 'up' or 'down'; amount is in notches."""
    _act({"action": "scroll", "x": x, "y": y, "direction": direction, "amount": amount})
    return f"scrolled {direction} {amount}"


# --- procedure cache: record once, replay instantly -------------------------

def _replay(proc):
    """Replay a recorded procedure locally, verifying each step. Returns content."""
    log.info("REPLAY '%s' (%d steps) — no model calls", proc.label, len(proc.steps))
    t0 = time.perf_counter()
    for i, step in enumerate(proc.steps, 1):
        _do(step.action)
        time.sleep(REPLAY_SETTLE)
        dist = hamming(fingerprint(_grab_png()), step.fingerprint)
        log.info("  replay step %d/%d %s verify=%dbits", i, len(proc.steps),
                 step.action, dist)
        if dist > STEP_DIVERGE_BITS:
            log.warning("REPLAY '%s' DIVERGED at step %d (%d bits) — aborting to model",
                        proc.label, i, dist)
            return (f"[task '{proc.label}'] DIVERGED at step {i}/{len(proc.steps)} "
                    f"(screen off by {dist} bits) — aborted to manual control. Take a "
                    f"screenshot to see the current state and finish the task yourself.")
    dt = time.perf_counter() - t0
    log.info("REPLAY '%s' done: %d steps in %.1fs, 0 model calls", proc.label, len(proc.steps), dt)
    png = _grab_png()
    return [f"[task '{proc.label}'] replayed {len(proc.steps)} actions in {dt:.1f}s with "
            f"zero model calls, all steps verified. Here is the final screen — read the "
            f"result from it; the task is done.", Image(data=png, format="png")]


@mcp.tool()
def task_begin(label: str):
    """Start a task. ALWAYS call this first with a short label describing the task
    (e.g. 'compute 7x8 in calculator').

    If this exact task was done before, the server REPLAYS it instantly with no
    further actions needed — you're done, just read the returned screen. Otherwise it
    starts recording: do the task normally with the computer_* tools, then call
    task_end to save it for next time."""
    global _recording_label, _recorded, _start_fp
    cur_fp = fingerprint(_grab_png())
    proc = _cache.get(label)
    if proc is not None:
        start_dist = hamming(cur_fp, proc.start_fingerprint)
        if start_dist <= START_DIVERGE_BITS:
            log.info("task_begin '%s' -> REPLAY (start matches, %dbits)", label, start_dist)
            return _replay(proc)
        log.info("task_begin '%s' -> RE-RECORD (start drifted %dbits)", label, start_dist)
    else:
        log.info("task_begin '%s' -> RECORD (new task)", label)

    _recording_label = label
    _recorded = []
    _start_fp = cur_fp
    extra = " (the cached version started from a different screen)" if proc else ""
    return (f"[task] no usable recording for '{label}'{extra}. Recording now: do the "
            f"task with the computer_* tools, then call task_end to save it.")


@mcp.tool()
def task_end() -> str:
    """Stop recording the current task and save it for instant replay next time."""
    global _recording_label
    if _recording_label is None:
        return "not recording a task"
    label, n = _recording_label, len(_recorded)
    _cache.put(label, _start_fp if _start_fp is not None else 0, _recorded)
    _recording_label = None
    log.info("task_end: saved '%s' with %d steps", label, n)
    return f"saved task '{label}' with {n} steps — next time, task_begin replays it instantly"


@mcp.tool()
def task_list() -> str:
    """List saved tasks that can be replayed."""
    names = _cache.labels()
    return "saved tasks: " + (", ".join(f"'{n}'" for n in names) if names else "(none)")


@mcp.tool()
def task_forget(label: str) -> str:
    """Delete a saved task (e.g. if the UI changed and its replay no longer works)."""
    return f"forgot '{label}'" if _cache.forget(label) else f"no saved task '{label}'"


@mcp.tool()
def glance_stats() -> str:
    """Token savings (Glance), cached tasks, and where the log lives."""
    return f"{_observer.stats.summary()} | {len(_cache)} cached task(s) | log: {LOG_PATH}"


@mcp.tool()
def glance_log(lines: int = 40) -> str:
    """Read the last N lines of the glance-cua log (so you can track what it's doing)."""
    try:
        with open(LOG_PATH) as f:
            tail = f.readlines()[-lines:]
        return f"--- {LOG_PATH} (last {len(tail)} lines) ---\n" + "".join(tail)
    except OSError as e:
        return f"could not read log at {LOG_PATH}: {e}"


@mcp.tool()
def glance_reset() -> str:
    """Forget the current screen baseline (call when starting unrelated work). Token
    stats and cached tasks are PRESERVED."""
    _observer.reset()
    return "baseline reset (savings stats + cached tasks preserved)"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
