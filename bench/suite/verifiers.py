"""End-state checks for suite tasks.

File checks are pure and unit-testable; app-state checks (Notes, Reminders) use
osascript on macOS. Each returns a `VerifyResult`; use `manual(...)` for tasks that
genuinely can't be auto-checked so the scorer excludes them from the success rate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .model import VerifyResult

DESKTOP = Path.home() / "Desktop"


def desktop_file(name: str, contains: str | None = None, base: Path | None = None) -> VerifyResult:
    """A file exists on the Desktop (or `base`), optionally containing a substring."""
    p = (base or DESKTOP) / name
    if not p.exists():
        return VerifyResult(False, f"{name} not found")
    if contains is not None and contains.lower() not in p.read_text(errors="ignore").lower():
        return VerifyResult(False, f"{name} is missing {contains!r}")
    return VerifyResult(True, f"{name} present" + (f" with {contains!r}" if contains else ""))


def _osa(script: str) -> str | None:
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=8, text=True)
        return (r.stdout or "").strip() if r.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


def note_exists(title: str, min_chars: int = 0) -> VerifyResult:
    """A Notes note with `title` exists (and is at least `min_chars` long)."""
    safe = title.replace('"', '\\"')
    body = _osa(f'tell application "Notes" to get body of note "{safe}"')
    if body is None:
        return VerifyResult(False, f'note "{title}" not found')
    if len(body) < min_chars:
        return VerifyResult(False, f'note "{title}" is too short ({len(body)} < {min_chars})')
    return VerifyResult(True, f'note "{title}" exists')


def reminder_list(name: str, min_items: int = 1) -> VerifyResult:
    """A Reminders list `name` exists with at least `min_items` reminders."""
    safe = name.replace('"', '\\"')
    out = _osa(f'tell application "Reminders" to count reminders in list "{safe}"')
    if out is None:
        return VerifyResult(False, f'reminders list "{name}" not found')
    try:
        n = int(out)
    except ValueError:
        return VerifyResult(False, f"unexpected count {out!r}")
    return VerifyResult(n >= min_items, f'list "{name}" has {n} reminders (need >= {min_items})')


def manual(note: str) -> VerifyResult:
    """Mark a task as needing a human check (not counted in the auto success rate)."""
    return VerifyResult(False, note, manual=True)


# --- setup helpers (idempotent clean-slate before a run) --------------------

def rm_desktop_file(name: str) -> None:
    (DESKTOP / name).unlink(missing_ok=True)


def delete_note(title: str) -> None:
    safe = title.replace('"', '\\"')
    _osa(f'tell application "Notes" to delete every note whose name is "{safe}"')
