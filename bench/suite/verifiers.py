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


_PREFLIGHT = "run `python -m bench.suite.preflight` and approve the dialogs"


def _osa(script: str) -> tuple[str, str]:
    """Run AppleScript -> (stdout, error_kind). error_kind is '' on success, 'perm' if
    macOS blocked automation (-1743 / Not authorized), or 'fail' for any other error.

    Distinguishing 'perm' matters: a permission gap must NOT masquerade as a wrong
    answer — it means "couldn't check", which the verifier reports as manual, not fail.
    """
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=8, text=True)
    except (subprocess.TimeoutExpired, OSError):
        return "", "fail"
    if r.returncode == 0:
        return (r.stdout or "").strip(), ""
    err = r.stderr or ""
    return "", ("perm" if ("-1743" in err or "Not authorized" in err) else "fail")


def note_exists(title: str, min_chars: int = 0) -> VerifyResult:
    """A Notes note named `title` exists (matched across accounts/folders), optionally at
    least `min_chars` long. Permission-denied -> manual (excluded from the success rate)."""
    safe = title.replace('"', '\\"')
    out, err = _osa(f'tell application "Notes" to return (count (notes whose name is "{safe}"))')
    if err == "perm":
        return VerifyResult(False, f"Notes automation not authorized — {_PREFLIGHT}", manual=True)
    if err or not out or out == "0":
        return VerifyResult(False, f'note "{title}" not found')
    if min_chars:
        body, berr = _osa(f'tell application "Notes" to get body of (first note whose name is "{safe}")')
        if not berr and len(body) < min_chars:
            return VerifyResult(False, f'note "{title}" is too short ({len(body)} < {min_chars})')
    return VerifyResult(True, f'note "{title}" exists')


def reminder_list(name: str, min_items: int = 1) -> VerifyResult:
    """A Reminders list `name` exists with at least `min_items` reminders. Permission-denied
    -> manual (excluded from the success rate)."""
    safe = name.replace('"', '\\"')
    out, err = _osa(f'tell application "Reminders" to count reminders in list "{safe}"')
    if err == "perm":
        return VerifyResult(False, f"Reminders automation not authorized — {_PREFLIGHT}", manual=True)
    if err:
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
