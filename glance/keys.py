"""macOS keyboard input.

Key presses go through AppleScript System Events (reliable for OS shortcuts like
Cmd+Space) with a short timeout so a first-use permission dialog can't hang, and a
pyautogui fallback for non-macOS.
"""

from __future__ import annotations

import subprocess
import sys

# pyautogui key names (non-macOS fallback)
_PYAUTOGUI = {
    "return": "enter", "escape": "esc", "backspace": "backspace", "delete": "delete",
    "cmd": "command", "super": "command", "ctrl": "ctrl", "control": "ctrl",
    "page_down": "pagedown", "page_up": "pageup", "space": "space",
}

# macOS virtual key codes for non-character keys (so e.g. 'f5' is pressed, not typed)
_KEYCODES = {
    "space": 49, "enter": 36, "return": 36, "tab": 48, "escape": 53, "esc": 53,
    "delete": 51, "backspace": 51, "left": 123, "right": 124, "down": 125, "up": 126,
    "pagedown": 121, "page_down": 121, "pageup": 116, "page_up": 116,
    "home": 115, "end": 119,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
}

_MODIFIERS = {
    "command": "command", "cmd": "command", "super": "command",
    "ctrl": "control", "control": "control", "shift": "shift",
    "option": "option", "alt": "option",
}


def mac_key(keys: str) -> bool:
    """Send a key/combo via AppleScript System Events. Never blocks (short timeout +
    captured output); returns False on timeout/error so the caller can fall back."""
    *mods, key = [p.strip() for p in keys.split("+")]
    using = ""
    if mods:
        names = [_MODIFIERS.get(m.lower(), m.lower()) for m in mods]
        using = " using {" + ", ".join(f"{n} down" for n in names) + "}"
    kl = key.lower()
    if kl in _KEYCODES:
        action = f"key code {_KEYCODES[kl]}"
    else:
        safe = key.replace("\\", "\\\\").replace('"', '\\"')
        action = f'keystroke "{safe}"'
    script = f'tell application "System Events" to {action}{using}'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=4)
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False


def press_key(pg, keys: str) -> None:
    """Press a key or combo, preferring System Events on macOS, else pyautogui (`pg`)."""
    if sys.platform == "darwin" and mac_key(keys):
        return
    parts = [_PYAUTOGUI.get(p.lower(), p.lower()) for p in keys.split("+")]
    pg.hotkey(*parts) if len(parts) > 1 else pg.press(parts[0])
