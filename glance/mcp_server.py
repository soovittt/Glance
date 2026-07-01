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
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from . import accessibility, display, keys, telemetry
from .cache import Step, TaskCache
from .diff import diff_frames, fingerprint, hamming, to_gray
from .metrics import estimate_image_tokens
from .observer import Observer
from .policy import GlancePolicy

_ENABLED = os.environ.get("GLANCE_DISABLED", "0") != "1"
TARGET_W = 1366   # served screenshot width; height derived from real aspect (_target_hw)

# Replay guards (out of 128 fingerprint bits). Lenient: catch GROSS drift (app didn't
# open, wrong window), tolerate clocks/cursor/anti-aliasing.
START_DIVERGE_BITS = 22   # current screen vs where the procedure was recorded
STEP_DIVERGE_BITS = 26    # each replayed step's result vs the recorded result
REPLAY_SETTLE = 0.35
# Action types that SHOULD visibly change the screen; near-zero change right after one
# of these in a batch means the action likely missed its target, so we stop early.
_STALL_ACTIONS = frozenset({"click", "type", "key", "drag"})

# Repo root (next to this package). Defaults for the task cache + log live here so
# they persist and are found regardless of where Claude Code launched the server.
_REPO = Path(__file__).resolve().parent.parent

mcp = FastMCP("glance-cua")
_observer = Observer(GlancePolicy(enabled=_ENABLED))
_cache = TaskCache(os.environ.get("GLANCE_TASK_FILE", str(_REPO / ".glance_tasks.json")))


def _setup_logging() -> tuple[logging.Logger, str]:
    """Log to a file (tailable) + stderr. NEVER stdout — that's the MCP channel."""
    lg = logging.getLogger("glance-cua")
    lg.setLevel(logging.INFO)
    lg.propagate = False
    # Default: a file inside the Glance repo, so it's always in the project and easy
    # to read later — regardless of where Claude Code launched the server from.
    # Override with GLANCE_LOG. Appends across runs.
    path = os.environ.get("GLANCE_LOG", str(_REPO / "glance.log"))
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
log.info("=== glance-cua start | glance=%s target_w=%d | %d cached task(s) | log=%s",
         "on" if _ENABLED else "OFF", TARGET_W, len(_cache), LOG_PATH)

# Recording state (set between task_begin on a new task and task_end).
_recording_label: str | None = None
_recorded: list[Step] = []
_start_fp: int | None = None

# pyautogui is imported lazily — it touches the display on import, which at
# module-load time would crash the server before it can register its tools.
_pg = None
_screen: tuple[int, int] | None = None
_active: display.Display | None = None   # the display we're currently serving/acting on


def _pyautogui():
    global _pg, _screen
    if _pg is None:
        import pyautogui as pg

        pg.FAILSAFE = False
        _pg = pg
        _screen = pg.size()
    return _pg


def _front_window_point() -> tuple[int, int] | None:
    """A global point just inside the frontmost app's window — used to pick its display."""
    if sys.platform != "darwin":
        return None
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to tell (first process whose frontmost is true) '
             'to get position of front window'],
            capture_output=True, timeout=4, text=True)
        parts = [p.strip() for p in (r.stdout or "").split(",")]
        if len(parts) == 2:
            return int(parts[0]) + 5, int(parts[1]) + 5
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass
    return None


def _active_display() -> display.Display:
    """The display the frontmost app is on; falls back to primary / pyautogui size."""
    ds = display.displays()
    if not ds:
        _pyautogui()
        sw, sh = _screen  # type: ignore[misc]
        return display.Display(0, 0, sw, sh)
    pt = _front_window_point()
    if pt:
        d = display.containing(ds, pt[0], pt[1])
        if d is not None:
            return d
    return display.main_display(ds) or ds[0]


def _ensure_active() -> display.Display:
    global _active
    if _active is None:
        _active = _active_display()
    return _active


def _target_hw() -> tuple[int, int]:
    """(width, height) for served screenshots — preserves the active display's aspect
    ratio so the image isn't distorted (which would throw off click grounding)."""
    return _ensure_active().target_size(TARGET_W)


