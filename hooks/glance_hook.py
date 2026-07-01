#!/usr/bin/env python3
"""Glance PostToolUse hook — make Claude Code's BUILT-IN computer use token-efficient.

Runs after every MCP tool call (matcher `mcp__.*`). For a screenshot result it
compares the frame to the last one Glance let through; if the screen didn't change
it returns `hookSpecificOutput.updatedToolOutput` = a short text note, and the model
receives THAT string instead of the ~1,000-token image. Anthropic's computer use is
untouched — Glance rides on its output. (Requires Claude Code >= 2.1.121.)

Invoke with the venv python so `glance` + cv2 import:
  "command": "/…/Glance/.venv/bin/python /…/Glance/hooks/glance_hook.py"

TELEMETRY (this is the point — full visibility to tune accuracy):
  ~/.glance/telemetry.jsonl   one JSON record per screenshot: decision, reason,
                              changed_fraction, tokens, cumulative savings.
  ~/.glance/hook_debug.log    human-readable trace.
  ~/.glance/hook_state.json   persistent cumulative counters.
  Analyze anytime:  python hooks/analyze.py

Never raises: on any error it prints "{}" (passthrough) so it can't break a tool.
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime
from pathlib import Path

GLANCE_DIR = Path.home() / ".glance"
DEBUG_LOG = GLANCE_DIR / "hook_debug.log"
TELEMETRY = GLANCE_DIR / "telemetry.jsonl"
STATE = GLANCE_DIR / "hook_state.json"
PREV = GLANCE_DIR / "hook_prev_frame.png"

SKIP_NOTE = ("[glance] No visual change since the previous screenshot; the screen is "
             "identical to your last view. Continue from that state.")
NOTE_TOKENS = 15


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _debug(msg: str) -> None:
    try:
        GLANCE_DIR.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG.open("a") as f:
            f.write(f"{_now()} {msg}\n")
    except OSError:
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"frames": 0, "skips": 0, "tokens_sent": 0, "tokens_baseline": 0}


def _save_state(state: dict) -> None:
    try:
        GLANCE_DIR.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state))
    except OSError:
        pass


def _emit_telemetry(record: dict) -> None:
    try:
        GLANCE_DIR.mkdir(parents=True, exist_ok=True)
        with TELEMETRY.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _find_image_b64(o):
    """Recursively locate base64 image data in a tool_response (MCP content blocks)."""
    if isinstance(o, dict):
        if o.get("type") == "image":
            src = o.get("source")
            if isinstance(src, dict) and src.get("data"):
                return src["data"]
            if isinstance(o.get("data"), str):
                return o["data"]
        for v in o.values():
            r = _find_image_b64(v)
            if r:
                return r
    elif isinstance(o, list):
        for x in o:
            r = _find_image_b64(x)
            if r:
                return r
    return None


def _passthrough() -> None:
    print("{}")


def _skip() -> None:
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": SKIP_NOTE}
    }))


def _record(state, *, tool, event, reason, changed_fraction, est_tokens, img_bytes,
            width, height, elapsed_ms):
    """Update cumulative state and write one telemetry record; return the record."""
    tokens_this = NOTE_TOKENS if event == "skip" else est_tokens
    state["frames"] += 1
    state["tokens_baseline"] += est_tokens
    state["tokens_sent"] += tokens_this
    if event == "skip":
        state["skips"] += 1
    saved = state["tokens_baseline"] - state["tokens_sent"]
    pct = round(100.0 * saved / state["tokens_baseline"], 1) if state["tokens_baseline"] else 0.0
    rec = {
        "ts": _now(), "tool": tool, "event": event, "reason": reason,
        "changed_fraction": None if changed_fraction is None else round(changed_fraction, 6),
        "width": width, "height": height, "img_bytes": img_bytes, "est_tokens": est_tokens,
        "tokens_saved_this": est_tokens - tokens_this, "decide_ms": elapsed_ms,
        "cum_frames": state["frames"], "cum_skips": state["skips"],
        "cum_skip_rate": round(100.0 * state["skips"] / state["frames"], 1),
        "cum_tokens_saved": saved, "cum_pct_saved": pct,
    }
    _save_state(state)
    _emit_telemetry(rec)
    _debug(f"{event.upper():4} {tool} reason={reason} "
           f"changed={rec['changed_fraction']} saved_this={rec['tokens_saved_this']}tok "
           f"| cum: {state['skips']}/{state['frames']} skipped, {saved}tok ({pct}%)")
    return rec


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return _passthrough()

    tool = str(data.get("tool_name", ""))
    img_b64 = _find_image_b64(data.get("tool_response"))
    if not img_b64:
        return _passthrough()  # not a screenshot — leave it alone (no telemetry noise)

    try:
        import time as _time

        import cv2
        import numpy as np

        from glance.decide import explain
        from glance.diff import to_gray
        from glance.metrics import estimate_image_tokens
        from glance.policy import GlancePolicy

        png = base64.b64decode(img_b64)
        arr = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
        h, w = (arr.shape[0], arr.shape[1]) if arr is not None else (0, 0)
        est_tokens = estimate_image_tokens(w, h)
        state = _load_state()

        if not PREV.exists():
            PREV.write_bytes(png)
            _record(state, tool=tool, event="send", reason="first_frame",
                    changed_fraction=None, est_tokens=est_tokens, img_bytes=len(png),
                    width=w, height=h, elapsed_ms=0)
            return _passthrough()

        t0 = _time.perf_counter()
        dec = explain(to_gray(PREV.read_bytes()), to_gray(arr), GlancePolicy())
        elapsed_ms = round((_time.perf_counter() - t0) * 1000, 1)

        if dec.changed:
            PREV.write_bytes(png)  # update the last frame we let the model see
            _record(state, tool=tool, event="send", reason=dec.reason,
                    changed_fraction=dec.changed_fraction, est_tokens=est_tokens,
                    img_bytes=len(png), width=w, height=h, elapsed_ms=elapsed_ms)
            return _passthrough()

        _record(state, tool=tool, event="skip", reason=dec.reason,
                changed_fraction=dec.changed_fraction, est_tokens=est_tokens,
                img_bytes=len(png), width=w, height=h, elapsed_ms=elapsed_ms)
        return _skip()
    except Exception as e:  # noqa: BLE001 - a hook must never break the tool
        _debug(f"ERROR passing through: {e}")
        return _passthrough()


if __name__ == "__main__":
    main()