def _to_screen(x: int, y: int) -> tuple[int, int]:
    """Map a served-screenshot point to global screen coords (correct across displays)."""
    return _ensure_active().to_global(x, y, TARGET_W)


def _grab_png() -> bytes:
    """Capture the display the active app is on, served at the target size."""
    global _active
    _active = _active_display()          # refresh — the app may have moved displays
    raw = display.capture(_active)
    if raw is None:                      # Quartz unavailable -> primary display via pyautogui
        buf = io.BytesIO()
        _pyautogui().screenshot().save(buf, format="PNG")
        raw = buf.getvalue()
    import cv2
    import numpy as np

    arr = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    _ok, out = cv2.imencode(".png", cv2.resize(arr, _active.target_size(TARGET_W)))
    return out.tobytes()


def _try_grab_fp() -> int | None:
    """Fingerprint the current screen, or None if capture fails (never raises)."""
    try:
        return fingerprint(_grab_png())
    except Exception as e:  # noqa: BLE001 - capture can fail (permissions, transient)
        log.warning("screen capture for fingerprint failed: %s", e)
        return None


def _frontmost_app() -> str:
    """Name of the frontmost (focused) app, via System Events. Never raises."""
    if sys.platform != "darwin":
        return "unknown (not macOS)"
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first '
             'application process whose frontmost is true'],
            capture_output=True, timeout=4, text=True)
        return (r.stdout or "").strip() or "unknown"
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"unknown ({e})"


# --- accessibility tree: structured, screenshot-free observation ------------

def _ui_elements() -> list[dict]:
    """Frontmost app's accessibility elements, mapped into the active display's space."""
    return accessibility.elements(_ensure_active(), TARGET_W)


def _anchor_for_click(x: int, y: int, els: list[dict] | None = None) -> dict | None:
    """Anchor a click to the element under it (reuse `els` to avoid a second a11y read)."""
    return accessibility.anchor_for_click(_ui_elements() if els is None else els, x, y)


def _resolve_anchor(anchor: dict) -> tuple[int, int] | None:
    """Live global coordinates of a recorded anchored element, or None if it's gone."""
    return accessibility.resolve_anchor(_ui_elements(), anchor)


# --- one dispatcher used by both the live tools and replay ------------------

def _clamp_wait(seconds) -> float:
    """Clamp a wait to a sane [0, 10] s range; default 1s on bad input."""
    try:
        return max(0.0, min(float(seconds), 10.0))
    except (TypeError, ValueError):
        return 1.0


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
        keys.press_key(_pyautogui(), action["keys"])
    elif a == "scroll":
        pg = _pyautogui()
        pg.moveTo(*_to_screen(action["x"], action["y"]))
        amt = int(action.get("amount", 3))
        pg.scroll(-amt * 100 if action.get("direction", "down") == "down" else amt * 100)
    elif a == "open_app":
        subprocess.run(["open", "-a", action["name"]], check=False,
                       capture_output=True, timeout=10)
    elif a == "wait":
        time.sleep(_clamp_wait(action.get("seconds", 1.0)))
    elif a == "drag":
        pg = _pyautogui()
        pg.moveTo(*_to_screen(action["x1"], action["y1"]))
        pg.dragTo(*_to_screen(action["x2"], action["y2"]), button=action.get("button", "left"))


def _act(action: dict) -> None:
    """Run a model-issued action; if a task is recording, append it to the procedure."""
    rec = _recording_label is not None
    # Resolve the click's anchor against the PRE-click UI — the click may change it.
    anchor = (_anchor_for_click(action["x"], action["y"])
              if rec and action.get("action") == "click" else None)
    _do(action)
    if rec:
        # fp=0 if capture fails: keeps the action in the sequence and makes replay
        # safely diverge at this step rather than crashing the recording.
        _recorded.append(Step(action=action, fingerprint=_try_grab_fp() or 0, anchor=anchor))
    log.info("action %s%s", action, f"  [recording '{_recording_label}' step {len(_recorded)}]" if rec else "")


def _safe_act(action: dict, ok_msg: str) -> str:
    """Run an action at a tool boundary: on failure return a clear message instead of
    crashing the tool, so the agent can recover. Broad except is deliberate here —
    GUI control can raise many low-level errors and resilience beats propagation."""
    try:
        _act(action)
        return ok_msg
    except Exception as e:  # noqa: BLE001 - intentional control boundary
        log.warning("action %s FAILED: %s", action, e)
        return f"action failed ({action.get('action')}): {e}"


# --- live computer-use tools ------------------------------------------------

@mcp.tool()
def computer_screenshot(force: bool = False):
    """Capture the screen. Returns the image, OR a short 'no change' note if it's
    identical to what you last saw (saves tokens; also reliable signal that your last
    action had no visible effect). Pass force=True to always get the pixels."""
    try:
        png = _grab_png()
    except Exception as e:  # noqa: BLE001 - capture can fail (permissions, transient)
        log.warning("screenshot FAILED: %s", e)
        return (f"[glance] screenshot failed: {e}. Check that the app running this "
                f"server has macOS Screen Recording permission, then try again.")
    obs = _observer.observe(png, force=force)
    s = _observer.stats
    log.info("screenshot %-4s changed=%5.2f%% img=%4dtok | session: %d/%d skipped, "
             "saved %d tok (%.0f%%)",
             "SKIP" if obs.skipped else "SEND", obs.changed_fraction * 100, obs.image_tokens,
             s.frames_skipped, s.frames_total, s.tokens_saved, s.pct_saved)
    telemetry.emit(tool="computer_screenshot", modality="image",
                   event="skip" if obs.skipped else "send",
                   est_tokens=obs.image_tokens, changed_fraction=round(obs.changed_fraction, 6))
    if obs.skipped:
        return ("[glance] No visual change since the last screenshot you saw. The "
                "screen is identical — if your last action was meant to change "
                "something, it had no visible effect; try a different approach.")
    return Image(data=png, format="png")


@mcp.tool()
def open_app(name: str) -> str:
    """Launch a macOS app by name (e.g. 'Calculator', 'Safari', 'TextEdit'). PREFER
    THIS to open apps — it runs `open -a` directly, which is far more reliable than
    driving Spotlight by keyboard or clicking its icon."""
    action = {"action": "open_app", "name": name}
    try:
        subprocess.run(["open", "-a", name], check=True, capture_output=True, timeout=10)
        ok, msg = True, f"launched {name}"
    except subprocess.CalledProcessError as e:
        ok, msg = False, f"could not launch '{name}': {e.stderr.decode()[:160].strip()}"
    except (subprocess.TimeoutExpired, OSError) as e:
        ok, msg = False, f"could not launch '{name}': {e}"
    if ok and _recording_label is not None:
        _recorded.append(Step(action=action, fingerprint=_try_grab_fp() or 0))
    log.info("open_app '%s' -> %s", name, "ok" if ok else msg)
    return msg


@mcp.tool()
def focus_app(name: str) -> str:
    """Bring an app to the front / raise its window above others. Use when an app is
    open but hidden behind another window (or on a second display) before you click or
    screenshot it — this is what stops the 'my keystrokes went to the wrong app' mess.
    Screenshots automatically follow whichever display the front app is on."""
    if sys.platform != "darwin":
        return "focus_app is macOS-only"
    safe = name.replace("\\", "\\\\").replace('"', '\\"')
    try:
        subprocess.run(["osascript", "-e", f'tell application "{safe}" to activate'],
                       check=True, capture_output=True, timeout=5)
        log.info("focus_app '%s'", name)
        return f"activated {name} (now frontmost)"
    except subprocess.CalledProcessError as e:
        return f"could not focus '{name}': {e.stderr.decode()[:150].strip()}"
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"could not focus '{name}': {e}"


@mcp.tool()
def frontmost_app() -> str:
    """Return the name of the frontmost (focused) app. Use it to CONFIRM an app
    actually launched and came to the front (e.g. right after open_app), instead of
    guessing from screenshots."""
    name = _frontmost_app()
    log.info("frontmost_app -> %s", name)
    return name


@mcp.tool()
def wait(seconds: float = 1.0) -> str:
    """Wait for the UI to settle — e.g. after launching an app or triggering a load.
    Capped at 10s. Use this instead of repeatedly screenshotting to 'check again'."""
    s = _clamp_wait(seconds)
    return _safe_act({"action": "wait", "seconds": s}, f"waited {s:.1f}s")


@mcp.tool()
def computer_click(x: int, y: int, button: str = "left", double: bool = False) -> str:
    """Click at (x, y) in the served screenshot's coordinate space (1366 px wide)."""
    return _safe_act({"action": "click", "x": x, "y": y, "button": button, "double": double},
                     f"clicked {button} at ({x},{y})")


@mcp.tool()
def computer_move(x: int, y: int) -> str:
    """Move the mouse to (x, y) in the screenshot coordinate space."""
    return _safe_act({"action": "move", "x": x, "y": y}, f"moved to ({x},{y})")


@mcp.tool()
def computer_type(text: str) -> str:
    """Type text at the current focus."""
    return _safe_act({"action": "type", "text": text}, f"typed {len(text)} chars")


@mcp.tool()
def computer_key(keys: str) -> str:
    """Press a key or combo, e.g. 'enter', 'cmd+space', 'cmd+c', 'ctrl+shift+t'."""
    return _safe_act({"action": "key", "keys": keys}, f"pressed {keys}")


@mcp.tool()
def computer_scroll(x: int, y: int, direction: str = "down", amount: int = 3) -> str:
    """Scroll at (x, y). direction is 'up' or 'down'; amount is in notches."""
    return _safe_act({"action": "scroll", "x": x, "y": y, "direction": direction, "amount": amount},
                     f"scrolled {direction} {amount}")


@mcp.tool()
def computer_drag(x1: int, y1: int, x2: int, y2: int, button: str = "left") -> str:
    """Drag from (x1, y1) to (x2, y2) in the screenshot coordinate space — e.g. to
    move a window, select text, or move a slider."""
    return _safe_act({"action": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "button": button},
                     f"dragged ({x1},{y1})->({x2},{y2})")


# --- efficiency tools: structured observation + batched actions -------------

@mcp.tool()
def ui_tree(limit: int = 60) -> str:
    """List the frontmost app's interactive UI elements (role, name, coordinates) as
    compact TEXT — far cheaper than a screenshot and precise for clicking. PREFER this
    over computer_screenshot to decide what to click; take a screenshot only when the
    tree is empty or the content is visual (canvas, image, video). Coordinates are in
    the screenshot space — pass them to computer_click, or use click_element(name)."""
    els = _ui_elements()
    if not els:
        return ("no accessibility elements available (grant Accessibility permission, or "
                "this app exposes none) — fall back to computer_screenshot.")
    lines = [f'[{e["role"]} "{e["name"]}"] @({e["tx"]},{e["ty"]})' for e in els[:limit]]
    extra = f"\n... (+{len(els) - limit} more; raise limit)" if len(els) > limit else ""
    text = f"{len(els)} UI elements in the frontmost app:\n" + "\n".join(lines) + extra
    log.info("ui_tree -> %d elements", len(els))
    telemetry.emit(tool="ui_tree", modality="text", n_elements=len(els),
                   est_tokens=max(1, len(text) // 4))
    return text


def _click_element(name: str) -> dict | None:
    """Locate and click a named element; return the matched element (or None)."""
    match = next((e for e in _ui_elements() if name.lower() in e["name"].lower()), None)
    if match is not None:
        _pyautogui().click(match["sx"], match["sy"])
        if _recording_label is not None:
            # This click came FROM the tree, so we know the element exactly — anchor it.
            _recorded.append(Step(action={"action": "click", "x": match["tx"], "y": match["ty"]},
                                  fingerprint=_try_grab_fp() or 0,
                                  anchor={"role": match["role"], "name": match["name"]}))
    return match


@mcp.tool()
def click_element(name: str) -> str:
    """Click the first UI element whose name matches `name` (case-insensitive) via the
    accessibility tree — no pixel hunting, no screenshot needed. Reliable where clicks
    by coordinate miss. Call ui_tree first to see the names."""
    match = _click_element(name)
    telemetry.emit(tool="click_element", modality="action", matched=match is not None,
                   est_tokens=8, avoided_screenshot=True)
    if match is None:
        return f"no UI element matching '{name}'. Call ui_tree to see available elements."
    log.info("click_element %r -> %r @(%d,%d)", name, match["name"], match["tx"], match["ty"])
    return f"clicked '{match['name']}' ({match['role']}) at ({match['tx']},{match['ty']})"


@mcp.tool()
def type_into(name: str, text: str) -> str:
    """Focus the element named `name` (via the accessibility tree) and type `text`
    into it — one call instead of screenshot -> locate -> click -> type."""
    match = _click_element(name)
    telemetry.emit(tool="type_into", modality="action", matched=match is not None,
                   est_tokens=8, avoided_screenshot=True)
    if match is None:
        return f"no UI element matching '{name}'. Call ui_tree to see available elements."
    time.sleep(0.15)
    _pyautogui().write(text, interval=0.01)
    return f"typed {len(text)} chars into '{name}'"


@mcp.tool()
def computer_batch(actions: list[dict[str, Any]], verify: bool = True,
                   stop_on_stall: bool = True):
    """Run a SEQUENCE of actions in ONE call — no model round-trip between them — and
    return a single screenshot at the end. This is the big speed/token win: instead of
    one screenshot per action, plan the steps and run them together.

    Each action is an object, e.g.:
      {"action":"click","x":303,"y":531}   {"action":"type","text":"hello"}
      {"action":"key","keys":"cmd+space"}  {"action":"open_app","name":"Calculator"}
      {"action":"scroll","x":700,"y":400,"direction":"down","amount":3}
      {"action":"wait","seconds":1}        {"action":"drag","x1":..,"y1":..,"x2":..,"y2":..}

    With verify=True (default) it reports how much the screen changed after each step.
    With stop_on_stall=True (default) it stops early if a click/type/key had NO visible
    effect (likely a missed target), returning the current screen so you can recover
    instead of blindly continuing a broken sequence."""
    if not isinstance(actions, list) or not actions:
        return "computer_batch needs a non-empty list of action objects"
    steps: list[str] = []
    t0 = time.perf_counter()
    prev = _grab_png()
    for i, a in enumerate(actions, 1):
        # Anchor a recorded click against the PRE-click UI (see _act for why).
        anchor = (_anchor_for_click(a["x"], a["y"])
                  if _recording_label is not None and a.get("action") == "click" else None)
        try:
            _do(a)
        except Exception as e:  # noqa: BLE001 - report and stop, don't crash the tool
            steps.append(f"{i}. {a.get('action')}: FAILED ({e}) — stopped here")
            break
        time.sleep(REPLAY_SETTLE)
        cur = _grab_png()
        if _recording_label is not None:
            _recorded.append(Step(action=a, fingerprint=fingerprint(cur), anchor=anchor))
        stalled = False
        if verify:
            frac = diff_frames(to_gray(prev), to_gray(cur)).changed_fraction
            stalled = (stop_on_stall and a.get("action") in _STALL_ACTIONS
                       and frac < _observer.policy.skip_threshold)
            steps.append(f"{i}. {a.get('action')}: screen changed {frac * 100:.1f}%"
                         + ("  ⚠ no visible effect (likely missed) — stopped early" if stalled else ""))
        else:
            steps.append(f"{i}. {a.get('action')}: done")
        prev = cur
        if stalled:
            break
    dt = time.perf_counter() - t0
    log.info("computer_batch: %d/%d actions in %.1fs", len(steps), len(actions), dt)
    telemetry.emit(tool="computer_batch", modality="batch", n_actions=len(actions),
                   n_ran=len(steps), round_trips_saved=max(0, len(steps) - 1),
                   est_tokens=estimate_image_tokens(*_target_hw()), duration_ms=round(dt * 1000))
    summary = (f"batch: ran {len(steps)}/{len(actions)} action(s) in {dt:.1f}s in one turn.\n"
               + "\n".join(steps) + "\nFinal screen:")
    return [summary, Image(data=prev, format="png")]


# --- procedure cache: record once, replay instantly -------------------------

def _do_step(step: Step) -> str:
    """Execute a recorded step during replay. For an anchored click, re-find the
    element live and click its CURRENT position (robust to the window having moved
    since recording); fall back to the recorded coordinate if the element can't be
    located. Returns the path taken ('anchor' | 'coord') for the log."""
    action = step.action
    if action.get("action") == "click" and step.anchor:
        pos = _resolve_anchor(step.anchor)
        if pos is not None:
            _pyautogui().click(*pos, button=action.get("button", "left"),
                               clicks=2 if action.get("double") else 1)
            return "anchor"
    _do(action)
    return "coord"


def _replay(proc):
    """Replay a recorded procedure locally, verifying each step. Returns content."""
    log.info("REPLAY '%s' (%d steps) — no model calls", proc.label, len(proc.steps))
    t0 = time.perf_counter()
    for i, step in enumerate(proc.steps, 1):
        via = _do_step(step)
        time.sleep(REPLAY_SETTLE)
        fp = _try_grab_fp()
        if fp is None:
            return (f"[task '{proc.label}'] aborted at step {i}: screen capture failed "
                    f"during replay. Check Screen Recording permission.")
        dist = hamming(fp, step.fingerprint)
        log.info("  replay step %d/%d %s via=%s verify=%dbits", i, len(proc.steps),
                 step.action, via, dist)
        if dist > STEP_DIVERGE_BITS:
            log.warning("REPLAY '%s' DIVERGED at step %d (%d bits) — aborting to model",
                        proc.label, i, dist)
            return (f"[task '{proc.label}'] DIVERGED at step {i}/{len(proc.steps)} "
                    f"(screen off by {dist} bits) — aborted to manual control. Take a "
                    f"screenshot to see the current state and finish the task yourself.")
    dt = time.perf_counter() - t0
    log.info("REPLAY '%s' done: %d steps in %.1fs, 0 model calls", proc.label, len(proc.steps), dt)
    summary = (f"[task '{proc.label}'] replayed {len(proc.steps)} actions in {dt:.1f}s with "
               f"zero model calls, all steps verified. The task is done.")
    try:
        return [summary + " Here is the final screen.", Image(data=_grab_png(), format="png")]
    except Exception:  # noqa: BLE001 - text-only result if the final capture fails
        return summary


@mcp.tool()
def task_begin(label: str):
    """Start a task. ALWAYS call this first with a short label describing the task
    (e.g. 'compute 7x8 in calculator').

    If this exact task was done before, the server REPLAYS it instantly with no
    further actions needed — you're done, just read the returned screen. Otherwise it
    starts recording: do the task normally with the computer_* tools, then call
    task_end to save it for next time."""
    global _recording_label, _recorded, _start_fp
    cur_fp = _try_grab_fp()
    if cur_fp is None:
        return ("[task] could not capture the screen to start the task — check macOS "
                "Screen Recording permission, then try again.")
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
def session_report() -> str:
    """Efficiency observability across ALL tools this session: screenshots vs ui_tree
    vs batches, estimated tokens by modality, model round-trips saved by batching, and
    overall % fewer tokens than a naive 1-screenshot-per-action loop. Call this to see
    what mix of tools is actually efficient."""
    return telemetry.summarize(telemetry.load())


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
    """Start a fresh measurement session: forget the screen baseline and clear session
    telemetry, so `session_report` reflects only what happens next. Cached tasks and the
    log file are preserved."""
    global _active
    _observer.reset()
    telemetry.reset()
    _active = None
    return "reset — fresh session (baseline + telemetry cleared; cached tasks kept)"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
